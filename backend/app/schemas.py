from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    success: bool = True
    message: str = "ok"
    data: Any = None


class ErrorEnvelope(BaseModel):
    success: bool = False
    message: str
    error: dict[str, Any] = Field(default_factory=dict)


class ChallengeSummary(BaseModel):
    id: str
    name: str
    category: str
    difficulty: str
    description: str
    available: bool
    current_instances: int
    entry: dict[str, Any]
    tags: list[str]
    starting_point: str = ""
    legacy: bool = False


class ChallengeDetail(ChallengeSummary):
    version: str
    objective: dict[str, Any]
    runtime: dict[str, Any]
    constraints: dict[str, Any]


class InstanceCreateRequest(BaseModel):
    challenge_id: str


class InstanceResponse(BaseModel):
    instance_id: str
    challenge_id: str
    target_url: str
    status: str
    expires_at: datetime
    created_at: datetime
    host_port: int


class InstanceSubmitRequest(BaseModel):
    flag: str


class InstanceSubmitResponse(BaseModel):
    correct: bool
    submission_id: str
    message: str


class RunCreateRequest(BaseModel):
    challenge_id: str
    instance_id: str | None = None
    model_name: str = "unknown"
    model_mode: str = "unknown"


class RunEventCreateRequest(BaseModel):
    event_type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ToolCallCreateRequest(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


class RunFinishRequest(BaseModel):
    success: bool
    flag_correct: bool = False
    http_request_count: int = 0
    tool_call_count: int = 0
    model_call_count: int = 0
    token_input_count: int = 0
    token_output_count: int = 0
    payload_attempts: int = 0
    failure_count: int = 0
    retry_count: int = 0
    human_intervention_count: int = 0
    crossed_boundary: bool = False
    failure_reason: str = "unknown"
    notes: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    id: str
    challenge_id: str
    instance_id: str | None
    model_name: str
    model_mode: str
    started_at: datetime
    finished_at: datetime | None
    total_duration_ms: int
    success: bool
    flag_correct: bool
    http_request_count: int
    tool_call_count: int
    model_call_count: int
    token_input_count: int
    token_output_count: int
    payload_attempts: int
    failure_count: int
    retry_count: int
    human_intervention_count: int
    crossed_boundary: bool
    failure_reason: str


class StatsSummary(BaseModel):
    total_runs: int
    success_runs: int
    success_rate: float
    average_duration_ms: float
    average_tool_calls: float
    challenge_success: list[dict[str, Any]]
