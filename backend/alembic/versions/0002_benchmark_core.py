"""add benchmark experiment and evaluation tables"""
from alembic import op
import sqlalchemy as sa

revision = "0002_benchmark_core"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade() -> None:
    common = [sa.Column("id", sa.String(64), primary_key=True)]
    op.create_table("benchmark_experiments", *common,
        sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("dataset", sa.String(128), nullable=False), sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_provider", sa.String(128), nullable=False), sa.Column("agent_version", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False), sa.Column("toolset_version", sa.String(64), nullable=False),
        sa.Column("variant_level", sa.Integer(), nullable=False), sa.Column("repeat_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime()), sa.Column("finished_at", sa.DateTime()), sa.Column("configuration_json", sa.Text(), nullable=False))
    op.create_table("benchmark_runs", *common,
        sa.Column("experiment_id", sa.String(64), sa.ForeignKey("benchmark_experiments.id"), nullable=False), sa.Column("challenge_id", sa.String(64), nullable=False), sa.Column("instance_id", sa.String(64)),
        sa.Column("variant_seed", sa.Integer(), nullable=False), sa.Column("run_index", sa.Integer(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("success", sa.Boolean(), nullable=False), sa.Column("flag_submitted", sa.Boolean(), nullable=False), sa.Column("flag_correct", sa.Boolean(), nullable=False), sa.Column("started_at", sa.DateTime()), sa.Column("finished_at", sa.DateTime()), sa.Column("duration_ms", sa.Integer(), nullable=False), sa.Column("request_count", sa.Integer(), nullable=False), sa.Column("tool_call_count", sa.Integer(), nullable=False), sa.Column("model_call_count", sa.Integer(), nullable=False), sa.Column("input_tokens", sa.Integer(), nullable=False), sa.Column("output_tokens", sa.Integer(), nullable=False), sa.Column("retry_count", sa.Integer(), nullable=False), sa.Column("payload_attempt_count", sa.Integer(), nullable=False), sa.Column("manual_intervention_count", sa.Integer(), nullable=False), sa.Column("safety_violation_count", sa.Integer(), nullable=False), sa.Column("primary_failure", sa.String(64), nullable=False), sa.Column("last_completed_stage", sa.String(64), nullable=False), sa.Column("score", sa.Integer(), nullable=False))
    op.create_table("run_stage_events", *common, sa.Column("run_id", sa.String(64), sa.ForeignKey("benchmark_runs.id"), nullable=False), sa.Column("stage", sa.String(64), nullable=False), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("source", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("evidence_type", sa.String(64), nullable=False), sa.Column("evidence_summary", sa.Text(), nullable=False), sa.Column("metadata_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("benchmark_results", *common, sa.Column("run_id", sa.String(64), sa.ForeignKey("benchmark_runs.id"), unique=True, nullable=False), sa.Column("discovery_score", sa.Integer(), nullable=False), sa.Column("hypothesis_score", sa.Integer(), nullable=False), sa.Column("exploitation_score", sa.Integer(), nullable=False), sa.Column("completion_score", sa.Integer(), nullable=False), sa.Column("efficiency_score", sa.Integer(), nullable=False), sa.Column("total_score", sa.Integer(), nullable=False), sa.Column("primary_failure", sa.String(64), nullable=False), sa.Column("secondary_failures_json", sa.Text(), nullable=False), sa.Column("evaluation_details_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("challenge_variants", *common, sa.Column("challenge_id", sa.String(64), nullable=False), sa.Column("variant_level", sa.Integer(), nullable=False), sa.Column("variant_seed", sa.Integer(), nullable=False), sa.Column("route_mapping_json", sa.Text(), nullable=False), sa.Column("parameter_mapping_json", sa.Text(), nullable=False), sa.Column("content_mapping_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("hint_usage", *common, sa.Column("run_id", sa.String(64), nullable=False), sa.Column("challenge_id", sa.String(64), nullable=False), sa.Column("hint_level", sa.Integer(), nullable=False), sa.Column("requested_at", sa.DateTime(), nullable=False), sa.Column("penalty_score", sa.Integer(), nullable=False))

def downgrade() -> None:
    for name in ("hint_usage", "challenge_variants", "benchmark_results", "run_stage_events", "benchmark_runs", "benchmark_experiments"):
        op.drop_table(name)
