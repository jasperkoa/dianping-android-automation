# -*- coding: utf-8 -*-
"""Dianping physical-device UI automation over ADB with optional scrcpy UHID input."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
UI_DUMP_JAR = ROOT / "android" / "prebuilt" / "ui-dump.jar"
DEFAULT_PACKAGE = "com.dianping.v1"
BUTTONS = {"免费抽", "免费抽奖"}
RISK_MARKERS = {"安全验证", "滑块验证", "操作频繁", "操作太频繁", "短信验证码", "人机验证"}
PAYMENT_MARKERS = {"立即支付", "确认支付", "支付报名", "消耗PASS", "使用PASS卡", "兑换报名"}
LIST_MARKERS = {"免费试天天抽"}


def label(node: ET.Element) -> str:
    return (node.get("text") or node.get("content-desc") or "").strip()


def bounds(node: ET.Element) -> list[int]:
    values = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
    return values if len(values) == 4 else [0, 0, 0, 0]


def visible(node: ET.Element) -> bool:
    x1, y1, x2, y2 = bounds(node)
    return x2 > x1 and y2 > y1 and node.get("enabled") != "false"


def find(root: ET.Element, text: str) -> ET.Element | None:
    return next((node for node in root.iter("node") if label(node) == text and visible(node)), None)


def texts(root: ET.Element) -> list[str]:
    return [label(node) for node in root.iter("node") if label(node) and visible(node)]


def candidates(root: ET.Element) -> list[tuple[str, ET.Element]]:
    """Return visible free-draw activity rows, regardless of Orange-V/ordinary category."""
    parents = {child: parent for parent in root.iter() for child in parent}
    result: list[tuple[str, ET.Element]] = []

    for button in root.iter("node"):
        if label(button) not in BUTTONS or not visible(button):
            continue

        parent = parents.get(button)
        while parent is not None:
            card_texts = texts(parent)
            button_count = sum(label(node) in BUTTONS and visible(node) for node in parent.iter("node"))
            if button_count > 1:
                break

            titles = [
                text
                for text in card_texts
                if len(text) >= 5
                and not any(
                    word in text
                    for word in ["中奖", "名额", "价值", "免费抽", "相似活动", "人报名", "已报名", "km", "开奖"]
                )
                and text not in ["橙V专享", "橙V专属"]
            ]
            if titles:
                name = titles[0].replace("\ufffc", "").strip()
                stores = [text for text in card_texts if text.endswith("店") and text != titles[0]]
                title = " | ".join([name] + stores[:1])
                result.append((title, button))
                break
            parent = parents.get(parent)

    return result


def resolve_adb(value: str | None) -> str:
    candidate = value or os.environ.get("ADB_PATH") or "adb"
    path = shutil.which(candidate)
    if path:
        return str(Path(path).resolve())
    if Path(candidate).is_file():
        return str(Path(candidate).resolve())
    raise RuntimeError(
        "找不到 adb。请把 Android SDK Platform-Tools 加入 PATH，"
        "或通过 --adb / ADB_PATH 指定 adb.exe 路径。"
    )


def list_connected_devices(adb: str) -> list[str]:
    process = subprocess.run([adb, "devices"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    if process.returncode:
        raise RuntimeError("adb devices 执行失败：" + (process.stderr or process.stdout).strip())
    devices: list[str] = []
    for line in process.stdout.splitlines()[1:]:
        fields = line.strip().split()
        if len(fields) >= 2 and fields[1] == "device":
            devices.append(fields[0])
    return devices


def resolve_serial(adb: str, value: str | None) -> str:
    serial = value or os.environ.get("ANDROID_SERIAL")
    if serial:
        return serial
    devices = list_connected_devices(adb)
    if len(devices) == 1:
        return devices[0]
    if not devices:
        raise RuntimeError("未发现已授权的 Android 设备。请先确认 adb devices 显示 device。")
    raise RuntimeError("检测到多台 Android 设备。请使用 --serial 或 ANDROID_SERIAL 明确指定目标设备。")


class Bot:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.run_dir = ROOT / "logs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.seen: set[str] = set()
        self.success = 0
        self.input = None
        self.reader_path = "/data/local/tmp/dianping-read-" + secrets.token_hex(4) + ".jar"
        self.reader_ready = False
        self.root: ET.Element | None = None
        self.width = 0
        self.height = 0

    def choices(self, root: ET.Element) -> list[tuple[str, ET.Element]]:
        return candidates(root)

    def adb(self, *args: object) -> str:
        process = subprocess.run(
            [self.args.adb, "-s", self.args.serial, *map(str, args)],
            capture_output=True,
            timeout=35,
        )
        out = process.stdout.decode("utf-8", errors="replace")
        err = process.stderr.decode("utf-8", errors="replace")
        combined = out + err
        if process.returncode or "SecurityException" in combined or "INJECT_EVENTS" in combined:
            raise RuntimeError("ADB 执行失败：" + combined[-1600:])
        return out

    def log(self, event: str, **data: object) -> None:
        row = {"time": dt.datetime.now().isoformat(timespec="seconds"), "event": event, **data}
        print(json.dumps(row, ensure_ascii=False), flush=True)
        with (self.run_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def snapshot(self) -> ET.Element:
        if not UI_DUMP_JAR.exists():
            raise RuntimeError(f"缺少 UI dump helper：{UI_DUMP_JAR}")
        if not self.reader_ready:
            self.adb("push", str(UI_DUMP_JAR), self.reader_path)
            self.reader_ready = True

        root = None
        for attempt in range(3):
            try:
                xml = self.adb("shell", "CLASSPATH=" + self.reader_path, "app_process", "/", "UiDump")
                if "<?xml" not in xml:
                    raise RuntimeError("未读取到页面控件。")
                root = ET.fromstring(xml[xml.index("<?xml"):])
                break
            except (RuntimeError, ET.ParseError):
                if attempt == 2:
                    raise
                time.sleep(2)

        assert root is not None
        if not any(node.get("package") == self.args.package for node in root.iter("node")):
            raise RuntimeError(f"目标 App（{self.args.package}）未在前台。请打开免费试活动列表后再运行。")

        self.root = root
        current_texts = texts(root)
        if any(any(marker in text for marker in RISK_MARKERS) for text in current_texts):
            raise RuntimeError("检测到验证或频率限制，请手动处理后再启动。")
        return root

    def tap(self, node: ET.Element) -> None:
        if node is None or not visible(node):
            raise RuntimeError("目标按钮不存在或不可见。")
        x1, y1, x2, y2 = bounds(node)
        x, y = (x1 + x2) // 2, (y1 + y2) // 2
        if self.input:
            self.input.tap(x, y, self.width, self.height)
        else:
            self.adb("shell", "input", "tap", x, y)
        time.sleep(self.args.delay)

    def back(self) -> None:
        mode = self.args.back_mode
        if mode == "adb":
            self.adb("shell", "input", "keyevent", "4")
        elif not self.input:
            raise RuntimeError(f"back-mode={mode} 需要 --input uhid。")
        elif mode in {"nav-left", "nav-right"}:
            default_x = 0.29 if mode == "nav-left" else 0.71
            x_ratio = self.args.back_x_ratio if self.args.back_x_ratio is not None else default_x
            y_ratio = self.args.back_y_ratio
            self.input.tap(round(self.width * x_ratio), round(self.height * y_ratio), self.width, self.height)
        elif mode in {"gesture-left", "gesture-right"}:
            y = round(self.height * 0.50)
            if mode == "gesture-left":
                self.input.swipe(max(2, round(self.width * 0.01)), y, round(self.width * 0.35), y, self.width, self.height)
            else:
                self.input.swipe(min(self.width - 3, round(self.width * 0.99)), y, round(self.width * 0.65), y, self.width, self.height)
        else:
            raise RuntimeError("未知 back-mode。")
        time.sleep(self.args.delay)

    def wait_for(self, names: list[str]) -> tuple[str, ET.Element]:
        for _ in range(4):
            root = self.snapshot()
            for name in names:
                node = find(root, name)
                if node is not None:
                    return name, node
            time.sleep(self.args.delay)
        raise RuntimeError("未出现预期页面：" + " / ".join(names))

    @staticmethod
    def is_list_page(root: ET.Element) -> bool:
        current_texts = texts(root)
        return bool(candidates(root)) or any(marker in current_texts for marker in LIST_MARKERS) or (
            "全部商区" in current_texts and "智能排序" in current_texts
        )

    def ensure_list(self) -> ET.Element:
        root = self.snapshot()
        if self.is_list_page(root):
            return root
        raise RuntimeError("当前不是可识别的免费试活动列表。请手动进入活动“查看全部”列表后再启动。")

    def return_list(self) -> ET.Element:
        for _ in range(4):
            root = self.snapshot()
            if find(root, "报名成功") is not None:
                done = find(root, "完成")
                if done is None:
                    raise RuntimeError("报名结果页面缺少完成按钮。")
                self.tap(done)
            elif find(root, "免费试活动详情") is not None:
                self.back()
            elif self.is_list_page(root):
                return root
            else:
                raise RuntimeError("当前不是可识别的活动详情或列表页面，停止以避免误操作。")
        raise RuntimeError("无法返回活动列表。")

    def apply(self, title: str, button: ET.Element) -> None:
        self.log("打开活动", title=title)
        self.tap(button)
        name, node = self.wait_for(["我要报名", "已报名,看看其他活动", "已报名，看看其他活动"])
        if name != "我要报名":
            self.log("跳过已报名", title=title)
            self.return_list()
            return

        self.tap(node)
        _, confirm = self.wait_for(["确认报名"])
        if find(self.root, "确认报名信息") is None:
            raise RuntimeError("未识别确认报名信息弹窗。")

        current_texts = texts(self.root)
        if any(any(marker in text for marker in PAYMENT_MARKERS) for text in current_texts):
            raise RuntimeError("出现支付或兑换选项，停止，请手动检查。")

        self.log("提交报名", title=title)
        self.tap(confirm)
        try:
            self.wait_for(["报名成功"])
        except RuntimeError as exc:
            raise RuntimeError("提交后未确认报名成功；不会自动重试提交，请手动检查。") from exc

        self.success += 1
        self.log("报名成功", title=title, success=self.success)
        self.return_list()

    def run(self) -> None:
        if self.adb("get-state").strip() != "device":
            raise RuntimeError("手机未连接。")

        root = self.snapshot()
        if self.args.inspect:
            self.log(
                "只读检查",
                candidates=[title for title, _ in self.choices(root)],
                page_markers=[text for text in texts(root) if text in {"报名成功", "免费试活动详情", "确认报名信息", "免费试天天抽"}],
            )
            return

        if self.args.input == "uhid":
            from uhid_input import UhidInput

            sizes = re.findall(r"(\d+)x(\d+)", self.adb("shell", "wm", "size"))
            if not sizes:
                raise RuntimeError("无法读取设备屏幕尺寸。")
            self.width, self.height = map(int, sizes[-1])
            self.input = UhidInput(
                self.args.adb,
                self.args.serial,
                self.run_dir,
                server_path=self.args.scrcpy_server,
                server_version=self.args.scrcpy_version,
            )
            self.log("UHID 输入已连接")

        root = self.ensure_list()
        fingerprints: set[str] = set()

        for scroll_index in range(self.args.max_scrolls + 1):
            while self.success < self.args.limit:
                root = self.snapshot()
                choices = [(title, node) for title, node in self.choices(root) if title not in self.seen]
                if not choices:
                    break
                title, button = choices[0]
                self.seen.add(title)
                self.apply(title, button)

            if self.success >= self.args.limit or scroll_index >= self.args.max_scrolls:
                break

            fingerprint = hashlib.sha256("\n".join(texts(root)).encode()).hexdigest()
            if fingerprint in fingerprints:
                self.log("列表停止变化，结束")
                break
            fingerprints.add(fingerprint)

            scrolls = [node for node in root.iter("node") if node.get("scrollable") == "true" and visible(node)]
            if not scrolls:
                raise RuntimeError("没有可识别的滚动容器，停止以避免误滑。")
            region = max(scrolls, key=lambda node: (bounds(node)[2] - bounds(node)[0]) * (bounds(node)[3] - bounds(node)[1]))
            x1, y1, x2, y2 = bounds(region)
            self.log("滚动列表", scroll=scroll_index + 1)
            start_x = (x1 + x2) // 2
            start_y = int(y1 + (y2 - y1) * 0.8)
            end_y = int(y1 + (y2 - y1) * 0.35)
            if self.input:
                self.input.swipe(start_x, start_y, start_x, end_y, self.width, self.height)
            else:
                self.adb("shell", "input", "swipe", start_x, start_y, start_x, end_y, "650")
            time.sleep(self.args.delay)

        self.log("运行结束", success=self.success)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default=None, help="adb 可执行文件路径；默认从 ADB_PATH/PATH 自动发现")
    parser.add_argument("--serial", default=None, help="ADB 设备序列号；单设备时可省略，也可设置 ANDROID_SERIAL")
    parser.add_argument("--package", default=os.environ.get("TARGET_PACKAGE", DEFAULT_PACKAGE), help="目标 Android 包名")
    parser.add_argument("--limit", type=int, default=10, help="本次成功操作上限")
    parser.add_argument("--max-scrolls", type=int, default=30, help="最大列表滚动次数")
    parser.add_argument("--delay", type=float, default=2.5, help="UI 操作后的等待秒数")
    parser.add_argument("--inspect", action="store_true", help="只读检查，不点击")
    parser.add_argument("--input", choices=["uhid", "adb"], default="uhid", help="输入方式")
    parser.add_argument(
        "--back-mode",
        choices=["adb", "gesture-left", "gesture-right", "nav-left", "nav-right"],
        default=os.environ.get("ANDROID_BACK_MODE", "adb"),
        help="返回操作方式；不同厂商/导航模式可能需要调整",
    )
    parser.add_argument("--back-x-ratio", type=float, default=None, help="三键导航返回键 X 比例，可选")
    parser.add_argument("--back-y-ratio", type=float, default=float(os.environ.get("ANDROID_BACK_Y_RATIO", "0.973")), help="三键导航返回键 Y 比例")
    parser.add_argument("--scrcpy-server", default=os.environ.get("SCRCPY_SERVER_PATH"), help="scrcpy-server 路径；默认自动发现")
    parser.add_argument("--scrcpy-version", default=os.environ.get("SCRCPY_SERVER_VERSION"), help="scrcpy server 版本；默认从 scrcpy --version 自动检测")
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args()
    if args.limit < 1 or args.max_scrolls < 0 or args.delay < 1:
        parser.error("limit >= 1, max-scrolls >= 0, delay >= 1")
    if not 0 < args.back_y_ratio < 1:
        parser.error("back-y-ratio 必须在 0 和 1 之间")
    if args.back_x_ratio is not None and not 0 < args.back_x_ratio < 1:
        parser.error("back-x-ratio 必须在 0 和 1 之间")

    bot = None
    try:
        args.adb = resolve_adb(args.adb)
        args.serial = resolve_serial(args.adb, args.serial)
        bot = Bot(args)
        print("大众点评免费试 Android 真机自动化", flush=True)
        print(f"ADB: {args.adb}", flush=True)
        print(f"Device: {args.serial}", flush=True)
        print(
            "只读检查，不点击。"
            if args.inspect
            else f"请保持免费试活动列表在前台。本次最多处理 {args.limit} 项，按 Ctrl+C 停止。",
            flush=True,
        )
        bot.run()
    except KeyboardInterrupt:
        if bot:
            bot.log("用户停止", success=bot.success)
        return 130
    except Exception as exc:
        if bot:
            bot.log("停止", reason=str(exc), success=bot.success)
        else:
            print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        if "INJECT_EVENTS" in str(exc):
            print("设备拒绝 ADB 输入注入；可改用 UHID，部分 MIUI 设备还需开启“USB 调试（安全设置）”。", flush=True)
        return 1
    finally:
        if bot and bot.input:
            try:
                bot.input.close()
            except Exception as exc:
                print(f"WARN: 关闭 UHID 输入时出现异常：{exc}", file=sys.stderr)
        if bot and bot.reader_ready:
            try:
                bot.adb("shell", "rm", "-f", bot.reader_path)
            except Exception as exc:
                print(f"WARN: 清理 UI helper 时出现异常：{exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
