# -*- coding: utf-8 -*-
"""scrcpy control-only UHID touchscreen transport."""
from __future__ import annotations

import glob
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import struct
import subprocess
import time


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _detect_scrcpy_version() -> str | None:
    executable = shutil.which("scrcpy") or shutil.which("scrcpy.exe")
    if not executable:
        return None
    try:
        process = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=_creation_flags(),
        )
    except OSError:
        return None
    match = re.search(r"\bscrcpy\s+([0-9]+(?:\.[0-9]+){1,2})\b", process.stdout + process.stderr)
    return match.group(1) if match else None


def _find_scrcpy_server(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_path = os.environ.get("SCRCPY_SERVER_PATH")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    scrcpy_exe = shutil.which("scrcpy") or shutil.which("scrcpy.exe")
    if scrcpy_exe:
        executable = Path(scrcpy_exe).resolve()
        candidates.append(executable.with_name("scrcpy-server"))
        candidates.append(executable.with_name("scrcpy-server.jar"))

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            patterns = [
                str(Path(local) / "Microsoft" / "WinGet" / "Packages" / "Genymobile.scrcpy_*" / "**" / "scrcpy-server"),
                str(Path(local) / "Microsoft" / "WinGet" / "Packages" / "Genymobile.scrcpy_*" / "**" / "scrcpy-server.jar"),
            ]
            for pattern in patterns:
                candidates.extend(Path(path) for path in glob.glob(pattern, recursive=True))
    else:
        candidates.extend(
            Path(path)
            for path in [
                "/usr/share/scrcpy/scrcpy-server",
                "/usr/local/share/scrcpy/scrcpy-server",
                "/opt/homebrew/share/scrcpy/scrcpy-server",
            ]
        )

    existing = [path.resolve() for path in candidates if path.is_file()]
    if not existing:
        raise RuntimeError(
            "找不到 scrcpy-server。请安装 scrcpy，或通过 --scrcpy-server / "
            "SCRCPY_SERVER_PATH 指定文件路径。"
        )
    # Prefer the newest discovered copy so WinGet upgrades do not pin an old directory.
    return max(existing, key=lambda path: path.stat().st_mtime)


class UhidInput:
    def __init__(
        self,
        adb: str,
        serial: str,
        log_dir: Path,
        server_path: str | None = None,
        server_version: str | None = None,
    ):
        self.adb_path = adb
        self.serial = serial
        self.sock = None
        self.proc = None
        self.port = None
        self.log = None
        self.remote = "/data/local/tmp/dianping-uhid-" + secrets.token_hex(4) + ".jar"
        server = _find_scrcpy_server(server_path)
        version = server_version or os.environ.get("SCRCPY_SERVER_VERSION") or _detect_scrcpy_version()
        if not version:
            raise RuntimeError(
                "无法确定 scrcpy server 版本。请通过 --scrcpy-version / "
                "SCRCPY_SERVER_VERSION 显式指定，例如 4.1。"
            )

        try:
            self.adb("push", str(server), self.remote)
            scid = secrets.randbelow(0x7FFFFFFF)
            self.port = self.adb("forward", "tcp:0", f"localabstract:scrcpy_{scid:08x}").strip()
            self.log = (log_dir / "uhid-server.log").open("wb")
            self.proc = subprocess.Popen(
                [
                    adb,
                    "-s",
                    serial,
                    "shell",
                    f"CLASSPATH={self.remote}",
                    "app_process",
                    "/",
                    "com.genymobile.scrcpy.Server",
                    version,
                    f"scid={scid:08x}",
                    "video=false",
                    "audio=false",
                    "control=true",
                    "tunnel_forward=true",
                    "send_device_meta=false",
                    "clipboard_autosync=false",
                    "cleanup=false",
                ],
                stdout=self.log,
                stderr=subprocess.STDOUT,
                creationflags=_creation_flags(),
            )
            for _ in range(30):
                sock = socket.socket()
                sock.settimeout(1)
                try:
                    sock.connect(("127.0.0.1", int(self.port)))
                    if sock.recv(1) != b"\0":
                        raise OSError("server not ready")
                    self.sock = sock
                    break
                except OSError:
                    sock.close()
                    time.sleep(0.2)
            if self.sock is None:
                raise RuntimeError("UHID 连接失败，请查看 logs 中的 uhid-server.log。")

            descriptor = bytes.fromhex(
                "05 0D 09 04 A1 01 09 22 A1 02 09 42 09 32 "
                "15 00 25 01 75 01 95 02 81 02 75 01 95 06 81 03 "
                "09 51 25 7F 75 08 95 01 81 02 "
                "05 01 09 30 09 31 16 00 00 26 FF 7F 75 10 95 02 81 02 C0 "
                "05 0D 09 54 15 00 25 01 75 08 95 01 81 02 C0"
            )
            name = b"Android automation touch"
            self.sock.sendall(
                struct.pack(">BHHHB", 12, 1, 0, 0, len(name))
                + name
                + struct.pack(">H", len(descriptor))
                + descriptor
            )
            time.sleep(1)

            devices = self.adb("shell", "getevent", "-pl")
            if name.decode() not in devices:
                raise RuntimeError("Android 未创建 UHID 输入设备，请查看 uhid-server.log。")
            state = self.adb("shell", "dumpsys", "input")
            device_state = state[state.rfind(name.decode()):]
            if "mode - direct" not in device_state.split("Input Dispatcher State:")[0]:
                raise RuntimeError("UHID 未按直接触屏模式映射，停止以避免坐标偏移。")
        except BaseException:
            self.close()
            raise

    def adb(self, *args: str) -> str:
        process = subprocess.run(
            [self.adb_path, "-s", self.serial, *args],
            capture_output=True,
            timeout=30,
            creationflags=_creation_flags(),
        )
        if process.returncode:
            raise RuntimeError(process.stderr.decode("utf-8", "replace"))
        return process.stdout.decode("utf-8", "replace")

    def report(self, x: int, y: int, down: bool, width: int, height: int) -> None:
        if not 0 <= x < width or not 0 <= y < height:
            raise RuntimeError("点击坐标超出屏幕。")
        if width <= 1 or height <= 1:
            raise RuntimeError("无效的设备屏幕尺寸。")
        report = struct.pack(
            "<BBHHB",
            3 if down else 0,
            0,
            round(x * 32767 / (width - 1)),
            round(y * 32767 / (height - 1)),
            1,
        )
        self.sock.sendall(struct.pack(">BHH", 13, 1, len(report)) + report)

    def tap(self, x: int, y: int, width: int, height: int) -> None:
        try:
            self.report(x, y, True, width, height)
            time.sleep(0.12)
        finally:
            self.report(x, y, False, width, height)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> None:
        try:
            for index in range(21):
                self.report(
                    round(x1 + (x2 - x1) * index / 20),
                    round(y1 + (y2 - y1) * index / 20),
                    True,
                    width,
                    height,
                )
                time.sleep(0.035)
        finally:
            self.report(x2, y2, False, width, height)

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None
        if self.proc:
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            self.proc = None
        if self.log:
            self.log.close()
            self.log = None
        if self.port:
            try:
                self.adb("forward", "--remove", "tcp:" + self.port)
            except Exception:
                pass
            self.port = None
        try:
            self.adb("shell", "rm", "-f", self.remote)
        except Exception:
            pass
