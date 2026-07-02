"""ORM models. Importing this package registers every model on Base.metadata."""
from app.models.user import User, UserRole, UserTier  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message, MessageRole  # noqa: F401
from app.models.lawyer import Lawyer, LawyerSpecialization  # noqa: F401
from app.models.case import Case  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.export import Export  # noqa: F401
from app.models.token_usage import TokenUsage  # noqa: F401
from app.models.prompt_version import PromptVersion  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "UserTier",
    "Conversation",
    "Message",
    "MessageRole",
    "Lawyer",
    "LawyerSpecialization",
    "Case",
    "Document",
    "Export",
    "TokenUsage",
    "PromptVersion",
]
