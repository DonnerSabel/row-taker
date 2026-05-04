from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class BotProcessHandle:
    process: subprocess.Popen[bytes]

    @classmethod
    def spawn(
        cls,
        *,
        host: str,
        port: int,
        display_name: str,
        client_id: str,
        seed: int,
        python_executable: str = sys.executable,
        log_level: str | None = None,
        log_file: str | None = None,
    ) -> BotProcessHandle:
        argv = [
            python_executable,
            "-m",
            "row_taker.bots.process_main",
            "--host",
            host,
            "--port",
            str(port),
            "--display-name",
            display_name,
            "--client-id",
            client_id,
            "--seed",
            str(seed),
        ]
        if log_level:
            argv.extend(["--log-level", log_level])
        if log_file:
            argv.extend(["--log-file", log_file])

        env = os.environ.copy()
        src_path = str(Path(__file__).resolve().parents[2])
        old_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            src_path if not old_pythonpath else f"{src_path}{os.pathsep}{old_pythonpath}"
        )

        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        return cls(process=process)

    def poll(self) -> int | None:
        return self.process.poll()

    def is_running(self) -> bool:
        return self.poll() is None

    def terminate(self) -> None:
        if self.is_running():
            self.process.terminate()

    def wait(self, timeout: float | None = None) -> int:
        return self.process.wait(timeout=timeout)

    def kill(self) -> None:
        if self.is_running():
            self.process.kill()

    def close(self) -> None:
        self.terminate()
        try:
            self.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self.kill()
            self.wait(timeout=1.0)
