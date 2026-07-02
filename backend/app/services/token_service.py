"""Token accounting: estimation, limit enforcement, usage recording."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.models.token_usage import TokenUsage
from app.models.user import User

log = get_logger("francessca.tokens")

# Rough heuristic: ~4 characters per token. Used for the pre-flight estimate
# before a request is sent; actual usage is reconciled from the API response.
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


class TokenService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def remaining(self, user: User) -> int | None:
        if user.is_unlimited:
            return None
        return max(0, (user.token_limit or 0) - user.tokens_used)

    def ensure_within_limit(self, user: User, estimated: int) -> None:
        """Reject the request up-front if the estimate would exceed the cap."""
        if user.is_unlimited:
            return
        remaining = self.remaining(user) or 0
        if estimated > remaining:
            log_event(
                log, "token_limit_exceeded", user_id=user.id,
                estimated=estimated, remaining=remaining,
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Monthly token limit exceeded. "
                    f"Estimated {estimated} tokens, {remaining} remaining."
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
        """Persist a usage row and increment the user's running total."""
        total = input_tokens + output_tokens
        usage = TokenUsage(
            user_id=user.id,
            conversation_id=conversation_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )
        self.db.add(usage)
        if not user.is_unlimited:
            user.tokens_used += total
        log_event(
            log, "token_usage", user_id=user.id, input=input_tokens,
            output=output_tokens, total=total,
        )
        return total
