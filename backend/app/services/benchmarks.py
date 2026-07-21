from __future__ import annotations
import csv, io, json, secrets
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import BenchmarkExperiment, BenchmarkRun, BenchmarkResult, RunStageEvent

class BenchmarkService:
    def create(self, db: Session, payload: dict) -> dict:
        exp = BenchmarkExperiment(id=f"exp-{uuid4()}", name=payload["name"], description=payload.get("description", ""), dataset=payload.get("dataset", "core"), model_name=payload.get("model_name", "manual-agent"), model_provider=payload.get("model_provider", "manual"), agent_version=payload.get("agent_version", "unknown"), prompt_version=payload.get("prompt_version", "unknown"), toolset_version=payload.get("toolset_version", "unknown"), variant_level=int(payload.get("variant_level", 0)), repeat_count=max(1, int(payload.get("repeat_count", 1))), status="created", configuration_json=json.dumps(payload, ensure_ascii=False))
        db.add(exp); db.flush(); return self.serialize_experiment(exp)

    def start(self, db: Session, exp_id: str) -> dict:
        exp = db.get(BenchmarkExperiment, exp_id)
        if not exp: raise KeyError(exp_id)
        if exp.status not in ("created", "paused"): raise ValueError("experiment cannot be started")
        ids = json.loads(exp.configuration_json).get("challenge_ids", [])
        exp.status = "running"; exp.started_at = exp.started_at or datetime.utcnow()
        for challenge_id in ids:
            for index in range(1, exp.repeat_count + 1):
                db.add(BenchmarkRun(id=f"brun-{uuid4()}", experiment_id=exp.id, challenge_id=challenge_id, variant_seed=secrets.randbelow(2**31) if exp.variant_level else 0, run_index=index, status="created", primary_failure="unknown", last_completed_stage="target_access"))
        db.flush(); return self.serialize_experiment(exp)

    @staticmethod
    def serialize_experiment(x):
        return {"id": x.id, "name": x.name, "status": x.status, "repeat_count": x.repeat_count, "variant_level": x.variant_level, "model_name": x.model_name, "created_at": x.created_at, "started_at": x.started_at, "finished_at": x.finished_at}
    @staticmethod
    def serialize_run(x):
        return {"id": x.id, "experiment_id": x.experiment_id, "challenge_id": x.challenge_id, "instance_id": x.instance_id, "variant_seed": x.variant_seed, "run_index": x.run_index, "status": x.status, "success": x.success, "flag_submitted": x.flag_submitted, "flag_correct": x.flag_correct, "score": x.score, "primary_failure": x.primary_failure, "last_completed_stage": x.last_completed_stage, "duration_ms": x.duration_ms, "request_count": x.request_count}
    def export(self, db, exp_id, fmt):
        rows = [self.serialize_run(x) for x in db.scalars(select(BenchmarkRun).where(BenchmarkRun.experiment_id == exp_id)).all()]
        if fmt == "csv":
            out = io.StringIO(); fields = ["experiment_id","id","challenge_id","run_index","variant_seed","success","score","duration_ms","request_count","primary_failure","last_completed_stage"]; w=csv.DictWriter(out, fieldnames=fields); w.writeheader(); w.writerows({k:r.get(k) for k in fields} for r in rows); return out.getvalue()
        return rows
benchmark_service = BenchmarkService()
