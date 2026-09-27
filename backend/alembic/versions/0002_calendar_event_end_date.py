"""Add an optional end date to calendar events."""

from alembic import op
import sqlalchemy as sa


revision = "0002_calendar_event_end_date"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("calendar_events", sa.Column("end_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("calendar_events", "end_date")
