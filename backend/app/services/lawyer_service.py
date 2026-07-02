"""Lawyer synchronisation and search service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.models.lawyer import Lawyer
from app.repositories.lawyer_repo import LawyerRepository
from app.scraper.rak_muenchen import ParsedLawyer, RakMuenchenScraper

log = get_logger("francessca.lawyers")


class LawyerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LawyerRepository(db)

    def search(self, **kwargs) -> tuple[int, list[Lawyer]]:
        return self.repo.search(**kwargs)

    def sync_from_parsed(self, parsed: list[ParsedLawyer]) -> dict[str, int]:
        """Upsert a list of parsed lawyers, skipping unchanged records."""
        created = updated = skipped = 0
        for item in parsed:
            _, changed = self.repo.upsert(item.to_upsert_dict())
            if changed:
                # We can't cheaply tell created vs updated post-upsert here,
                # so the repo could be extended; for now count changes.
                updated += 1
            else:
                skipped += 1
        self.db.commit()
        stats = {"changed": updated, "skipped": skipped, "total": len(parsed)}
        log_event(log, "lawyer_sync", **stats)
        return stats

    def sync_live(self, max_pages: int = 5) -> dict[str, int]:
        """Run the live scraper and synchronise the results."""
        scraper = RakMuenchenScraper()
        parsed = scraper.crawl(max_pages=max_pages)
        return self.sync_from_parsed(parsed)
