"""Initial olympiad management schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    role = sa.Enum("GLOBAL_ADMIN", "OLYMPIAD_LEAD", name="role", native_enum=False)
    status = sa.Enum("PRESENT", "ABSENT", name="attendancestatus", native_enum=False)
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(50), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("full_name", sa.String(120), nullable=False), sa.Column("role", role, nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("olympiads", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False), sa.Column("description", sa.Text()), sa.Column("lead_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_olympiads_name", "olympiads", ["name"], unique=True); op.create_index("ix_olympiads_lead_user_id", "olympiads", ["lead_user_id"])
    op.create_table("students", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("full_name", sa.String(120), nullable=False), sa.Column("class_name", sa.String(30), nullable=False), sa.Column("olympiad_id", sa.Integer(), sa.ForeignKey("olympiads.id", ondelete="RESTRICT"), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_students_full_name", "students", ["full_name"]); op.create_index("ix_students_olympiad_id", "students", ["olympiad_id"]); op.create_index("ix_students_active", "students", ["active"]); op.create_index("ix_students_olympiad_active", "students", ["olympiad_id", "active"])
    op.create_table("attendance", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False), sa.Column("date", sa.Date(), nullable=False), sa.Column("status", status, nullable=False), sa.Column("marked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("student_id", "date", name="uq_attendance_student_date"))
    op.create_index("ix_attendance_student_id", "attendance", ["student_id"]); op.create_index("ix_attendance_date", "attendance", ["date"]); op.create_index("ix_attendance_student_date", "attendance", ["student_id", "date"])
    op.create_table("calendar_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("date", sa.Date(), nullable=False), sa.Column("title", sa.String(180), nullable=False), sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_calendar_events_date", "calendar_events", ["date"])

def downgrade():
    op.drop_table("calendar_events"); op.drop_table("attendance"); op.drop_table("students"); op.drop_table("olympiads"); op.drop_table("users")
