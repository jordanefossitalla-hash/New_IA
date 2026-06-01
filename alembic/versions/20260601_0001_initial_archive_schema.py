"""Initial newspaper archive schema

Revision ID: 20260601_0001
Revises: 
Create Date: 2026-06-01 00:00:01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "20260601_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_status') THEN
                CREATE TYPE document_status AS ENUM ('pending', 'processing', 'completed', 'failed');
            END IF;
        END
        $$;
        """
    )

    document_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="document_status",
        create_type=False,
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("journal_name", sa.String(length=255), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("status", document_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_documents_journal_name", "documents", ["journal_name"])
    op.create_index("ix_documents_publication_date", "documents", ["publication_date"])
    op.create_unique_constraint("uq_documents_file_path", "documents", ["file_path"])

    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("ocr_used", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pages_document_id", "pages", ["document_id"])
    op.create_unique_constraint("uq_pages_document_page", "pages", ["document_id", "page_number"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_page_number", "chunks", ["page_number"])
    op.create_unique_constraint(
        "uq_chunks_document_page_chunk",
        "chunks",
        ["document_id", "page_number", "chunk_index"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_chunks_document_page_chunk", "chunks", type_="unique")
    op.drop_index("ix_chunks_page_number", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")

    op.drop_constraint("uq_pages_document_page", "pages", type_="unique")
    op.drop_index("ix_pages_document_id", table_name="pages")
    op.drop_table("pages")

    op.drop_constraint("uq_documents_file_path", "documents", type_="unique")
    op.drop_index("ix_documents_publication_date", table_name="documents")
    op.drop_index("ix_documents_journal_name", table_name="documents")
    op.drop_table("documents")

    op.execute("DROP TYPE IF EXISTS document_status")
