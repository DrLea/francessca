"""Admin panel routes. All endpoints require an admin user."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models.conversation import Conversation
from app.models.case import Case
from app.models.lawyer import Lawyer
from app.models.lawyer_application import ApplicationStatus, LawyerApplication
from app.models.order import (
    BILLABLE_STATUSES,
    FeedbackStatus,
    LawyerFeedback,
    LawyerReview,
    Order,
    OrderStatus,
)
from app.models.prompt_version import PromptVersion
from app.models.token_usage import TokenUsage
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.repositories.lawyer_repo import LawyerRepository
from app.schemas.lawyer_application import LawyerApplicationOut
from app.schemas.portal import (
    AdminFeedbackOut,
    AdminFeedbackUpdate,
    AdminLawyerUpdate,
)
from app.schemas.user import AdminUserUpdate, UserOut
from app.config import settings
from app.services import email_service
from app.seeds.lawyers import sample_lawyers
from app.services.lawyer_service import LawyerService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in UserRepository(db).all_users()]


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field_name, value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(conv)
    db.commit()
    return {"detail": "deleted"}


@router.post("/lawyers/sync")
def sync_lawyers(
    live: bool = False,
    max_pages: int = 5,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger lawyer synchronisation.

    `live=false` (default) reseeds from the sample dataset; `live=true` runs
    the rak-muenchen scraper (which itself caches and skips unchanged pages).
    """
    service = LawyerService(db)
    if live:
        return service.sync_live(max_pages=max_pages)
    return service.sync_from_parsed(sample_lawyers())


# --- Lawyer sign-up applications ----------------------------------------
@router.get("/lawyer-applications", response_model=list[LawyerApplicationOut])
def list_lawyer_applications(
    status_filter: ApplicationStatus | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[LawyerApplicationOut]:
    stmt = select(LawyerApplication).order_by(desc(LawyerApplication.created_at))
    if status_filter is not None:
        stmt = stmt.where(LawyerApplication.status == status_filter)
    return [LawyerApplicationOut.model_validate(a) for a in db.scalars(stmt)]


def _get_application(db: Session, application_id: int) -> LawyerApplication:
    application = db.get(LawyerApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if application.status is not ApplicationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application already {application.status.value}",
        )
    return application


@router.post("/lawyer-applications/{application_id}/approve", response_model=LawyerApplicationOut)
def approve_lawyer_application(
    application_id: int,
    background: BackgroundTasks,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LawyerApplicationOut:
    """Publish an application to the directory.

    The new row gets a source_key of its own so a later scraper sync can
    never overwrite or delete a lawyer who signed up here directly.
    """
    application = _get_application(db, application_id)
    if application.lawyer_id is not None:
        # Registered through the portal: the directory row already exists
        # (and may have been edited since) — approving just publishes it.
        lawyer = db.get(Lawyer, application.lawyer_id)
        if lawyer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer profile is gone"
            )
        lawyer.is_published = True
        application.status = ApplicationStatus.approved
        application.reviewed_at = func.now()
        db.commit()
        db.refresh(application)
        background.add_task(
            email_service.lawyer_decision, application.email, application.name, True
        )
        return LawyerApplicationOut.model_validate(application)

    lawyer, _changed = LawyerRepository(db).upsert(
        {
            "source_key": f"application:{application.id}",
            "name": application.name,
            "law_firm": application.law_firm,
            "city": application.city,
            "email": application.email,
            "phone": application.phone,
            "website": application.website,
            "address": application.address,
            "languages": application.languages,
            "specializations": [
                s.strip()
                for s in (application.specializations or "").split(",")
                if s.strip()
            ],
        }
    )
    db.flush()
    application.status = ApplicationStatus.approved
    application.lawyer_id = lawyer.id
    application.reviewed_at = func.now()
    db.commit()
    db.refresh(application)
    return LawyerApplicationOut.model_validate(application)


@router.post("/lawyer-applications/{application_id}/reject", response_model=LawyerApplicationOut)
def reject_lawyer_application(
    application_id: int,
    background: BackgroundTasks,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LawyerApplicationOut:
    application = _get_application(db, application_id)
    application.status = ApplicationStatus.rejected
    application.reviewed_at = func.now()
    db.commit()
    db.refresh(application)
    if application.user_id is not None:
        background.add_task(
            email_service.lawyer_decision, application.email, application.name, False
        )
    return LawyerApplicationOut.model_validate(application)


@router.get("/usage")
def ai_usage(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict:
    total_in = db.scalar(select(func.coalesce(func.sum(TokenUsage.input_tokens), 0)))
    total_out = db.scalar(select(func.coalesce(func.sum(TokenUsage.output_tokens), 0)))
    requests = db.scalar(select(func.count()).select_from(TokenUsage))
    return {
        "requests": requests,
        "input_tokens": int(total_in or 0),
        "output_tokens": int(total_out or 0),
        "total_tokens": int((total_in or 0) + (total_out or 0)),
    }


# --- Prompt management ---------------------------------------------------
class PromptIn(BaseModel):
    name: str = "francessca-system"
    content: str
    activate: bool = True


@router.get("/prompts")
def list_prompts(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.scalars(
        select(PromptVersion).order_by(desc(PromptVersion.created_at))
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "is_active": p.is_active,
            "content": p.content,
            "created_at": p.created_at.isoformat(),
        }
        for p in rows
    ]


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
def create_prompt(
    data: PromptIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    prompt = PromptVersion(name=data.name, content=data.content, is_active=data.activate)
    if data.activate:
        # Deactivate any currently-active prompt of the same name.
        for existing in db.scalars(
            select(PromptVersion).where(
                PromptVersion.is_active.is_(True), PromptVersion.name == data.name
            )
        ):
            existing.is_active = False
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return {"id": prompt.id, "is_active": prompt.is_active}


# --- Overview: everything on one screen ---------------------------------
def _count(db: Session, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for clause in where:
        stmt = stmt.where(clause)
    return db.scalar(stmt) or 0


@router.get("/overview")
def overview(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    order_counts = dict(
        db.execute(select(Order.status, func.count()).group_by(Order.status)).all()
    )
    orders = {s.value: int(order_counts.get(s.value, 0)) for s in OrderStatus}
    accepted = sum(orders[s] for s in BILLABLE_STATUSES)
    revenue = db.scalar(
        select(func.coalesce(func.sum(Order.deal_value), 0)).where(
            Order.status == OrderStatus.closed_won.value
        )
    )
    avg_quality = db.scalar(
        select(func.avg(Order.quality_score)).where(
            Order.status != OrderStatus.cancelled.value
        )
    )
    avg_rating = db.scalar(select(func.avg(LawyerReview.rating)))
    total_in = db.scalar(select(func.coalesce(func.sum(TokenUsage.input_tokens), 0)))
    total_out = db.scalar(select(func.coalesce(func.sum(TokenUsage.output_tokens), 0)))

    recent_orders = db.scalars(
        select(Order).order_by(Order.created_at.desc(), Order.id.desc()).limit(10)
    ).all()
    recent_users = db.scalars(
        select(User).order_by(User.created_at.desc(), User.id.desc()).limit(8)
    ).all()

    return {
        "users": {
            "clients": _count(db, User, User.role == UserRole.user),
            "lawyers": _count(db, User, User.role == UserRole.lawyer),
            "admins": _count(db, User, User.role == UserRole.admin),
        },
        "lawyers": {
            "directory": _count(db, Lawyer, Lawyer.is_published.is_(True)),
            "registered": _count(db, Lawyer, Lawyer.user_id.is_not(None)),
            "live": _count(
                db, Lawyer, Lawyer.user_id.is_not(None), Lawyer.is_published.is_(True)
            ),
            "pending_approval": _count(
                db, LawyerApplication, LawyerApplication.status == ApplicationStatus.pending
            ),
        },
        "orders": {
            **orders,
            "total": sum(orders.values()),
            "accepted_total": accepted,
            "avg_quality": round(float(avg_quality)) if avg_quality is not None else None,
            "reported_revenue": float(revenue or 0),
        },
        "feedback": {
            "new": _count(db, LawyerFeedback, LawyerFeedback.status == FeedbackStatus.new.value),
            "total": _count(db, LawyerFeedback),
        },
        "reviews": {
            "total": _count(db, LawyerReview),
            "average": round(float(avg_rating), 2) if avg_rating is not None else None,
        },
        "activity": {
            "conversations": _count(db, Conversation),
            "cases": _count(db, Case),
            "tokens": int((total_in or 0) + (total_out or 0)),
        },
        "recent_orders": [
            {
                "id": o.id,
                "status": o.status,
                "lawyer": o.lawyer.name if o.lawyer else None,
                "client": o.client.email if o.client else None,
                "case_title": o.case_title,
                "quality_score": o.quality_score,
                "deal_value": float(o.deal_value) if o.deal_value is not None else None,
                "created_at": o.created_at.isoformat(),
            }
            for o in recent_orders
        ],
        "recent_users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "created_at": u.created_at.isoformat(),
            }
            for u in recent_users
        ],
    }


# --- Registered lawyers: publish state and order allowance --------------
def _lawyer_row(db: Session, lawyer: Lawyer, used: int) -> dict:
    free = max(0, settings.lawyer_free_orders)
    return {
        "id": lawyer.id,
        "name": lawyer.name,
        "email": lawyer.email,
        "city": lawyer.city,
        "law_firm": lawyer.law_firm,
        "is_published": lawyer.is_published,
        "rating_avg": lawyer.rating_avg,
        "rating_count": lawyer.rating_count,
        "orders_used": used,
        "free_total": free,
        "extra_orders": lawyer.extra_orders,
        "orders_remaining": max(0, free + lawyer.extra_orders - used),
        "created_at": lawyer.created_at.isoformat(),
    }


@router.get("/lawyer-accounts")
def list_lawyer_accounts(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[dict]:
    """Lawyers who have an account, with how many orders they have used."""
    used = dict(
        db.execute(
            select(Order.lawyer_id, func.count())
            .where(Order.status.in_(BILLABLE_STATUSES))
            .group_by(Order.lawyer_id)
        ).all()
    )
    lawyers = db.scalars(
        select(Lawyer).where(Lawyer.user_id.is_not(None)).order_by(desc(Lawyer.created_at))
    )
    return [_lawyer_row(db, lw, int(used.get(lw.id, 0))) for lw in lawyers]


@router.patch("/lawyer-accounts/{lawyer_id}")
def update_lawyer_account(
    lawyer_id: int,
    data: AdminLawyerUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Unlock more orders after the free ones, or pull a profile from the
    directory."""
    lawyer = db.get(Lawyer, lawyer_id)
    if lawyer is None or lawyer.user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if data.extra_orders is not None:
        lawyer.extra_orders = data.extra_orders
    if data.is_published is not None:
        lawyer.is_published = data.is_published
    db.commit()
    db.refresh(lawyer)
    used = _count(
        db, Order, Order.lawyer_id == lawyer.id, Order.status.in_(BILLABLE_STATUSES)
    )
    return _lawyer_row(db, lawyer, used)


# --- Lawyer feedback ----------------------------------------------------
def _feedback_out(feedback: LawyerFeedback) -> AdminFeedbackOut:
    order = feedback.order
    return AdminFeedbackOut(
        **{
            c: getattr(feedback, c)
            for c in (
                "id",
                "lawyer_id",
                "order_id",
                "category",
                "rating",
                "comment",
                "status",
                "admin_note",
                "created_at",
            )
        },
        lawyer_name=feedback.lawyer.name if feedback.lawyer else "—",
        lawyer_city=feedback.lawyer.city if feedback.lawyer else None,
        order_quality_score=order.quality_score if order else None,
        order_case_title=order.case_title if order else None,
    )


@router.get("/feedback")
def list_feedback(
    status_filter: FeedbackStatus | None = None,
    category: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(LawyerFeedback).order_by(
        desc(LawyerFeedback.created_at), desc(LawyerFeedback.id)
    )
    if status_filter is not None:
        stmt = stmt.where(LawyerFeedback.status == status_filter.value)
    if category:
        stmt = stmt.where(LawyerFeedback.category == category)
    items = [_feedback_out(f) for f in db.scalars(stmt)]

    # Summary over *all* feedback, whatever the current filter.
    by_category = {
        cat: {"count": int(count), "avg_rating": round(float(avg), 2) if avg is not None else None}
        for cat, count, avg in db.execute(
            select(
                LawyerFeedback.category,
                func.count(),
                func.avg(LawyerFeedback.rating),
            ).group_by(LawyerFeedback.category)
        ).all()
    }
    return {
        "items": [i.model_dump(mode="json") for i in items],
        "summary": {
            "new": _count(db, LawyerFeedback, LawyerFeedback.status == FeedbackStatus.new.value),
            "total": _count(db, LawyerFeedback),
            "by_category": by_category,
        },
    }


@router.patch("/feedback/{feedback_id}", response_model=AdminFeedbackOut)
def update_feedback(
    feedback_id: int,
    data: AdminFeedbackUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminFeedbackOut:
    feedback = db.get(LawyerFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if data.status is not None:
        feedback.status = data.status
    if data.admin_note is not None:
        feedback.admin_note = data.admin_note.strip() or None
    db.commit()
    db.refresh(feedback)
    return _feedback_out(feedback)
