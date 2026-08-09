from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import docker
import httpx
from docker.errors import APIError, NotFound

from ..config import get_settings


@dataclass(slots=True)
class ContainerLaunchResult:
    container_id: str
    host_port: int
    network_name: str


class DockerManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = docker.from_env()

    def image_exists(self, image_name: str) -> bool:
        try:
            self.client.images.get(image_name)
            return True
        except NotFound:
            return False

    def build_image(self, image_name: str, dockerfile: str, path: str) -> None:
        self.client.images.build(path=path, dockerfile=dockerfile, tag=image_name, rm=True)

    def ensure_network(self, network_name: str) -> None:
        try:
            self.client.networks.get(network_name)
        except NotFound:
            self.client.networks.create(network_name, driver="bridge", check_duplicate=True)

    def remove_network(self, network_name: str) -> None:
        try:
            network = self.client.networks.get(network_name)
            network.remove()
        except NotFound:
            return

    def remove_container(self, container_id: str | None) -> None:
        if not container_id:
            return
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
        except NotFound:
            return

    def build_if_needed(self, image_name: str, dockerfile: str, path: str) -> None:
        # Images are built explicitly during deployment. Rebuilding for every
        # instance can restore stale BuildKit layers over a freshly fixed image.
        if not self.image_exists(image_name):
            self.build_image(image_name=image_name, dockerfile=dockerfile, path=path)

    def run_container(
        self,
        *,
        image_name: str,
        container_name: str,
        challenge_id: str,
        flag: str,
        network_name: str,
        host_port: int,
        internal_port: int,
        extra_env: dict[str, str] | None = None,
        memory_limit: str = "256m",
        cpu_limit: str = "0.5",
    ) -> ContainerLaunchResult:
        self.ensure_network(network_name)
        env = {
            "CHALLENGE_ID": challenge_id,
            "INSTANCE_FLAG": flag,
            "INSTANCE_ID": container_name,
        }
        if extra_env:
            env.update(extra_env)

        cpu_quota = max(1, int(float(cpu_limit) * 100000))
        container = self.client.containers.run(
            image_name,
            name=container_name,
            detach=True,
            environment=env,
            network=network_name,
            ports={f"{internal_port}/tcp": ("0.0.0.0", host_port)},
            mem_limit=memory_limit,
            cpu_period=100000,
            cpu_quota=cpu_quota,
            pids_limit=128,
            security_opt=["no-new-privileges:true"],
            read_only=False,
            cap_drop=["ALL"],
            restart_policy={"Name": "no"},
        )
        return ContainerLaunchResult(container_id=container.id, host_port=host_port, network_name=network_name)

    def wait_healthy(self, host_port: int, timeout_seconds: int = 30) -> None:
        import time

        deadline = time.time() + timeout_seconds
        url = f"http://host.docker.internal:{host_port}/health"
        while time.time() < deadline:
            try:
                response = httpx.get(url, timeout=3.0)
                if response.status_code == 200:
                    return
            except Exception:
                time.sleep(1)
        raise TimeoutError(f"challenge endpoint on port {host_port} did not become healthy")


docker_manager = DockerManager()
