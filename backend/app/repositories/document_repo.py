"""Document, case and export repositories."""
from __future__ import annotations

from sqlalchemy import select

from app.models.case import Case
from app.models.document import Document
from app.models.export import Export
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def list_for_user(self, user_id: int) -> list[Document]:
        return list(
            self.db.scalars(
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.uploaded_at.desc())
            )
        )

    def get_many_for_user(self, ids: list[int], user_id: int) -> list[Document]:
        if not ids:
            return []
        return list(
            self.db.scalars(
                select(Document).where(
                    Document.id.in_(ids), Document.user_id == user_id
                )
            )
        )


class CaseRepository(BaseRepository[Case]):
    model = Case

    def list_for_user(self, user_id: int) -> list[Case]:
        return list(
            self.db.scalars(
                select(Case)
                .where(Case.user_id == user_id)
                .order_by(Case.created_at.desc())
            )
        )

    def get_for_user(self, case_id: int, user_id: int) -> Case | None:
        return self.db.scalar(
            select(Case).where(Case.id == case_id, Case.user_id == user_id)
        )


class ExportRepository(BaseRepository[Export]):
    model = Export

    def list_for_case(self, case_id: int) -> list[Export]:
        return list(
            self.db.scalars(select(Export).where(Export.case_id == case_id))
        )
