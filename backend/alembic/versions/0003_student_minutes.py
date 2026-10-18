"""Track minutes recorded for students by olympiad leads."""

from alembic import op
import sqlalchemy as sa


revision = "0003_student_minutes"
down_revision = "0002_calendar_event_end_date"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "student_minutes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("minutes >= 0", name="ck_student_minutes_nonnegative"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "date", name="uq_student_minutes_student_date"),
    )
    op.create_index("ix_student_minutes_date", "student_minutes", ["date"])
    op.create_index("ix_student_minutes_student_id", "student_minutes", ["student_id"])


def downgrade():
    op.drop_index("ix_student_minutes_student_id", table_name="student_minutes")
    op.drop_index("ix_student_minutes_date", table_name="student_minutes")
    op.drop_table("student_minutes")
