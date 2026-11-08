"""Token accounting: estimation, fair-use enforcement, usage recording.

Francesca is free for people, so there are no plans to buy. The only limit
is a hidden fair-use cap against abuse: a rolling 24-hour token budget per
user. ``User.token_limit`` holds a per-user override an admin can set;
``NULL`` means "use the default" and the ``premium`` tier means "no cap"
(kept for admins, staff accounts and partner pilots -- never sold).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.models.token_usage import TokenUsage
from app.models.user import User, UserTier

log = get_logger("francessca.tokens")

# Rough heuristic: ~4 characters per token. Used for the pre-flight estimate
# before a request is sent; actual usage is reconciled from the API response.
_CHARS_PER_TOKEN = 4

FAIR_USE_WINDOW = timedelta(hours=24)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


class TokenService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # -- limits -------------------------------------------------------------
    def daily_limit(self, user: User) -> int | None:
        """Tokens allowed per rolling 24 h, or None for no cap."""
        if user.tier == UserTier.premium:
            return None
        return user.token_limit or settings.fair_use_daily_tokens

    def used_today(self, user: User) -> int:
        since = datetime.now(timezone.utc) - FAIR_USE_WINDOW
        total = self.db.execute(
            select(
                func.coalesce(
                    func.sum(TokenUsage.input_tokens + TokenUsage.output_tokens), 0
                )
            ).where(TokenUsage.user_id == user.id, TokenUsage.created_at >= since)
        ).scalar_one()
        return int(total or 0)

    def remaining(self, user: User) -> int | None:
        limit = self.daily_limit(user)
        if limit is None:
            return None
        return max(0, limit - self.used_today(user))

    def ensure_within_limit(self, user: User, estimated: int) -> None:
        """Reject the request up-front if the estimate would exceed the cap."""
        remaining = self.remaining(user)
        if remaining is None:
            return
        if estimated > remaining:
            log_event(
                log, "fair_use_limit_reached", user_id=user.id,
                estimated=estimated, remaining=remaining,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "You have reached today's fair-use limit. Francesca stays "
                    "free - please continue in a few hours."
                ),
            )

    def record(
        self,
        user: User,
        *,
        input_tokens: int,
        output_tokens: int,
        model: str,
        conversation_id: int | None = None,
    ) -> int:
        """Persist a usage row and increment the user's lifetime total."""
        total = input_tokens + output_tokens
        usage = TokenUsage(
            user_id=user.id,
            conversation_id=conversation_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )
        self.db.add(usage)
        user.tokens_used += total
        log_event(
            log, "token_usage", user_id=user.id, input=input_tokens,
            output=output_tokens, total=total,
        )
        return total
