from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import Base, engine, ensure_compatibility_schema, get_db
from .models import *  # noqa: F401,F403
from .schemas import (
    Envelope,
    ErrorEnvelope,
    InstanceCreateRequest,
    InstanceResetRequest,
    InstanceResponse,
    InstanceSubmitRequest,
    InstanceSubmitResponse,
    RunCreateRequest,
    RunEventCreateRequest,
    RunFinishRequest,
    RunSummary,
    StatsSummary,
)
from .services.challenges import challenge_service
from .services.instances import instance_service
from .services.runs import run_service
from .services.benchmarks import benchmark_service


def envelope(data: Any = None, message: str = "ok", success: bool = True) -> dict[str, Any]:
    return {"success": success, "message": message, "data": data}


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/challenges")
    def list_challenges(db: Session = Depends(get_db)) -> dict[str, Any]:
        return envelope({"items": challenge_service.list_challenges(db)})

    @router.get("/challenges/{challenge_id}/hints")
    def get_hint_levels(challenge_id: str, level: int | None = None, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            result = challenge_service.get_hints(db, challenge_id, level)
            return envelope(result)
        except KeyError:
            raise HTTPException(status_code=404, detail="challenge not found")
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/challenges/{challenge_id}")
    def get_challenge(challenge_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(challenge_service.get_challenge(db, challenge_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="challenge not found")

    @router.post("/instances")
    def create_instance(payload: InstanceCreateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(instance_service.create_instance(db, payload.challenge_id), "created")
        except KeyError:
            raise HTTPException(status_code=404, detail="challenge not found")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get("/instances")
    def list_instances(db: Session = Depends(get_db)) -> dict[str, Any]:
        return envelope({"items": instance_service.list_instances(db)})

    @router.get("/instances/{instance_id}")
    def get_instance(instance_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(instance_service.get_instance(db, instance_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="instance not found")

    @router.post("/instances/{instance_id}/reset")
    def reset_instance(instance_id: str, payload: InstanceResetRequest | None = None, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            regenerate_variant = payload.regenerate_variant if payload is not None else False
            return envelope(instance_service.reset_instance(db, instance_id, regenerate_variant), "reset")
        except KeyError:
            raise HTTPException(status_code=404, detail="instance not found")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc))

    @router.delete("/instances/{instance_id}")
    def destroy_instance(instance_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(instance_service.destroy_instance(db, instance_id), "destroyed")
        except KeyError:
            raise HTTPException(status_code=404, detail="instance not found")

    @router.post("/instances/{instance_id}/submit")
    def submit_flag(instance_id: str, payload: InstanceSubmitRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            result = instance_service.submit_flag(db, instance_id, payload.flag)
            message = "Flag correct" if result["correct"] else "Flag incorrect"
            return envelope(result, message)
        except KeyError:
            raise HTTPException(status_code=404, detail="instance not found")

    @router.get("/runs")
    def list_runs(db: Session = Depends(get_db)) -> dict[str, Any]:
        return envelope({"items": run_service.list_runs(db)})

    @router.post("/runs")
    def create_run(payload: RunCreateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
        return envelope(run_service.create_run(db, challenge_id=payload.challenge_id, instance_id=payload.instance_id, model_name=payload.model_name, model_mode=payload.model_mode), "created")

    @router.get("/runs/{run_id}")
    def get_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(run_service.get_run(db, run_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found")

    @router.post("/runs/{run_id}/events")
    def create_run_event(run_id: str, payload: RunEventCreateRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(run_service.add_event(db, run_id, payload.event_type, payload.message, payload.payload), "created")
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found")

    @router.post("/runs/{run_id}/hints/{level}")
    def request_hint(run_id: str, level: int, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            run_record = db.get(AgentRun, run_id)
            if run_record is None:
                raise KeyError(run_id)
            used_levels = {
                int(json.loads(event.payload_json).get("level"))
                for event in db.scalars(select(RunEvent).where(RunEvent.run_id == run_id, RunEvent.event_type == "hint_used")).all()
            }
            if level > 1 and any(previous not in used_levels for previous in range(1, level)):
                raise HTTPException(status_code=409, detail="request previous hint levels first")
            run = run_service.get_run(db, run_id)
            hint = challenge_service.get_hints(db, run["challenge_id"], level)
            db.add(HintUsage(id=f"hint-{uuid4()}", challenge_id=run["challenge_id"], run_id=run_id, hint_level=level, penalty_score=hint["penalty"]))
            event = run_service.add_event(
                db, run_id, "hint_used", f"hint level {level} requested",
                {"level": level, "penalty": hint["penalty"]},
            )
            return envelope({**hint, "event_id": event["event_id"]}, "hint returned")
        except KeyError:
            raise HTTPException(status_code=404, detail="run or challenge not found")
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.post("/runs/{run_id}/tool-calls")
    def create_tool_call(run_id: str, payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(
                run_service.add_tool_call(
                    db,
                    run_id,
                    str(payload.get("tool_name", "unknown")),
                    dict(payload.get("args", {})),
                    dict(payload.get("result", {})),
                    int(payload.get("duration_ms", 0)),
                ),
                "created",
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found")

    @router.post("/runs/{run_id}/finish")
    def finish_run(run_id: str, payload: RunFinishRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
        try:
            return envelope(run_service.finish_run(db, run_id, payload.model_dump()), "finished")
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found")

    @router.get("/stats")
    def get_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
        return envelope(run_service.stats(db))

    @router.post("/benchmark/experiments")
    def create_experiment(payload: dict[str, Any], db: Session = Depends(get_db)):
        return envelope(benchmark_service.create(db, payload), "created")

    @router.get("/benchmark/experiments")
    def list_experiments(db: Session = Depends(get_db)):
        items = db.scalars(select(BenchmarkExperiment).order_by(BenchmarkExperiment.created_at.desc())).all()
        return envelope({"items": [benchmark_service.serialize_experiment(x) for x in items]})

    @router.post("/benchmark/experiments/{experiment_id}/start")
    def start_experiment(experiment_id: str, db: Session = Depends(get_db)):
        try: return envelope(benchmark_service.start(db, experiment_id), "started")
        except KeyError: raise HTTPException(status_code=404, detail="experiment not found")

    @router.get("/benchmark/experiments/{experiment_id}/runs")
    def experiment_runs(experiment_id: str, db: Session = Depends(get_db)):
        items = db.scalars(select(BenchmarkRun).where(BenchmarkRun.experiment_id == experiment_id).order_by(BenchmarkRun.run_index)).all()
        return envelope({"items": [benchmark_service.serialize_run(x) for x in items]})

    @router.get("/benchmark/experiments/{experiment_id}/export")
    def export_experiment(experiment_id: str, format: str = "json", db: Session = Depends(get_db)):
        if format not in ("json", "csv"): raise HTTPException(status_code=400, detail="format must be json or csv")
        return envelope(benchmark_service.export(db, experiment_id, format))

    return router


def build_app() -> FastAPI:
    app = FastAPI(title="ctf-agent-range", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_router())

    @app.exception_handler(HTTPException)
    def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": str(exc.detail), "error": {"status_code": exc.status_code}},
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return envelope({"status": "ok"}, "healthy")

    @app.on_event("startup")
    def startup() -> None:
        Base.metadata.create_all(bind=engine)
        ensure_compatibility_schema()
        from .services.challenges import challenge_service

        from .database import SessionLocal

        with SessionLocal() as db:
            challenge_service.refresh_registry(db)
            db.commit()

    return app


app = build_app()
