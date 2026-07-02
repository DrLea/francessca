"""Lawyer repository with search and upsert support."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.lawyer import Lawyer, LawyerSpecialization
from app.repositories.base import BaseRepository


class LawyerRepository(BaseRepository[Lawyer]):
    model = Lawyer

    def get_by_source_key(self, source_key: str) -> Lawyer | None:
        return self.db.scalar(
            select(Lawyer)
            .options(selectinload(Lawyer.specializations))
            .where(Lawyer.source_key == source_key)
        )

    def search(
        self,
        *,
        specialization: str | None = None,
        city: str | None = None,
        language: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, list[Lawyer]]:
        stmt = select(Lawyer).options(selectinload(Lawyer.specializations))
        count_stmt = select(func.count(func.distinct(Lawyer.id)))

        if specialization:
            stmt = stmt.join(LawyerSpecialization).where(
                LawyerSpecialization.name.ilike(f"%{specialization}%")
            )
            count_stmt = count_stmt.join(LawyerSpecialization).where(
                LawyerSpecialization.name.ilike(f"%{specialization}%")
            )
        if city:
            stmt = stmt.where(Lawyer.city.ilike(f"%{city}%"))
            count_stmt = count_stmt.where(Lawyer.city.ilike(f"%{city}%"))
        if language:
            stmt = stmt.where(Lawyer.languages.ilike(f"%{language}%"))
            count_stmt = count_stmt.where(Lawyer.languages.ilike(f"%{language}%"))

        total = self.db.scalar(count_stmt) or 0
        rows = list(
            self.db.scalars(
                stmt.distinct().order_by(Lawyer.name).limit(limit).offset(offset)
            )
        )
        return total, rows

    def upsert(self, parsed: dict) -> tuple[Lawyer, bool]:
        """Insert or update a lawyer by source_key.

        Returns (lawyer, changed). `changed` is False when the cached
        content_hash matches, allowing the scraper to skip writes.
        """
        existing = self.get_by_source_key(parsed["source_key"])
        specs = parsed.pop("specializations", [])
        content_hash = parsed.get("content_hash")

        if existing is None:
            lawyer = Lawyer(**parsed)
            lawyer.last_synced_at = datetime.now(timezone.utc)
            lawyer.specializations = [LawyerSpecialization(name=s) for s in specs]
            self.add(lawyer)
            return lawyer, True

        if existing.content_hash and existing.content_hash == content_hash:
            # No change since last sync — just touch the timestamp.
            existing.last_synced_at = datetime.now(timezone.utc)
            return existing, False

        for key, value in parsed.items():
            setattr(existing, key, value)
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.specializations = [LawyerSpecialization(name=s) for s in specs]
        return existing, True
