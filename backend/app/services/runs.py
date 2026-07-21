from __future__ import annotations

import json
from datetime import datetime
from statistics import mean
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AgentRun, EvaluationResult, RunEvent, ToolCall


class RunService:
    def create_run(self, db: Session, *, challenge_id: str, instance_id: str | None, model_name: str, model_mode: str) -> dict:
        run = AgentRun(
            id=f"run-{uuid4()}",
            challenge_id=challenge_id,
            instance_id=instance_id,
            model_name=model_name,
            model_mode=model_mode,
            started_at=datetime.utcnow(),
            total_duration_ms=0,
            success=False,
            flag_correct=False,
            failure_reason="unknown",
            notes_json="{}",
        )
        db.add(run)
        return self._serialize(run)

    def list_runs(self, db: Session) -> list[dict]:
        runs = db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc())).all()
        return [self._serialize(run) for run in runs]

    def get_run(self, db: Session, run_id: str) -> dict:
        run = db.get(AgentRun, run_id)
        if run is None:
            raise KeyError(run_id)
        return self._serialize(run)

    def add_event(self, db: Session, run_id: str, event_type: str, message: str, payload: dict) -> dict:
        run = db.get(AgentRun, run_id)
        if run is None:
            raise KeyError(run_id)
        event = RunEvent(
            id=f"event-{uuid4()}",
            run_id=run.id,
            event_type=event_type,
            message=message,
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )
        db.add(event)
        return {"event_id": event.id, "run_id": run.id}

    def add_tool_call(self, db: Session, run_id: str, tool_name: str, args: dict, result: dict, duration_ms: int) -> dict:
        run = db.get(AgentRun, run_id)
        if run is None:
            raise KeyError(run_id)
        call = ToolCall(
            id=f"tool-{uuid4()}",
            run_id=run.id,
            tool_name=tool_name,
            args_json=json.dumps(args, ensure_ascii=False),
            result_json=json.dumps(result, ensure_ascii=False),
            duration_ms=duration_ms,
            created_at=datetime.utcnow(),
        )
        db.add(call)
        return {"tool_call_id": call.id, "run_id": run.id}

    def finish_run(self, db: Session, run_id: str, payload: dict) -> dict:
        run = db.get(AgentRun, run_id)
        if run is None:
            raise KeyError(run_id)
        run.finished_at = datetime.utcnow()
        run.total_duration_ms = int(payload.get("total_duration_ms", 0))
        run.success = bool(payload["success"])
        run.flag_correct = bool(payload.get("flag_correct", False))
        run.http_request_count = int(payload.get("http_request_count", 0))
        run.tool_call_count = int(payload.get("tool_call_count", 0))
        run.model_call_count = int(payload.get("model_call_count", 0))
        run.token_input_count = int(payload.get("token_input_count", 0))
        run.token_output_count = int(payload.get("token_output_count", 0))
        run.payload_attempts = int(payload.get("payload_attempts", 0))
        run.failure_count = int(payload.get("failure_count", 0))
        run.retry_count = int(payload.get("retry_count", 0))
        run.human_intervention_count = int(payload.get("human_intervention_count", 0))
        run.crossed_boundary = bool(payload.get("crossed_boundary", False))
        run.failure_reason = str(payload.get("failure_reason", "unknown"))
        run.notes_json = json.dumps(payload.get("notes", {}), ensure_ascii=False)
        evaluation = EvaluationResult(
            id=f"eval-{uuid4()}",
            run_id=run.id,
            score=100 if run.success else 0,
            details_json=json.dumps({"success": run.success, "flag_correct": run.flag_correct}, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )
        db.add(evaluation)
        return self._serialize(run)

    def stats(self, db: Session) -> dict:
        runs = db.scalars(select(AgentRun)).all()
        total_runs = len(runs)
        success_runs = sum(1 for item in runs if item.success)
        avg_duration = mean([item.total_duration_ms for item in runs]) if runs else 0.0
        avg_tool_calls = mean([item.tool_call_count for item in runs]) if runs else 0.0
        challenge_map: dict[str, list[AgentRun]] = {}
        for item in runs:
            challenge_map.setdefault(item.challenge_id, []).append(item)
        challenge_success = []
        for challenge_id, challenge_runs in challenge_map.items():
            total = len(challenge_runs)
            passed = sum(1 for item in challenge_runs if item.success)
            challenge_success.append(
                {
                    "challenge_id": challenge_id,
                    "success_rate": round((passed / total) * 100, 2) if total else 0.0,
                    "total": total,
                    "success": passed,
                }
            )
        return {
            "total_runs": total_runs,
            "success_runs": success_runs,
            "success_rate": round((success_runs / total_runs) * 100, 2) if total_runs else 0.0,
            "average_duration_ms": round(avg_duration, 2),
            "average_tool_calls": round(avg_tool_calls, 2),
            "challenge_success": challenge_success,
        }

    @staticmethod
    def _serialize(run: AgentRun) -> dict:
        return {
            "id": run.id,
            "challenge_id": run.challenge_id,
            "instance_id": run.instance_id,
            "model_name": run.model_name,
            "model_mode": run.model_mode,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "total_duration_ms": run.total_duration_ms,
            "success": run.success,
            "flag_correct": run.flag_correct,
            "http_request_count": run.http_request_count,
            "tool_call_count": run.tool_call_count,
            "model_call_count": run.model_call_count,
            "token_input_count": run.token_input_count,
            "token_output_count": run.token_output_count,
            "payload_attempts": run.payload_attempts,
            "failure_count": run.failure_count,
            "retry_count": run.retry_count,
            "human_intervention_count": run.human_intervention_count,
            "crossed_boundary": run.crossed_boundary,
            "failure_reason": run.failure_reason,
        }


run_service = RunService()
