"""Unauthenticated routes used by the public landing page.

Everything here is readable by anyone, so the lawyer preview deliberately
omits contact details (those stay behind the login on /lawyers) and the
application endpoint only ever creates a *pending* record.
"""
from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.database import get_db
from app.models.lawyer import Lawyer
from app.models.lawyer_application import LawyerApplication
from app.schemas.lawyer_application import (
    LawyerApplicationCreate,
    LawyerApplicationOut,
    LawyerPublicOut,
)

router = APIRouter(prefix="/public", tags=["public"])
log = get_logger("francessca.public")

# Fixed names, so nothing from the request ever reaches the filesystem.
DOWNLOAD_FILENAMES = {
    "windows": "Francesca.exe",
    "mac": "Francesca.dmg",
    "linux": "Francesca",
}

# Hashing 175 MB takes seconds; do it once per file, keyed by what would
# change if the file were replaced.
_checksums: dict[tuple[str, int, float], str] = {}


def _self_hosted(platform: str) -> str | None:
    """Path to a locally hosted build, if one is there."""
    if not settings.download_dir:
        return None
    path = os.path.join(settings.download_dir, DOWNLOAD_FILENAMES[platform])
    return path if os.path.isfile(path) else None


def _sha256(path: str) -> str:
    stat = os.stat(path)
    key = (path, stat.st_size, stat.st_mtime)
    if key not in _checksums:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        _checksums.clear()  # only ever the current build matters
        _checksums[key] = digest.hexdigest()
    return _checksums[key]


@router.get("/lawyers")
def preview_lawyers(
    limit: int = Query(6, ge=1, le=24), db: Session = Depends(get_db)
) -> dict:
    """A short, contact-free preview of the directory for the landing page."""
    from sqlalchemy.orm import selectinload

    total = (
        db.scalar(
            select(func.count()).select_from(Lawyer).where(Lawyer.is_published.is_(True), Lawyer.suspended_at.is_(None))
        )
        or 0
    )
    rows = db.scalars(
        select(Lawyer)
        .options(selectinload(Lawyer.specializations))
        .where(Lawyer.is_published.is_(True), Lawyer.suspended_at.is_(None))
        .order_by(Lawyer.name)
        .limit(limit)
    )
    return {
        "total": total,
        "items": [LawyerPublicOut.model_validate(r).model_dump() for r in rows],
    }


@router.post(
    "/lawyer-applications",
    response_model=LawyerApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def apply_as_lawyer(
    data: LawyerApplicationCreate, db: Session = Depends(get_db)
) -> LawyerApplicationOut:
    """A lawyer asks to be listed. Stored as pending; an admin reviews it
    before anything reaches the directory."""
    application = LawyerApplication(
        name=data.name.strip(),
        email=str(data.email).lower(),
        law_firm=data.law_firm,
        city=data.city,
        phone=data.phone,
        website=data.website,
        address=data.address,
        languages=", ".join(data.languages) or None,
        specializations=", ".join(data.specializations) or None,
        message=data.message,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    log_event(log, "lawyer_application", id=application.id, email=application.email)
    return LawyerApplicationOut.model_validate(application)


@router.get("/downloads")
def desktop_downloads() -> dict:
    """Which desktop builds are on offer, if any.

    Empty list = nothing published yet, and the landing page hides the
    section rather than showing a dead button.
    """
    configured = (
        ("windows", settings.download_windows, settings.download_windows_sha256),
        ("mac", settings.download_mac, settings.download_mac_sha256),
        ("linux", settings.download_linux, settings.download_linux_sha256),
    )
    items = []
    for platform, url, sha in configured:
        local = _self_hosted(platform)
        if local:
            # Prefer our own copy: it is reachable wherever the app is, which
            # a third-party CDN is not (some networks cannot reach GitHub's).
            items.append(
                {
                    "platform": platform,
                    "url": f"/public/download/{platform}",
                    "sha256": (sha or "").strip() or _sha256(local),
                }
            )
        elif url.strip():
            items.append(
                {
                    "platform": platform,
                    "url": url.strip(),
                    "sha256": (sha or "").strip() or None,
                }
            )
    return {"version": settings.download_version.strip() or None, "items": items}


@router.get("/download/{platform}")
def download_desktop_build(platform: str) -> FileResponse:
    """Stream a locally hosted desktop build."""
    if platform not in DOWNLOAD_FILENAMES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path = _self_hosted(platform)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No build published for this platform",
        )
    log_event(log, "desktop_download", platform=platform)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=DOWNLOAD_FILENAMES[platform],
    )
