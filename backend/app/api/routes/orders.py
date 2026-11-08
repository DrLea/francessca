"""Client side of orders: send a prepared case to a lawyer, follow it, and
rate the lawyer once it is closed."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.database import get_db
from app.dependencies import get_current_user, require_data_consent
from app.models.document import Document
from app.models.lawyer import Lawyer
from app.models.order import CLOSED_STATUSES, LawyerReview, Order, OrderStatus
from app.models.user import User, UserRole
from app.repositories.document_repo import CaseRepository
from app.repositories.timeline_repo import TimelineRepository
from app.schemas.portal import ClientOrderOut, OrderCreate, ReviewCreate
from app.services import email_service
from app.services.lead_quality import score_lead
from app.services.order_service import OrderService, utcnow

router = APIRouter(prefix="/orders", tags=["orders"])
log = get_logger("francessca.orders")


def _own_order(db: Session, user: User, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return order


@router.post("", response_model=ClientOrderOut, status_code=status.HTTP_201_CREATED)
def send_case(
    data: OrderCreate,
    background: BackgroundTasks,
    user: User = Depends(require_data_consent),
    db: Session = Depends(get_db),
) -> ClientOrderOut:
    if user.role == UserRole.lawyer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lawyer accounts cannot send cases",
        )
    if not data.consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please confirm that you want to share this case with this lawyer",
        )
    lawyer = db.get(Lawyer, data.lawyer_id)
    if lawyer is None or not lawyer.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer not found")
    if not lawyer.accepts_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This lawyer cannot receive cases through Francesca yet",
        )
    already = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.client_id == user.id,
            Order.lawyer_id == lawyer.id,
            Order.status == OrderStatus.pending.value,
        )
    )
    if already:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a request waiting with this lawyer",
        )

    case = None
    if data.case_id is not None:
        case = CaseRepository(db).get_for_user(data.case_id, user.id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    elif data.conversation_id is not None:
        # Builds a fresh summary: the one place sending a case calls the model.
        from app.services.case_service import CaseService

        case = CaseService(db).generate_summary(user, data.conversation_id, None)

    message = (data.message or "").strip() or None
    if case is None and not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a case or write a message",
        )

    summary = dict(case.summary or {}) if case is not None else {}
    document_count = (
        db.scalar(
            select(func.count()).select_from(Document).where(Document.user_id == user.id)
        )
        or 0
    )
    score, breakdown = score_lead(
        summary,
        message=message,
        # Documents and dates belong to the account, not to one case; only
        # count them when a case is actually attached.
        document_count=document_count if case is not None else 0,
        timeline_count=len(TimelineRepository(db).list_for_user(user.id))
        if case is not None
        else 0,
    )
    order = Order(
        client_id=user.id,
        lawyer_id=lawyer.id,
        case_id=case.id if case is not None else None,
        message=message,
        case_title=case.title if case is not None else None,
        case_type=(case.case_type or summary.get("case_type") or None)
        if case is not None
        else None,
        case_summary=summary,
        quality_score=score,
        quality_breakdown=breakdown,
        consent_at=utcnow(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    log_event(log, "order_created", order_id=order.id, lawyer_id=lawyer.id, score=score)

    # Notify the lawyer on the address of their account, falling back to
    # the public one on the profile.
    account = db.get(User, lawyer.user_id) if lawyer.user_id else None
    background.add_task(
        email_service.new_order_lawyer,
        account.email if account else lawyer.email,
        lawyer.name,
        order.case_title or "Message from a client",
        score,
    )
    return OrderService(db).to_client(order)


@router.get("", response_model=list[ClientOrderOut])
def my_orders(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ClientOrderOut]:
    service = OrderService(db)
    return [service.to_client(o) for o in service.for_client(user.id)]


@router.post("/{order_id}/cancel", response_model=ClientOrderOut)
def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientOrderOut:
    """Withdraw a request the lawyer has not answered yet."""
    order = _own_order(db, user, order_id)
    if order.status != OrderStatus.pending.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a request that is still waiting can be withdrawn",
        )
    order.status = OrderStatus.cancelled.value
    db.commit()
    db.refresh(order)
    return OrderService(db).to_client(order)


@router.post("/{order_id}/withdraw", response_model=ClientOrderOut)
def withdraw_consent(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientOrderOut:
    """Take back consent for a case already shared with a lawyer. From now
    on the lawyer no longer sees the case file or the client's contact."""
    order = _own_order(db, user, order_id)
    if order.status in (OrderStatus.cancelled.value, OrderStatus.withdrawn.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Consent was already withdrawn"
        )
    order.status = (
        OrderStatus.cancelled if order.status == OrderStatus.pending.value
        else OrderStatus.withdrawn
    ).value
    order.consent_withdrawn_at = utcnow()
    db.commit()
    db.refresh(order)
    log_event(log, "order_consent_withdrawn", order_id=order.id)
    return OrderService(db).to_client(order)


@router.post("/{order_id}/review", response_model=ClientOrderOut)
def review_lawyer(
    order_id: int,
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientOrderOut:
    """Rate the lawyer — once, and only after the order was closed, so
    every review comes from someone who actually dealt with them."""
    order = _own_order(db, user, order_id)
    if order.status not in CLOSED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You can review a lawyer once the case is closed",
        )
    if order.review is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already reviewed")
    db.add(
        LawyerReview(
            order_id=order.id,
            lawyer_id=order.lawyer_id,
            client_id=user.id,
            rating=data.rating,
            comment=(data.comment or "").strip() or None,
        )
    )
    db.flush()
    service = OrderService(db)
    service.refresh_rating(order.lawyer)
    db.commit()
    db.refresh(order)
    return service.to_client(order)
