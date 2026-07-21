from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Challenge, ChallengeInstance
from ..registry import registry


class ChallengeService:
    def refresh_registry(self, db: Session) -> None:
        registry.load()
        active_ids = {item.id for item in registry.all()}
        for existing in db.scalars(select(Challenge)).all():
            existing.is_active = existing.id in active_ids
        for item in registry.all():
            existing = db.get(Challenge, item.id)
            payload = json.dumps({
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "difficulty": item.difficulty,
                "version": item.version,
                "description": item.description,
                "starting_point": item.starting_point,
                "entry": item.entry,
                "objective": item.objective,
                "runtime": item.runtime,
                "constraints": item.constraints,
                "tags": item.tags,
                "hints": item.hints,
                "legacy": item.legacy,
            }, ensure_ascii=False)
            values = dict(
                name=item.name, category=item.category, difficulty=item.difficulty,
                version=item.version, description=item.description, metadata_json=payload,
                image_name=item.image_name, build_context=item.build_context,
                dockerfile_path=item.dockerfile_path, entry_path=item.entry["path"],
                internal_port=int(item.entry["internal_port"]),
                runtime_max_seconds=int(item.runtime.get("max_seconds", 900)),
                runtime_memory_limit=str(item.runtime.get("memory_limit", "256m")),
                runtime_cpu_limit=str(item.runtime.get("cpu_limit", 0.5)),
                allow_internet=bool(item.constraints.get("allow_internet", False)),
                allow_bruteforce=bool(item.constraints.get("allow_bruteforce", False)),
                allow_port_scan=bool(item.constraints.get("allow_port_scan", False)),
                max_requests=int(item.constraints.get("max_requests", 300)),
                tags_json=json.dumps(item.tags, ensure_ascii=False), is_active=True,
            )
            if existing is None:
                db.add(Challenge(id=item.id, **values))
            else:
                for key, value in values.items():
                    setattr(existing, key, value)

    @staticmethod
    def _public(challenge: Challenge, metadata: dict, current_instances: int) -> dict:
        return {
            "id": challenge.id, "name": challenge.name, "category": challenge.category,
            "difficulty": challenge.difficulty, "description": challenge.description,
            "available": challenge.is_active, "current_instances": current_instances,
            "starting_point": metadata.get("starting_point", "从实例首页开始观察业务入口。"),
            "entry": metadata["entry"], "tags": json.loads(challenge.tags_json),
            "version": challenge.version, "objective": metadata["objective"],
            "runtime": metadata["runtime"], "constraints": metadata["constraints"],
            "legacy": bool(metadata.get("legacy", False)),
        }

    def list_challenges(self, db: Session) -> list[dict]:
        challenges = db.scalars(select(Challenge).where(Challenge.is_active.is_(True)).order_by(Challenge.id)).all()
        counts = Counter(db.scalars(select(ChallengeInstance.challenge_id).where(ChallengeInstance.status.in_(["running", "starting"]))).all())
        return [self._public(c, json.loads(c.metadata_json), int(counts.get(c.id, 0))) for c in challenges]

    def get_challenge(self, db: Session, challenge_id: str) -> dict:
        challenge = db.get(Challenge, challenge_id)
        if challenge is None or not challenge.is_active:
            raise KeyError(challenge_id)
        count = len(db.scalars(select(ChallengeInstance).where(ChallengeInstance.challenge_id == challenge.id, ChallengeInstance.status.in_(["running", "starting"]))).all())
        return self._public(challenge, json.loads(challenge.metadata_json), count)

    def get_hints(self, db: Session, challenge_id: str, level: int | None) -> dict:
        challenge = db.get(Challenge, challenge_id)
        if challenge is None or not challenge.is_active:
            raise KeyError(challenge_id)
        hints = json.loads(challenge.metadata_json).get("hints", [])
        if level is None:
            return {"challenge_id": challenge_id, "available_levels": [int(x["level"]) for x in hints]}
        match = next((x for x in hints if int(x["level"]) == level), None)
        if match is None:
            raise ValueError("hint level unavailable")
        return {"challenge_id": challenge_id, "level": level, "text": match["text"], "penalty": int(match.get("penalty", 0))}


challenge_service = ChallengeService()
