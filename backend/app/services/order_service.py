"""Orders: quota, serialisation and the lawyer's statistics."""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models.lawyer import Lawyer
from app.models.order import (
    BILLABLE_STATUSES,
    CLOSED_STATUSES,
    LawyerReview,
    Order,
    OrderStatus,
)
from app.schemas.portal import (
    ClientOrderOut,
    LawyerOrderOut,
    OrderClientRef,
    OrderLawyerRef,
    QuotaOut,
    ReviewOut,
)

PROFILE_FIELDS = (
    "name",
    "law_firm",
    "city",
    "email",
    "phone",
    "website",
    "address",
    "photo_url",
    "bio",
    "years_experience",
    "consultation_fee",
    "office_hours",
    "languages",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Quota ----------------------------------------------------------
    def used_orders(self, lawyer_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.lawyer_id == lawyer_id, Order.status.in_(BILLABLE_STATUSES))
            )
            or 0
        )

    def quota(self, lawyer: Lawyer) -> QuotaOut:
        free = max(0, settings.lawyer_free_orders)
        used = self.used_orders(lawyer.id)
        return QuotaOut(
            free_total=free,
            extra=lawyer.extra_orders,
            used=used,
            remaining=max(0, free + lawyer.extra_orders - used),
            free_remaining=max(0, free - used),
            contact_email=settings.contact_email or None,
        )

    # --- Queries --------------------------------------------------------
    def for_lawyer(self, lawyer_id: int, status: str | None = None) -> list[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.client), selectinload(Order.review))
            .where(Order.lawyer_id == lawyer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
        if status:
            stmt = stmt.where(Order.status == status)
        return list(self.db.scalars(stmt))

    def for_client(self, client_id: int) -> list[Order]:
        return list(
            self.db.scalars(
                select(Order)
                .options(selectinload(Order.lawyer), selectinload(Order.review))
                .where(Order.client_id == client_id)
                .order_by(Order.created_at.desc(), Order.id.desc())
            )
        )

    # --- Serialisation --------------------------------------------------
    @staticmethod
    def _review(order: Order) -> ReviewOut | None:
        return ReviewOut.model_validate(order.review) if order.review else None

    def to_lawyer(self, order: Order) -> LawyerOrderOut:
        revealed = order.status in BILLABLE_STATUSES
        client = order.client
        return LawyerOrderOut(
            id=order.id,
            status=order.status,
            case_title=order.case_title,
            case_type=order.case_type,
            case_summary=order.case_summary or {},
            message=order.message,
            quality_score=order.quality_score,
            quality_breakdown=order.quality_breakdown or {},
            is_free=order.is_free,
            deal_value=float(order.deal_value) if order.deal_value is not None else None,
            created_at=order.created_at,
            responded_at=order.responded_at,
            closed_at=order.closed_at,
            client=OrderClientRef(
                name=client.full_name, email=client.email, language=client.language
            )
            if revealed and client is not None
            else None,
            review=self._review(order),
        )

    def to_client(self, order: Order) -> ClientOrderOut:
        lawyer = order.lawyer
        return ClientOrderOut(
            id=order.id,
            status=order.status,
            lawyer=OrderLawyerRef(
                id=lawyer.id,
                name=lawyer.name,
                law_firm=lawyer.law_firm,
                city=lawyer.city,
                email=lawyer.email,
                phone=lawyer.phone,
            ),
            case_title=order.case_title,
            message=order.message,
            quality_score=order.quality_score,
            created_at=order.created_at,
            responded_at=order.responded_at,
            closed_at=order.closed_at,
            review=self._review(order),
            can_review=order.status in CLOSED_STATUSES and order.review is None,
        )

    # --- Reviews --------------------------------------------------------
    def refresh_rating(self, lawyer: Lawyer) -> None:
        avg, count = self.db.execute(
            select(func.avg(LawyerReview.rating), func.count(LawyerReview.id)).where(
                LawyerReview.lawyer_id == lawyer.id
            )
        ).one()
        lawyer.rating_avg = round(float(avg), 2) if avg is not None else None
        lawyer.rating_count = int(count or 0)

    # --- Statistics -----------------------------------------------------
    def stats(self, lawyer: Lawyer, months: int = 6) -> dict:
        orders = self.for_lawyer(lawyer.id)
        by_status = {s.value: 0 for s in OrderStatus}
        for order in orders:
            by_status[order.status] = by_status.get(order.status, 0) + 1

        received = len(orders) - by_status[OrderStatus.cancelled.value]
        accepted = sum(by_status[s] for s in BILLABLE_STATUSES)
        responded = accepted + by_status[OrderStatus.declined.value]
        won = by_status[OrderStatus.closed_won.value]
        lost = by_status[OrderStatus.closed_lost.value]

        won_orders = [o for o in orders if o.status == OrderStatus.closed_won.value]
        revenue = sum(float(o.deal_value or 0) for o in won_orders)
        valued = [o for o in won_orders if o.deal_value is not None]

        response_hours = [
            (o.responded_at - o.created_at).total_seconds() / 3600
            for o in orders
            if o.responded_at and o.created_at
            # SQLite hands back naive datetimes; only compare like with like.
            and (o.responded_at.tzinfo is None) == (o.created_at.tzinfo is None)
        ]

        # Month buckets, oldest first, always `months` long so the chart
        # has a stable x-axis even for a brand-new account.
        now = utcnow()
        buckets: "OrderedDict[str, dict]" = OrderedDict()
        year, month = now.year, now.month
        keys = []
        for _ in range(months):
            keys.append(f"{year:04d}-{month:02d}")
            month -= 1
            if month == 0:
                year, month = year - 1, 12
        for key in reversed(keys):
            buckets[key] = {"month": key, "received": 0, "accepted": 0, "won": 0, "revenue": 0.0}
        for order in orders:
            if order.status == OrderStatus.cancelled.value:
                continue
            key = order.created_at.strftime("%Y-%m")
            if key in buckets:
                buckets[key]["received"] += 1
                if order.status in BILLABLE_STATUSES:
                    buckets[key]["accepted"] += 1
            if order.status == OrderStatus.closed_won.value:
                closed_key = (order.closed_at or order.created_at).strftime("%Y-%m")
                if closed_key in buckets:
                    buckets[closed_key]["won"] += 1
                    buckets[closed_key]["revenue"] += float(order.deal_value or 0)

        free_total = max(0, settings.lawyer_free_orders)
        scored = [o.quality_score for o in orders if o.status != OrderStatus.cancelled.value]
        return {
            "orders": {
                "received": received,
                "pending": by_status[OrderStatus.pending.value],
                "accepted": accepted,
                "declined": by_status[OrderStatus.declined.value],
                "in_progress": by_status[OrderStatus.accepted.value],
                "won": won,
                "lost": lost,
            },
            "rates": {
                # None rather than 0 when there is nothing to divide by.
                "acceptance": round(accepted / responded, 3) if responded else None,
                "win": round(won / (won + lost), 3) if (won + lost) else None,
                "avg_response_hours": round(sum(response_hours) / len(response_hours), 1)
                if response_hours
                else None,
                "avg_lead_quality": round(sum(scored) / len(scored)) if scored else None,
            },
            "rating": {"average": lawyer.rating_avg, "count": lawyer.rating_count},
            "finance": {
                "revenue": round(revenue, 2),
                "deals": won,
                "avg_deal": round(revenue / len(valued), 2) if valued else None,
                "free_orders_used": min(accepted, free_total),
                "paid_orders_used": max(0, accepted - free_total),
                # Nothing is charged yet; kept explicit so the page can say so.
                "platform_fees": 0.0,
            },
            "monthly": list(buckets.values()),
        }


def profile_completeness(lawyer: Lawyer) -> int:
    filled = sum(1 for f in PROFILE_FIELDS if getattr(lawyer, f) not in (None, ""))
    total = len(PROFILE_FIELDS) + 1
    if lawyer.specializations:
        filled += 1
    return round(100 * filled / total)
