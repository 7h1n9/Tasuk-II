from __future__ import annotations

import hashlib
import random
import secrets
import socket
from pathlib import Path
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from docker.errors import APIError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Challenge, ChallengeInstance, InstanceFlag, Submission
from .docker_manager import docker_manager


class InstanceService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _hash_flag(flag: str) -> str:
        return hashlib.sha256(flag.encode("utf-8")).hexdigest()

    @staticmethod
    def _new_flag() -> str:
        return f"flag{{{secrets.token_hex(16)}}}"

    @staticmethod
    def _new_variant_seed() -> str:
        return secrets.token_urlsafe(12)

    def _port_is_available(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return True
            except OSError:
                return False

    def _candidate_ports(self, db: Session) -> list[int]:
        taken = {
            row[0]
            for row in db.execute(select(ChallengeInstance.host_port).where(ChallengeInstance.status.in_(["starting", "running", "resetting"]))).all()
        }
        taken.add(self.settings.backend_port)
        candidates = [
            port
            for port in range(self.settings.instance_port_min, self.settings.instance_port_max + 1)
            if port not in taken and self._port_is_available(port)
        ]
        random.shuffle(candidates)
        return candidates

    def _instance_target_url(self, host_port: int) -> str:
        public_port = host_port + self.settings.instance_public_port_offset
        return f"http://{self.settings.instance_public_host}:{public_port}"

    def create_instance(self, db: Session, challenge_id: str) -> dict[str, Any]:
        challenge = db.get(Challenge, challenge_id)
        if challenge is None or not challenge.is_active:
            raise KeyError(challenge_id)

        flag = self._new_flag()
        flag_hash = self._hash_flag(flag)
        variant_seed = self._new_variant_seed()
        instance_id = f"instance-{uuid4()}"
        expires_at = datetime.utcnow() + timedelta(seconds=self.settings.instance_ttl_seconds)
        docker_manager.build_if_needed(
            image_name=challenge.image_name,
            dockerfile=challenge.dockerfile_path,
            path=str((self.settings.project_root / challenge.build_context).resolve()),
        )

        container_id = None
        network_name = None
        host_port = None
        last_error: Exception | None = None
        for candidate_port in self._candidate_ports(db):
            host_port = candidate_port
            network_name = f"{self.settings.instance_network_prefix}-{instance_id}-{host_port}"
            docker_container = None
            try:
                docker_container = docker_manager.run_container(
                    image_name=challenge.image_name,
                    container_name=f"cfr-{challenge.id}-{instance_id}-{host_port}",
                    challenge_id=challenge.id,
                    flag=flag,
                    network_name=network_name,
                    host_port=host_port,
                    internal_port=challenge.internal_port,
                    memory_limit=challenge.runtime_memory_limit,
                cpu_limit=challenge.runtime_cpu_limit,
                    extra_env={"VARIANT_SEED": variant_seed, "INSTANCE_ID": instance_id},
                )
                docker_manager.wait_healthy(host_port)
                container_id = docker_container.container_id
                break
            except APIError as exc:
                last_error = exc
                if docker_container is not None:
                    with suppress(Exception):
                        docker_manager.remove_container(docker_container.container_id)
                message = str(exc).lower()
                if "port is already allocated" not in message and "bind" not in message:
                    if network_name:
                        with suppress(Exception):
                            docker_manager.remove_network(network_name)
                    raise
                if network_name:
                    with suppress(Exception):
                        docker_manager.remove_network(network_name)
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if docker_container is not None:
                    with suppress(Exception):
                        docker_manager.remove_container(docker_container.container_id)
                if network_name:
                    with suppress(Exception):
                        docker_manager.remove_network(network_name)
                raise

        if container_id is None or host_port is None or network_name is None:
            raise RuntimeError(f"no free instance ports: {last_error}")

        instance = ChallengeInstance(
            id=instance_id,
            challenge_id=challenge.id,
            target_url=self._instance_target_url(host_port),
            status="running",
            host_port=host_port,
            container_id=container_id,
            network_name=network_name,
            flag_hash=flag_hash,
            variant_seed=variant_seed,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            updated_at=datetime.utcnow(),
            last_health_at=datetime.utcnow(),
        )
        db.add(instance)
        db.flush()
        db.add(InstanceFlag(id=f"flag-{instance_id}", instance_id=instance_id, flag_hash=flag_hash))

        return {
            "instance_id": instance.id,
            "challenge_id": instance.challenge_id,
            "target_url": self._instance_target_url(instance.host_port),
            "status": instance.status,
            "expires_at": instance.expires_at,
            "created_at": instance.created_at,
            "host_port": instance.host_port,
        }

    def get_instance(self, db: Session, instance_id: str) -> dict[str, Any]:
        instance = db.get(ChallengeInstance, instance_id)
        if instance is None:
            raise KeyError(instance_id)
        challenge = db.get(Challenge, instance.challenge_id)
        return {
            "instance_id": instance.id,
            "challenge_id": instance.challenge_id,
            "challenge_name": challenge.name if challenge else instance.challenge_id,
            "target_url": self._instance_target_url(instance.host_port),
            "status": instance.status,
            "host_port": instance.host_port,
            "created_at": instance.created_at,
            "expires_at": instance.expires_at,
            "updated_at": instance.updated_at,
            "last_error": instance.last_error,
        }

    def list_instances(self, db: Session) -> list[dict[str, Any]]:
        instances = db.scalars(select(ChallengeInstance).order_by(ChallengeInstance.created_at.desc())).all()
        challenge_names = {row.id: row.name for row in db.scalars(select(Challenge)).all()}
        return [
            {
                "instance_id": item.id,
                "challenge_id": item.challenge_id,
                "challenge_name": challenge_names.get(item.challenge_id, item.challenge_id),
                "target_url": self._instance_target_url(item.host_port),
                "status": item.status,
                "host_port": item.host_port,
                "created_at": item.created_at,
                "expires_at": item.expires_at,
                "updated_at": item.updated_at,
                "last_error": item.last_error,
            }
            for item in instances
        ]

    def submit_flag(self, db: Session, instance_id: str, flag: str) -> dict[str, Any]:
        instance = db.get(ChallengeInstance, instance_id)
        if instance is None:
            raise KeyError(instance_id)
        submitted_hash = self._hash_flag(flag)
        correct = submitted_hash == instance.flag_hash
        submission = Submission(
            id=f"submission-{uuid4()}",
            instance_id=instance.id,
            submitted_flag_hash=submitted_hash,
            is_correct=correct,
            message="Flag correct" if correct else "Flag incorrect",
        )
        db.add(submission)
        return {
            "correct": correct,
            "submission_id": submission.id,
            "message": submission.message,
        }

    def reset_instance(self, db: Session, instance_id: str, regenerate_variant: bool = False) -> dict[str, Any]:
        instance = db.get(ChallengeInstance, instance_id)
        if instance is None:
            raise KeyError(instance_id)
        challenge = db.get(Challenge, instance.challenge_id)
        if challenge is None:
            raise KeyError(instance.challenge_id)

        old_container_id = instance.container_id
        old_network_name = instance.network_name
        docker_manager.remove_container(old_container_id)
        if old_network_name:
            docker_manager.remove_network(old_network_name)

        new_flag = self._new_flag()
        variant_seed = instance.variant_seed or self._new_variant_seed()
        if regenerate_variant:
            variant_seed = self._new_variant_seed()
        docker_manager.build_if_needed(
            image_name=challenge.image_name,
            dockerfile=challenge.dockerfile_path,
            path=str((self.settings.project_root / challenge.build_context).resolve()),
        )
        new_network_name = f"{self.settings.instance_network_prefix}-{instance.id}-{instance.host_port}"
        docker_container = None
        try:
            docker_container = docker_manager.run_container(
                image_name=challenge.image_name,
                container_name=f"cfr-{challenge.id}-{instance.id}-{instance.host_port}",
                challenge_id=challenge.id,
                flag=new_flag,
                network_name=new_network_name,
                host_port=instance.host_port,
                internal_port=challenge.internal_port,
                memory_limit=challenge.runtime_memory_limit,
                    cpu_limit=challenge.runtime_cpu_limit,
                extra_env={"VARIANT_SEED": variant_seed, "INSTANCE_ID": instance.id},
            )
            docker_manager.wait_healthy(instance.host_port)
        except Exception:
            if docker_container is not None:
                with suppress(Exception):
                    docker_manager.remove_container(docker_container.container_id)
            with suppress(Exception):
                docker_manager.remove_network(new_network_name)
            raise
        instance.flag_hash = self._hash_flag(new_flag)
        instance.variant_seed = variant_seed
        instance.status = "resetting"
        instance.last_error = None
        instance.updated_at = datetime.utcnow()
        existing_flag = db.scalars(select(InstanceFlag).where(InstanceFlag.instance_id == instance.id)).first()
        if existing_flag is None:
            db.add(InstanceFlag(id=f"flag-{instance.id}", instance_id=instance.id, flag_hash=instance.flag_hash))
        else:
            existing_flag.flag_hash = instance.flag_hash
            existing_flag.created_at = datetime.utcnow()
        instance.container_id = docker_container.container_id
        instance.network_name = new_network_name
        instance.status = "running"
        instance.last_health_at = datetime.utcnow()
        return {
            "instance_id": instance.id,
            "challenge_id": instance.challenge_id,
            "target_url": self._instance_target_url(instance.host_port),
            "status": instance.status,
            "expires_at": instance.expires_at,
            "created_at": instance.created_at,
            "host_port": instance.host_port,
        }

    def destroy_instance(self, db: Session, instance_id: str) -> dict[str, Any]:
        instance = db.get(ChallengeInstance, instance_id)
        if instance is None:
            raise KeyError(instance_id)
        docker_manager.remove_container(instance.container_id)
        if instance.network_name:
            docker_manager.remove_network(instance.network_name)
        instance.status = "destroyed"
        instance.container_id = None
        instance.network_name = None
        instance.updated_at = datetime.utcnow()
        return {"instance_id": instance.id, "status": instance.status}


instance_service = InstanceService()
