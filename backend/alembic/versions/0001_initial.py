"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "challenges",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("image_name", sa.String(length=255), nullable=False),
        sa.Column("build_context", sa.String(length=255), nullable=False),
        sa.Column("dockerfile_path", sa.String(length=255), nullable=False),
        sa.Column("entry_path", sa.String(length=255), nullable=False),
        sa.Column("internal_port", sa.Integer(), nullable=False),
        sa.Column("runtime_max_seconds", sa.Integer(), nullable=False),
        sa.Column("runtime_memory_limit", sa.String(length=32), nullable=False),
        sa.Column("runtime_cpu_limit", sa.String(length=32), nullable=False),
        sa.Column("allow_internet", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("allow_bruteforce", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("allow_port_scan", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_requests", sa.Integer(), nullable=False),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "challenge_instances",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("challenge_id", sa.String(length=64), sa.ForeignKey("challenges.id"), nullable=False),
        sa.Column("target_url", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("host_port", sa.Integer(), nullable=False),
        sa.Column("container_id", sa.String(length=128), nullable=True),
        sa.Column("network_name", sa.String(length=128), nullable=True),
        sa.Column("flag_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_health_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_table(
        "instance_flags",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("instance_id", sa.String(length=64), sa.ForeignKey("challenge_instances.id"), nullable=False, unique=True),
        sa.Column("flag_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("instance_id", sa.String(length=64), sa.ForeignKey("challenge_instances.id"), nullable=False),
        sa.Column("submitted_flag_hash", sa.String(length=128), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("challenge_id", sa.String(length=64), sa.ForeignKey("challenges.id"), nullable=False),
        sa.Column("instance_id", sa.String(length=64), sa.ForeignKey("challenge_instances.id"), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_mode", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("total_duration_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("flag_correct", sa.Boolean(), nullable=False),
        sa.Column("http_request_count", sa.Integer(), nullable=False),
        sa.Column("tool_call_count", sa.Integer(), nullable=False),
        sa.Column("model_call_count", sa.Integer(), nullable=False),
        sa.Column("token_input_count", sa.Integer(), nullable=False),
        sa.Column("token_output_count", sa.Integer(), nullable=False),
        sa.Column("payload_attempts", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("human_intervention_count", sa.Integer(), nullable=False),
        sa.Column("crossed_boundary", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(length=64), nullable=False),
        sa.Column("notes_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("args_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("run_events")
    op.drop_table("tool_calls")
    op.drop_table("agent_runs")
    op.drop_table("submissions")
    op.drop_table("instance_flags")
    op.drop_table("challenge_instances")
    op.drop_table("challenges")

