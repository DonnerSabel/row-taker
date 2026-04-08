from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys


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
    ) -> "BotProcessHandle":
        process = subprocess.Popen(
            [
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
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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
