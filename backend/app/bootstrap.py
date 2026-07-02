"""Idempotent startup bootstrap.

Creates the admin user (from env) and seeds sample data if the relevant
tables are empty. Safe to run on every startup — it only acts when needed.
Invoked by entrypoint.sh after migrations, and importable in tests.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.config import settings
from app.core.logging import get_logger
from app.core.prompts import FRANCESSCA_SYSTEM_PROMPT
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.lawyer import Lawyer
from app.models.prompt_version import PromptVersion
from app.models.user import User, UserRole, UserTier
from app.seeds.lawyers import sample_lawyers
from app.services.lawyer_service import LawyerService

log = get_logger("francessca.bootstrap")


def ensure_admin(db) -> None:
    if not settings.admin_email or not settings.admin_password:
        log.info("No ADMIN_EMAIL/ADMIN_PASSWORD set; skipping admin bootstrap")
        return
    existing = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
    if existing:
        return
    admin = User(
        email=settings.admin_email.lower(),
        password_hash=hash_password(settings.admin_password),
        full_name="Administrator",
        role=UserRole.admin,
        tier=UserTier.premium,
        token_limit=None,
    )
    db.add(admin)
    db.commit()
    log.info("Created admin user %s", admin.email)


def ensure_active_prompt(db) -> None:
    has_active = db.scalar(
        select(func.count()).select_from(PromptVersion).where(
            PromptVersion.is_active.is_(True)
        )
    )
    if not has_active:
        db.add(
            PromptVersion(
                name="francessca-system",
                content=FRANCESSCA_SYSTEM_PROMPT,
                is_active=True,
            )
        )
        db.commit()
        log.info("Seeded active system prompt")


def ensure_lawyers(db) -> None:
    count = db.scalar(select(func.count()).select_from(Lawyer))
    if count:
        return
    stats = LawyerService(db).sync_from_parsed(sample_lawyers())
    log.info("Seeded lawyers: %s", stats)


def run() -> None:
    db = SessionLocal()
    try:
        ensure_admin(db)
        ensure_active_prompt(db)
        ensure_lawyers(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
