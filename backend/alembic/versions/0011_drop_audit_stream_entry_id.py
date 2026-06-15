"""Drop workflow_audit_log.stream_entry_id (AE-0074).

Events are published only after the owning transaction commits, so the
audit row can no longer store the Redis stream entry id returned by
publish(). Nothing reads the column; the Phase 6 outbox will own any
audit-to-stream linkage.
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_drop_audit_stream_entry_id"
down_revision = "0010_add_caption_en"
branch_labels = None
depends_on = None

TABLE_WORKFLOW_AUDIT_LOG = "workflow_audit_log"
COLUMN_STREAM_ENTRY_ID = "stream_entry_id"


def upgrade() -> None:
    op.drop_column(TABLE_WORKFLOW_AUDIT_LOG, COLUMN_STREAM_ENTRY_ID)


def downgrade() -> None:
    op.add_column(
        TABLE_WORKFLOW_AUDIT_LOG,
        sa.Column(COLUMN_STREAM_ENTRY_ID, sa.String(100), nullable=True),
    )
