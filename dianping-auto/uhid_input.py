# -*- coding: utf-8 -*-
"""scrcpy 4.1 control-only UHID touchscreen. No Windows mouse injection."""
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import time


class UhidInput:
    def __init__(self, adb, serial, log_dir):
        self.adb_path, self.serial = adb, serial
        self.sock = self.proc = self.port = self.log = None
        self.remote = '/data/local/tmp/dianping-uhid-' + secrets.token_hex(4) + '.jar'
        root = Path(os.environ['LOCALAPPDATA']) / 'Microsoft/WinGet/Packages/Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe/scrcpy-win64-v4.1'
        server = root / 'scrcpy-server'
        if not server.exists():
            raise RuntimeError('找不到已安装的 scrcpy 4.1 server：' + str(server))
        try:
            self.adb('push', str(server), self.remote)
            scid = secrets.randbelow(0x7fffffff)
            self.port = self.adb('forward', 'tcp:0', f'localabstract:scrcpy_{scid:08x}').strip()
            self.log = (log_dir / 'uhid-server.log').open('wb')
            self.proc = subprocess.Popen([adb, '-s', serial, 'shell', f'CLASSPATH={self.remote}',
                'app_process', '/', 'com.genymobile.scrcpy.Server', '4.1', f'scid={scid:08x}',
                'video=false', 'audio=false', 'control=true', 'tunnel_forward=true',
                'send_device_meta=false', 'clipboard_autosync=false', 'cleanup=false'],
                stdout=self.log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(30):
                s = socket.socket()
                s.settimeout(1)
                try:
                    s.connect(('127.0.0.1', int(self.port)))
                    if s.recv(1) != b'\0':
                        raise OSError('server not ready')
                    self.sock = s
                    break
                except OSError:
                    s.close()
                    time.sleep(.2)
            if self.sock is None:
                raise RuntimeError('UHID 连接失败，请查看 uhid-server.log')
            # Single-contact multitouch digitizer; contact ID selects hid-multitouch.
            descriptor = bytes.fromhex(
                '05 0D 09 04 A1 01 09 22 A1 02 09 42 09 32 '
                '15 00 25 01 75 01 95 02 81 02 75 01 95 06 81 03 '
                '09 51 25 7F 75 08 95 01 81 02 '
                '05 01 09 30 09 31 16 00 00 26 FF 7F 75 10 95 02 81 02 C0 '
                '05 0D 09 54 15 00 25 01 75 08 95 01 81 02 C0')
            name = b'Dianping automation touch'
            self.sock.sendall(struct.pack('>BHHHB', 12, 1, 0, 0, len(name)) + name
                              + struct.pack('>H', len(descriptor)) + descriptor)
            time.sleep(1)
            devices = self.adb('shell', 'getevent', '-pl')
            if name.decode() not in devices:
                raise RuntimeError('Android 未创建 UHID 输入设备，请查看 uhid-server.log')
            state = self.adb('shell', 'dumpsys', 'input')
            device_state = state[state.rfind(name.decode()):]
            if 'mode - direct' not in device_state.split('Input Dispatcher State:')[0]:
                raise RuntimeError('UHID 未按直接触屏模式映射，停止以避免坐标偏移。')
        except BaseException:
            self.close()
            raise

    def adb(self, *args):
        p = subprocess.run([self.adb_path, '-s', self.serial, *args], capture_output=True,
                           timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        if p.returncode:
            raise RuntimeError(p.stderr.decode('utf-8', 'replace'))
        return p.stdout.decode('utf-8', 'replace')

    def report(self, x, y, down, width, height):
        if not 0 <= x < width or not 0 <= y < height:
            raise RuntimeError('点击坐标超出屏幕。')
        report = struct.pack('<BBHHB', 3 if down else 0, 0,
                             round(x * 32767 / (width - 1)), round(y * 32767 / (height - 1)), 1)
        self.sock.sendall(struct.pack('>BHH', 13, 1, len(report)) + report)

    def tap(self, x, y, width, height):
        try:
            self.report(x, y, True, width, height)
            time.sleep(.12)
        finally:
            self.report(x, y, False, width, height)

    def swipe(self, x1, y1, x2, y2, width, height, settle=0):
        try:
            for i in range(21):
                self.report(round(x1+(x2-x1)*i/20), round(y1+(y2-y1)*i/20), True, width, height)
                time.sleep(.035)
            if settle:
                time.sleep(settle)
        finally:
            self.report(x2, y2, False, width, height)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
        if self.proc:
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=3)
        if self.log:
            self.log.close()
        if self.port:
            self.adb('forward', '--remove', 'tcp:' + self.port)
            self.port = None
        self.adb('shell', 'rm', '-f', self.remote)
