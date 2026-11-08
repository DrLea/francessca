"""The lawyer portal: profile, incoming orders, statistics, feedback.

Everything here is scoped to the signed-in lawyer's own record.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.database import get_db
from app.dependencies import get_current_user, require_lawyer
from app.models.lawyer import Lawyer, LawyerSpecialization
from app.models.lawyer_application import ApplicationStatus, LawyerApplication
from app.models.order import LawyerFeedback, LawyerReview, Order, OrderStatus
from app.models.user import User
from app.schemas.portal import (
    BeaCodeConfirm,
    FeedbackCreate,
    FeedbackOut,
    LawyerMeOut,
    LawyerOrderOut,
    LawyerProfileOut,
    LawyerProfileUpdate,
    OrderClose,
    ReviewOut,
)
from app.services import email_service
from app.services.order_service import OrderService, profile_completeness, utcnow
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/lawyer", tags=["lawyer portal"])
log = get_logger("francessca.lawyer")


def _approval(db: Session, lawyer: Lawyer) -> str:
    if lawyer.is_published:
        return ApplicationStatus.approved.value
    application = db.scalar(
        select(LawyerApplication)
        .where(LawyerApplication.lawyer_id == lawyer.id)
        .order_by(LawyerApplication.id.desc())
    )
    if application is not None and application.status is ApplicationStatus.rejected:
        return ApplicationStatus.rejected.value
    return ApplicationStatus.pending.value


def _me(db: Session, lawyer: Lawyer) -> LawyerMeOut:
    return LawyerMeOut(
        approval=_approval(db, lawyer),
        profile=LawyerProfileOut.model_validate(lawyer),
        subscription=OrderService.subscription(lawyer),
        verification=OrderService.verification(lawyer),
        profile_completeness=profile_completeness(lawyer),
    )


def _own_order(db: Session, lawyer: Lawyer, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.lawyer_id != lawyer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return order


@router.get("/me", response_model=LawyerMeOut)
def lawyer_me(
    lawyer: Lawyer = Depends(require_lawyer), db: Session = Depends(get_db)
) -> LawyerMeOut:
    return _me(db, lawyer)


@router.put("/profile", response_model=LawyerMeOut)
def update_profile(
    data: LawyerProfileUpdate,
    lawyer: Lawyer = Depends(require_lawyer),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LawyerMeOut:
    """Edit the directory profile. Allowed while approval is still pending,
    so a new lawyer can finish their profile before it goes live."""
    fields = data.model_dump(exclude_unset=True)
    specializations = fields.pop("specializations", None)
    languages = fields.pop("languages", None)

    if "name" in fields and not fields["name"]:
        fields.pop("name")  # the one field that may not be cleared
    register_keys = ("name", "brak_register_id", "chamber", "admission_date")
    before = tuple(getattr(lawyer, k) for k in register_keys)
    for key, value in fields.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(lawyer, key, str(value) if key == "email" and value else value)
    if languages is not None:
        lawyer.languages = ", ".join(languages) or None
    if specializations is not None:
        # De-duplicate case-insensitively: (lawyer_id, name) is unique.
        wanted: dict[str, str] = {}
        for name in specializations:
            wanted.setdefault(name.lower(), name)
        # Keep the rows that stay and only add/remove the difference.
        # Replacing the whole list would INSERT the unchanged names before
        # the old rows are deleted, and trip that unique constraint.
        kept = [s for s in lawyer.specializations if s.name.lower() in wanted]
        have = {s.name.lower() for s in kept}
        lawyer.specializations = kept + [
            LawyerSpecialization(name=n) for key, n in wanted.items() if key not in have
        ]
    if lawyer.name:
        user.full_name = lawyer.name
    if tuple(getattr(lawyer, k) for k in register_keys) != before:
        # The register check was for the old details.
        lawyer.brak_checked_at = None
        VerificationService.refresh(lawyer)

    db.commit()
    db.refresh(lawyer)
    return _me(db, lawyer)


# --- Verification -------------------------------------------------------
@router.post("/verification/bea", response_model=LawyerMeOut)
def confirm_bea_code(
    data: BeaCodeConfirm,
    lawyer: Lawyer = Depends(require_lawyer),
    db: Session = Depends(get_db),
) -> LawyerMeOut:
    """Type back the code that was sent to the lawyer's beA mailbox."""
    VerificationService(db).confirm_bea_code(lawyer, data.code)
    db.commit()
    db.refresh(lawyer)
    return _me(db, lawyer)


# --- Orders -------------------------------------------------------------
@router.get("/orders", response_model=list[LawyerOrderOut])
def list_orders(
    status_filter: OrderStatus | None = None,
    lawyer: Lawyer = Depends(require_lawyer),
    db: Session = Depends(get_db),
) -> list[LawyerOrderOut]:
    service = OrderService(db)
    orders = service.for_lawyer(
        lawyer.id, status_filter.value if status_filter else None
    )
    # A withdrawn request is none of the lawyer's business any more.
    return [
        service.to_lawyer(o) for o in orders if o.status != OrderStatus.cancelled.value
    ]


@router.post("/orders/{order_id}/accept", response_model=LawyerOrderOut)
def accept_order(
    order_id: int,
    background: BackgroundTasks,
    lawyer: Lawyer = Depends(require_lawyer),
    db: Session = Depends(get_db),
) -> LawyerOrderOut:
    """Take the case. Uses one order and reveals the client's contact."""
    service = OrderService(db)
    order = _own_order(db, lawyer, order_id)
    if order.status != OrderStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Order is already {order.status}"
        )
    subscription = service.subscription(lawyer)
    if not subscription.can_accept:
        # Flat fee, never per client: once the trial is over a firm needs an
        # active subscription. No payment provider yet -- an admin records
        # payment in /admin/lawyers.
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Your free trial has ended. Francesca costs a flat "
                f"EUR {settings.lawyer_monthly_fee:.0f} per month - contact us to continue."
            ),
        )
    order.status = OrderStatus.accepted.value
    order.is_free = subscription.state == "trial"
    order.responded_at = utcnow()
    db.commit()
    db.refresh(order)
    log_event(log, "order_accepted", order_id=order.id, lawyer_id=lawyer.id, free=order.is_free)
    background.add_task(
        email_service.order_response_client, order.client.email, lawyer.name, True
    )
    return service.to_lawyer(order)


@router.post("/orders/{order_id}/decline", response_model=LawyerOrderOut)
def decline_order(
    order_id: int,
    background: BackgroundTasks,
    lawyer: Lawyer = Depends(require_lawyer),
    db: Session = Depends(get_db),
) -> LawyerOrderOut:
    order = _own_order(db, lawyer, order_id)
    if order.status != OrderStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Order is already {order.status}"
        )
    order.status = OrderStatus.declined.value
    order.responded_at = utcnow()
    db.commit()
    db.refresh(order)
    background.add_task(
        email_service.order_response_client, order.client.email, lawyer.name, False
    )
    return OrderService(db).to_lawyer(order)


@router.post("/orders/{order_id}/close", response_model=LawyerOrderOut)
def close_order(
    order_id: int,
    data: OrderClose,
    lawyer: Lawyer = Depends(require_lawyer),
    db: Session = Depends(get_db),
) -> LawyerOrderOut:
    """Record how an accepted order ended. Can be corrected afterwards
    (won <-> lost, or the amount) by calling it again."""
    order = _own_order(db, lawyer, order_id)
    if order.status not in (
        OrderStatus.accepted.value,
        OrderStatus.closed_won.value,
        OrderStatus.closed_lost.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an accepted order can be closed",
        )
    won = data.outcome == "won"
    order.status = (OrderStatus.closed_won if won else OrderStatus.closed_lost).value
    order.deal_value = data.deal_value if won else None
    order.closed_at = order.closed_at or utcnow()
    db.commit()
    db.refresh(order)
    return OrderService(db).to_lawyer(order)


@router.get("/stats")
def stats(
    lawyer: Lawyer = Depends(require_lawyer), db: Session = Depends(get_db)
) -> dict:
    return OrderService(db).stats(lawyer)


@router.get("/reviews", response_model=list[ReviewOut])
def my_reviews(
    lawyer: Lawyer = Depends(require_lawyer), db: Session = Depends(get_db)
) -> list[ReviewOut]:
    rows = db.scalars(
        select(LawyerReview)
        .where(LawyerReview.lawyer_id == lawyer.id)
        .order_by(LawyerReview.created_at.desc())
    )
    return [ReviewOut.model_validate(r) for r in rows]


# --- Feedback -----------------------------------------------------------
@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def leave_feedback(
    data: FeedbackCreate,
    background: BackgroundTasks,
    lawyer: Lawyer = Depends(require_lawyer),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    if data.order_id is not None:
        _own_order(db, lawyer, data.order_id)
    feedback = LawyerFeedback(
        lawyer_id=lawyer.id,
        user_id=lawyer.user_id,
        order_id=data.order_id,
        category=data.category,
        rating=data.rating,
        comment=data.comment.strip(),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    log_event(log, "lawyer_feedback", id=feedback.id, lawyer_id=lawyer.id)
    background.add_task(
        email_service.new_feedback_admin, lawyer.name, data.category, feedback.comment
    )
    return FeedbackOut.model_validate(feedback)


@router.get("/feedback", response_model=list[FeedbackOut])
def my_feedback(
    lawyer: Lawyer = Depends(require_lawyer), db: Session = Depends(get_db)
) -> list[FeedbackOut]:
    rows = db.scalars(
        select(LawyerFeedback)
        .where(LawyerFeedback.lawyer_id == lawyer.id)
        .order_by(LawyerFeedback.created_at.desc())
    )
    return [FeedbackOut.model_validate(r) for r in rows]
