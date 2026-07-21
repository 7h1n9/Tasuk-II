from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings


@dataclass(slots=True)
class ChallengeDefinition:
    id: str
    name: str
    category: str
    difficulty: str
    version: str
    description: str
    starting_point: str
    entry: dict[str, Any]
    objective: dict[str, Any]
    runtime: dict[str, Any]
    constraints: dict[str, Any]
    tags: list[str]
    hints: list[dict[str, Any]]
    legacy: bool
    image_name: str
    build_context: str
    dockerfile_path: str
    metadata_path: str


class ChallengeRegistry:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._challenges: dict[str, ChallengeDefinition] = {}

    def load(self) -> None:
        registry_path = self.settings.challenge_registry_path
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        loaded: dict[str, ChallengeDefinition] = {}
        for item in payload.get("challenges", []):
            challenge_id = str(item["id"])
            if not challenge_id.startswith("core-"):
                continue
            metadata_path = (self.settings.project_root / item["metadata_path"]).resolve()
            raw = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            legacy = "public" not in raw
            public = dict(raw.get("public", raw))
            if legacy:
                # Legacy entries remain runnable, but are explicitly marked and
                # never expose their implementation metadata through the API.
                public = {
                    "name": f"待重构题目 {challenge_id}",
                    "category": "legacy",
                    "difficulty": "legacy",
                    "description": "该题目尚未迁移到可发现业务规范。",
                    "starting_point": "从实例首页开始观察业务入口。",
                    "entry": {"protocol": "http", "internal_port": raw.get("internal_port", 5000), "path": "/"},
                    "objective": "获取格式为 flag{...} 的字符串",
                    "constraints": {"max_requests": 300, "allow_bruteforce": False, "allow_port_scan": False},
                    "tags": ["legacy"],
                    "hints": [],
                }
            public["entry"] = public.get("entry", {"protocol": "http", "internal_port": 5000, "path": "/"})
            public["objective"] = public.get("objective", "获取格式为 flag{...} 的字符串")
            objective = public["objective"] if isinstance(public["objective"], dict) else {"type": "flag", "format": "flag{...}"}
            loaded[challenge_id] = ChallengeDefinition(
                id=challenge_id,
                name=str(public.get("name", challenge_id)),
                category=str(public.get("category", "uncategorized")),
                difficulty=str(public.get("difficulty", "unknown")),
                version=str(raw.get("version", "1.0.0")),
                description=str(public.get("description", "")),
                starting_point=str(public.get("starting_point", "从实例首页开始观察业务入口。")),
                entry=dict(public["entry"]),
                objective=objective,
                runtime=dict(public.get("runtime", {"max_seconds": 900, "memory_limit": "256m", "cpu_limit": 0.5})),
                constraints=dict(public.get("constraints", {})),
                tags=list(public.get("tags", [])),
                hints=list(public.get("hints", [])),
                legacy=legacy,
                image_name=item["image_name"],
                build_context=item.get("build_context", "."),
                dockerfile_path=item["dockerfile_path"],
                metadata_path=str(metadata_path),
            )
        self._challenges = loaded

    def all(self) -> list[ChallengeDefinition]:
        return list(self._challenges.values())

    def get(self, challenge_id: str) -> ChallengeDefinition:
        if challenge_id not in self._challenges:
            raise KeyError(challenge_id)
        return self._challenges[challenge_id]


registry = ChallengeRegistry()
