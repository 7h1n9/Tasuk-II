from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Challenge, ChallengeInstance
from ..registry import ChallengeDefinition, registry


class ChallengeService:
    def refresh_registry(self, db: Session) -> None:
        registry.load()
        active_ids = {item.id for item in registry.all()}
        for existing in db.scalars(select(Challenge)).all():
            existing.is_active = existing.id in active_ids
        for item in registry.all():
            existing = db.get(Challenge, item.id)
            payload = json.dumps(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "difficulty": item.difficulty,
                    "version": item.version,
                    "description": item.description,
                    "entry": item.entry,
                    "objective": item.objective,
                    "runtime": item.runtime,
                    "constraints": item.constraints,
                    "tags": item.tags,
                    "guide": item.guide,
                },
                ensure_ascii=False,
            )
            if existing is None:
                db.add(
                    Challenge(
                        id=item.id,
                        name=item.name,
                        category=item.category,
                        difficulty=item.difficulty,
                        version=item.version,
                        description=item.description,
                        metadata_json=payload,
                        image_name=item.image_name,
                        build_context=item.build_context,
                        dockerfile_path=item.dockerfile_path,
                        entry_path=item.entry["path"],
                        internal_port=int(item.entry["internal_port"]),
                        runtime_max_seconds=int(item.runtime["max_seconds"]),
                        runtime_memory_limit=str(item.runtime["memory_limit"]),
                        runtime_cpu_limit=str(item.runtime["cpu_limit"]),
                        allow_internet=bool(item.constraints.get("allow_internet", False)),
                        allow_bruteforce=bool(item.constraints.get("allow_bruteforce", False)),
                        allow_port_scan=bool(item.constraints.get("allow_port_scan", False)),
                        max_requests=int(item.constraints.get("max_requests", 300)),
                        tags_json=json.dumps(item.tags, ensure_ascii=False),
                        is_active=True,
                    )
                )
            else:
                existing.name = item.name
                existing.category = item.category
                existing.difficulty = item.difficulty
                existing.version = item.version
                existing.description = item.description
                existing.metadata_json = payload
                existing.image_name = item.image_name
                existing.build_context = item.build_context
                existing.dockerfile_path = item.dockerfile_path
                existing.entry_path = item.entry["path"]
                existing.internal_port = int(item.entry["internal_port"])
                existing.runtime_max_seconds = int(item.runtime["max_seconds"])
                existing.runtime_memory_limit = str(item.runtime["memory_limit"])
                existing.runtime_cpu_limit = str(item.runtime["cpu_limit"])
                existing.allow_internet = bool(item.constraints.get("allow_internet", False))
                existing.allow_bruteforce = bool(item.constraints.get("allow_bruteforce", False))
                existing.allow_port_scan = bool(item.constraints.get("allow_port_scan", False))
                existing.max_requests = int(item.constraints.get("max_requests", 300))
                existing.tags_json = json.dumps(item.tags, ensure_ascii=False)
                existing.is_active = True

    def list_challenges(self, db: Session) -> list[dict]:
        challenges = db.scalars(select(Challenge).where(Challenge.is_active.is_(True)).order_by(Challenge.id)).all()
        instance_counts = Counter(
            db.scalars(select(ChallengeInstance.challenge_id).where(ChallengeInstance.status.in_(["running", "starting"]))).all()
        )
        result: list[dict] = []
        for challenge in challenges:
            metadata = json.loads(challenge.metadata_json)
            result.append(
                {
                    "id": challenge.id,
                    "name": challenge.name,
                    "category": challenge.category,
                    "difficulty": challenge.difficulty,
                    "description": challenge.description,
                    "available": challenge.is_active,
                    "current_instances": int(instance_counts.get(challenge.id, 0)),
                    "entry": metadata["entry"],
                    "tags": json.loads(challenge.tags_json),
                    "version": challenge.version,
                    "objective": metadata["objective"],
                    "runtime": metadata["runtime"],
                    "constraints": metadata["constraints"],
                    "guide": metadata.get("guide", {}),
                }
            )
        return result

    def get_challenge(self, db: Session, challenge_id: str) -> dict:
        challenge = db.get(Challenge, challenge_id)
        if challenge is None:
            raise KeyError(challenge_id)
        metadata = json.loads(challenge.metadata_json)
        return {
            "id": challenge.id,
            "name": challenge.name,
            "category": challenge.category,
            "difficulty": challenge.difficulty,
            "description": challenge.description,
            "available": challenge.is_active,
            "current_instances": len(
                db.scalars(select(ChallengeInstance).where(ChallengeInstance.challenge_id == challenge.id, ChallengeInstance.status.in_(["running", "starting"]))).all()
            ),
            "entry": metadata["entry"],
            "tags": json.loads(challenge.tags_json),
            "version": challenge.version,
            "objective": metadata["objective"],
            "runtime": metadata["runtime"],
            "constraints": metadata["constraints"],
            "guide": metadata.get("guide", {}),
        }


challenge_service = ChallengeService()
