from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    image_name: Mapped[str] = mapped_column(String(255), nullable=False)
    build_context: Mapped[str] = mapped_column(String(255), nullable=False)
    dockerfile_path: Mapped[str] = mapped_column(String(255), nullable=False)
    entry_path: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_port: Mapped[int] = mapped_column(Integer, nullable=False)
    runtime_max_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    runtime_memory_limit: Mapped[str] = mapped_column(String(32), nullable=False)
    runtime_cpu_limit: Mapped[str] = mapped_column(String(32), nullable=False)
    allow_internet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_bruteforce: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_port_scan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    instances: Mapped[list["ChallengeInstance"]] = relationship(back_populates="challenge")


class ChallengeInstance(Base):
    __tablename__ = "challenge_instances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(64), ForeignKey("challenges.id"), nullable=False)
    target_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    host_port: Mapped[int] = mapped_column(Integer, nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    network_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    flag_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_seed: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    challenge: Mapped["Challenge"] = relationship(back_populates="instances")
    flag_record: Mapped["InstanceFlag"] = relationship(back_populates="instance", uselist=False)
    submissions: Mapped[list["Submission"]] = relationship(back_populates="instance")


class InstanceFlag(Base):
    __tablename__ = "instance_flags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(64), ForeignKey("challenge_instances.id"), unique=True, nullable=False)
    flag_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    instance: Mapped["ChallengeInstance"] = relationship(back_populates="flag_record")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(64), ForeignKey("challenge_instances.id"), nullable=False)
    submitted_flag_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    instance: Mapped["ChallengeInstance"] = relationship(back_populates="submissions")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(64), ForeignKey("challenges.id"), nullable=False)
    instance_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("challenge_instances.id"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    http_request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_input_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_output_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    human_intervention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crossed_boundary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    notes_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    events: Mapped[list["RunEvent"]] = relationship(back_populates="run")
    tool_calls: Mapped[list["ToolCall"]] = relationship(back_populates="run")
    evaluation: Mapped["EvaluationResult"] = relationship(back_populates="run", uselist=False)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    args_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    run: Mapped["AgentRun"] = relationship(back_populates="tool_calls")


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    run: Mapped["AgentRun"] = relationship(back_populates="events")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("agent_runs.id"), nullable=False, unique=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    run: Mapped["AgentRun"] = relationship(back_populates="evaluation")


class BenchmarkExperiment(Base):
    __tablename__ = "benchmark_experiments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    dataset: Mapped[str] = mapped_column(String(128), default="core", nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(128), default="manual", nullable=False)
    agent_version: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    toolset_version: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    variant_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repeat_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    configuration_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(64), ForeignKey("benchmark_experiments.id"), nullable=False)
    challenge_id: Mapped[str] = mapped_column(String(64), nullable=False)
    instance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    variant_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_intervention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary_failure: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    last_completed_stage: Mapped[str] = mapped_column(String(64), default="target_access", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RunStageEvent(Base):
    __tablename__ = "run_stage_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("benchmark_runs.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("benchmark_runs.id"), unique=True, nullable=False)
    discovery_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hypothesis_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exploitation_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    efficiency_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary_failure: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    secondary_failures_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evaluation_details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ChallengeVariant(Base):
    __tablename__ = "challenge_variants"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_level: Mapped[int] = mapped_column(Integer, nullable=False)
    variant_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    route_mapping_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    parameter_mapping_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    content_mapping_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class HintUsage(Base):
    __tablename__ = "hint_usage"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    challenge_id: Mapped[str] = mapped_column(String(64), nullable=False)
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    penalty_score: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
