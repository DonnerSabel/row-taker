from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import BinaryIO

from row_taker.protocol.framing import decode_client_message, encode_server_message
from row_taker.server.endpoints import LocalLoopbackEndpoint


@dataclass(slots=True)
class ProcessBotRunner:
    endpoint: LocalLoopbackEndpoint
    seed: int | None = None
    _process: subprocess.Popen[bytes] = field(init=False)
    _stdin: BinaryIO = field(init=False)
    _stdout: BinaryIO = field(init=False)

    def __post_init__(self) -> None:
        env = dict(os.environ)
        pythonpath = env.get('PYTHONPATH')
        src_dir = self._detect_src_dir()
        if pythonpath:
            env['PYTHONPATH'] = src_dir + os.pathsep + pythonpath
        else:
            env['PYTHONPATH'] = src_dir
        cmd = [sys.executable, '-m', 'row_taker.bots.process_main']
        if self.seed is not None:
            cmd.extend(['--seed', str(self.seed)])
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if self._process.stdin is None or self._process.stdout is None:
            raise RuntimeError('failed to start bot process pipes')
        self._stdin = self._process.stdin
        self._stdout = self._process.stdout

    def pump(self) -> int:
        handled_messages = 0
        for message in self.endpoint.drain_incoming():
            handled_messages += 1
            self._ensure_running()
            self._stdin.write(encode_server_message(message))
            self._stdin.flush()
            line = self._stdout.readline()
            if not line:
                raise RuntimeError(self._build_process_failure_message('bot process closed stdout unexpectedly'))
            response = decode_client_message(line)
            self.endpoint.send_to_server(response)
        return handled_messages

    def close(self) -> None:
        process = getattr(self, '_process', None)
        if process is None:
            return
        if process.poll() is None:
            try:
                stdin = getattr(self, '_stdin', None)
                if stdin is not None:
                    stdin.close()
            except OSError:
                pass
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        stdout = getattr(self, '_stdout', None)
        if stdout is not None:
            stdout.close()
        stderr = process.stderr
        if stderr is not None:
            stderr.close()

    def _ensure_running(self) -> None:
        if self._process.poll() is not None:
            raise RuntimeError(self._build_process_failure_message('bot process is no longer running'))

    def _build_process_failure_message(self, prefix: str) -> str:
        stderr = self._process.stderr
        stderr_preview = ''
        if stderr is not None:
            try:
                raw = stderr.read()
            except OSError:
                raw = b''
            if raw:
                stderr_preview = raw.decode('utf-8', errors='replace').strip()
        if stderr_preview:
            return f'{prefix}: {stderr_preview}'
        return prefix

    def _detect_src_dir(self) -> str:
        current = os.path.abspath(__file__)
        return os.path.dirname(os.path.dirname(os.path.dirname(current)))
