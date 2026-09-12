# -*- coding: utf-8 -*-
"""大众点评免费抽自动报名：所有类别的免费抽活动，ADB 读取页面、UHID 点击。"""
import argparse
import datetime as dt
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import secrets
import io
import xml.etree.ElementTree as ET
from screen_guard import inside, list_area, orange_button, footer_present, mine_selected

BASE = Path(__file__).resolve().parent
PACKAGE = 'com.dianping.v1'
BUTTONS = {'免费抽', '免费抽奖'}


class RecoverableUI(RuntimeError):
    pass


def label(n):
    return (n.get('text') or n.get('content-desc') or '').strip()


def bounds(n):
    v = list(map(int, re.findall(r'-?\d+', n.get('bounds', ''))))
    return v if len(v) == 4 else [0, 0, 0, 0]


def visible(n):
    x1, y1, x2, y2 = bounds(n)
    return x2 > x1 and y2 > y1 and n.get('enabled') != 'false'


def find(root, text):
    return next((n for n in root.iter('node') if label(n) == text and visible(n)), None)


def texts(root):
    return [label(n) for n in root.iter('node') if label(n) and visible(n)]


def activity_step(root, width, height):
    """Measure one row from adjacent activity titles, including registered rows."""
    rows = []
    for n in root.iter('node'):
        t = label(n)
        x1, y1, x2, y2 = bounds(n)
        if (visible(n) and ('套餐' in t or '代金券' in t) and ('|' in t or '｜' in t)
                and x1 >= width*.25 and height*.105 <= y1 < height*.85):
            if not any(abs(y1-y) < 20 for _, y in rows):
                rows.append((t, y1))
    rows.sort(key=lambda item: item[1])
    for (first, y1), (second, y2) in zip(rows, rows[1:]):
        if width*.2 <= y2-y1 <= width*.6:
            return y2-y1, second, y2
    return round(width*335/1080), None, None


def candidates(root):
    """按列表顺序选择有可见免费抽按钮的活动，不按会员徽标筛选。"""
    parents = {child: p for p in root.iter() for child in p}
    result = []
    for button in root.iter('node'):
        if label(button) not in BUTTONS or not visible(button):
            continue
        p = parents.get(button)
        while p is not None:
            ts = texts(p)
            count = sum(label(n) in BUTTONS and visible(n) for n in p.iter('node'))
            if count > 1:
                break
            titles = [t for t in ts if len(t) >= 5 and re.search(r'[A-Za-z\u4e00-\u9fff]', t) and not any(w in t for w in
                      ['中奖', '名额', '价值', '免费抽', '相似活动', '人报名', '已报名', 'km', '开奖'])
                      and t not in ['橙V专享', '橙V专属']]
            if titles:
                name = titles[0].replace('\ufffc', '').strip()
                stores = [t for t in ts if t.endswith('店') and t != titles[0]]
                title = ' | '.join([name] + stores[:1])
                result.append((title, button))
                break
            p = parents.get(p)
    return result


class Bot:
    def __init__(self, args):
        self.args = args
        self.run_dir = BASE / 'logs' / dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.seen = set()
        self.success = 0
        self.input = None
        self.reader_path = '/data/local/tmp/dianping-read-' + secrets.token_hex(4) + '.jar'
        self.reader_ready = False
        self.width, self.height = 1080, 2340
        self.recoveries = 0

    def choices(self, root):
        area = list_area(self.width, self.height)
        return [(t, n) for t, n in candidates(root) if inside(bounds(n), area)]

    def screenshot(self):
        from PIL import Image
        p = subprocess.run([self.args.adb, '-s', self.args.serial, 'exec-out', 'screencap', '-p'],
                           capture_output=True, timeout=20)
        if p.returncode:
            raise RuntimeError('无法读取当前屏幕。')
        frame = Image.open(io.BytesIO(p.stdout)).convert('RGB')
        if frame.size != (self.width, self.height):
            raise RuntimeError('屏幕方向或尺寸变化，请保持手机竖屏。')
        return frame

    def recover_navigation(self, root):
        ts = texts(root)
        if self.menu_visible(root):
            if self.recoveries >= 3:
                raise RuntimeError('页面恢复次数过多，请手动检查。')
            self.recoveries += 1
            self.log('关闭误开的更多菜单')
            # This web menu does not consume Android Back; Back leaves the trial page.
            # Its observed top-right trigger toggles the popover without navigating.
            self.tap_point(round(self.width*.92), round(self.height*.063))
            return True
        if any(t in ts for t in ['确认报名信息', '确认报名', '免费试活动详情', '报名成功']):
            return False
        if footer_present(self.screenshot()):
            if self.recoveries >= 3:
                raise RuntimeError('页面恢复次数过多，请手动检查。')
            self.recoveries += 1
            self.log('返回底部免费试页签', recovery=self.recoveries)
            self.tap_point(round(self.width/6), round(self.height*.89))
            return True
        return False

    @staticmethod
    def menu_visible(root):
        ts = texts(root)
        return (sum(t in ts for t in ['微信好友', '朋友圈', '复制链接', '在浏览器打开', '刷新']) >= 2
                or sum(t in ts for t in ['活动订阅', '霸气宝箱规则', '免费试规则', '报名资格查询', '新手任务规则']) >= 2)

    def adb(self, *args):
        p = subprocess.run([self.args.adb, '-s', self.args.serial, *map(str, args)],
                           capture_output=True, timeout=35)
        out = p.stdout.decode('utf-8', errors='replace')
        err = p.stderr.decode('utf-8', errors='replace')
        if p.returncode or 'SecurityException' in out + err or 'INJECT_EVENTS' in out + err:
            raise RuntimeError('ADB 执行失败：' + (out + err)[-1600:])
        return out

    def log(self, event, **data):
        row = dict(time=dt.datetime.now().isoformat(timespec='seconds'), event=event, **data)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        with (self.run_dir / 'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    def snapshot(self):
        if not self.reader_ready:
            self.adb('push', str(BASE / 'build' / 'ui-dump.jar'), self.reader_path)
            self.reader_ready = True
        for attempt in range(3):
            try:
                xml = self.adb('shell', 'CLASSPATH=' + self.reader_path, 'app_process', '/', 'UiDump')
                if '<?xml' not in xml:
                    raise RuntimeError('未读取到页面控件。')
                xml = xml[xml.index('<?xml'):]
                root = ET.fromstring(xml)
                break
            except (RuntimeError, ET.ParseError):
                if attempt == 2:
                    raise
                time.sleep(2)
        if not any(n.get('package') == PACKAGE for n in root.iter('node')):
            raise RuntimeError('大众点评未在前台，请打开免费试的查看全部列表。')
        self.root = root
        # 仅内存读取完整页面，避免把电话号码等字段写入日志。
        ts = texts(root)
        if any(any(w in t for w in ['安全验证', '滑块验证', '操作频繁', '操作太频繁', '短信验证码', '人机验证']) for t in ts):
            raise RuntimeError('检测到验证或频率限制，请手动处理后再启动。')
        return root

    def tap(self, n):
        if n is None or not visible(n):
            raise RuntimeError('目标按钮不存在或不可见。')
        x1, y1, x2, y2 = bounds(n)
        if label(n) in BUTTONS:
            if not inside(bounds(n), list_area(self.width, self.height)):
                raise RecoverableUI('免费抽按钮被工具栏或底部导航遮挡，重新定位。')
        if label(n) in BUTTONS | {'我要报名', '确认报名'}:
            if not orange_button(self.screenshot(), bounds(n)):
                raise RecoverableUI('当前截图中的按钮位置不符，取消点击并重新定位。')
        self.tap_point((x1+x2)//2, (y1+y2)//2)

    def tap_point(self, x, y):
        if self.input:
            self.input.tap(x, y, self.width, self.height)
        else:
            self.adb('shell', 'input', 'tap', x, y)
        time.sleep(self.args.delay)

    def back(self):
        if self.input:
            # Mi9SE uses the visible three-button navigation bar, back on the right.
            self.input.tap(round(self.width*.71), round(self.height*.973), self.width, self.height)
        else:
            self.adb('shell', 'input', 'keyevent', '4')
        time.sleep(self.args.delay)

    def wait_for(self, names):
        for _ in range(4):
            root = self.snapshot()
            for name in names:
                n = find(root, name)
                if n is not None:
                    return name, n
            time.sleep(self.args.delay)
        raise RuntimeError('未出现预期页面：' + ' / '.join(names))

    def return_list(self):
        for _ in range(4):
            root = self.snapshot()
            if self.menu_visible(root):
                self.recover_navigation(root)
                continue
            if not any(t in texts(root) for t in ['免费试活动详情', '确认报名信息', '报名成功']):
                if mine_selected(self.screenshot()):
                    self.recover_navigation(root)
                    continue
            if find(root, '报名成功') is not None:
                n = find(root, '完成')
                if n is None:
                    raise RuntimeError('报名结果页面缺少完成按钮。')
                self.tap(n)
            elif find(root, '免费试活动详情') is not None:
                self.back()
            elif '免费试天天抽' in texts(root) or ('全部商区' in texts(root) and '智能排序' in texts(root)):
                return root
            elif self.choices(root) or any(t in texts(root) for t in ['橙V专享免费试', '橙V专属免费试']):
                return root
            else:
                if not self.recover_navigation(root):
                    raise RuntimeError('当前不是可识别的免费抽列表，请进入免费试的查看全部列表。')
        raise RuntimeError('无法返回列表。')

    def apply(self, title, button):
        # Re-read immediately before opening an activity; never reuse old list coordinates.
        previous = bounds(button)
        current = next((n for t, n in self.choices(self.snapshot()) if t == title), None)
        if current is None or bounds(current) != previous:
            raise RecoverableUI('列表位置变化，重新识别活动。')
        button = current
        self.log('打开活动', title=title)
        self.tap(button)
        try:
            name, n = self.wait_for(['我要报名', '已报名,看看其他活动', '已报名，看看其他活动'])
        except RuntimeError:
            if self.recover_navigation(self.snapshot()):
                self.return_list()
                raise RecoverableUI('打开活动后发生导航偏移，已返回免费试。')
            raise
        if name != '我要报名':
            self.log('跳过已报名', title=title)
            self.return_list()
            return
        self.tap(n)
        _, confirm = self.wait_for(['确认报名'])
        if find(self.root, '确认报名信息') is None:
            raise RuntimeError('未识别确认报名信息弹窗。')
        ts = texts(self.root)
        if any(any(w in t for w in ['立即支付', '确认支付', '支付报名', '消耗PASS', '使用PASS卡', '兑换报名']) for t in ts):
            raise RuntimeError('出现支付或兑换选项，停止，请手动检查。')
        # 不猜测无标签勾选框；沿用页面现有协议/候补状态。
        self.log('提交报名', title=title)
        self.tap(confirm)
        try:
            self.wait_for(['报名成功'])
        except RuntimeError as e:
            raise RuntimeError('提交后未确认报名成功；不会自动重试提交，请手动检查。') from e
        self.success += 1
        self.log('报名成功', title=title, success=self.success)
        self.return_list()
        self.ensure_all_list()
        self.scroll_one_activity()

    def scroll_one_activity(self):
        root = self.return_list()
        distance, anchor, old_y = activity_step(root, self.width, self.height)
        _, top, _, bottom = list_area(self.width, self.height)
        sx = round(self.width*.2)
        start_y = bottom-round(self.height*.02)
        end_y = max(top+60, start_y-distance)
        self.log('报名后上移一个活动', pixels=start_y-end_y)
        if self.input:
            self.input.swipe(sx, start_y, sx, end_y, self.width, self.height, settle=.3)
        else:
            self.adb('shell', 'input', 'swipe', sx, start_y, sx, end_y, '1000')
        time.sleep(self.args.delay)
        after = self.snapshot()
        if anchor:
            match = find(after, anchor)
            if match is not None:
                self.log('活动上移核验', target_pixels=distance, actual_pixels=old_y-bounds(match)[1])

    def ensure_all_list(self):
        root = self.snapshot()
        if '评友中心' in texts(root):
            if '橙V立享0元吃喝玩乐' not in texts(root):
                tab = find(root, '橙V专享免费试')
                if tab is None or not inside(bounds(tab), list_area(self.width, self.height)):
                    raise RuntimeError('请先打开免费试的查看全部列表。')
                self.tap(tab)
                self.wait_for(['橙V立享0元吃喝玩乐'])
                root = self.root
            header = find(root, '橙V立享0元吃喝玩乐')
            nearby = [n for n in root.iter('node') if label(n) == '查看全部' and visible(n)
                      and abs(bounds(n)[1]-bounds(header)[1]) < 100]
            n = nearby[0] if len(nearby) == 1 else None
            if n is None:
                raise RuntimeError('未找到橙V免费试栏目的查看全部。')
            if not inside(bounds(n), list_area(self.width, self.height)):
                raise RuntimeError('查看全部靠近顶部菜单或底部导航，请手动进入列表后启动。')
            self.tap(n)
            self.wait_for(['免费试天天抽'])

    def run(self):
        if self.adb('get-state').strip() != 'device':
            raise RuntimeError('手机未连接。')
        sizes = re.findall(r'(\d+)x(\d+)', self.adb('shell', 'wm', 'size'))
        self.width, self.height = map(int, sizes[-1])
        root = self.snapshot()
        if self.args.inspect:
            self.log('只读检查', candidates=[t for t, _ in self.choices(root)],
                     page_markers=[t for t in texts(root) if t in ['报名成功', '免费试活动详情', '确认报名信息', '免费试天天抽']])
            return
        if self.args.input == 'uhid':
            from uhid_input import UhidInput
            self.input = UhidInput(self.args.adb, self.args.serial, self.run_dir)
            self.log('UHID 输入已连接')
        else:
            self.adb('shell', 'input', 'keyevent', '0')
        self.return_list()
        self.ensure_all_list()
        fingerprints = {}
        retry_counts = {}
        for scroll_index in itertools.count():
            while self.args.limit == 0 or self.success < self.args.limit:
                root = self.return_list()
                if '评友中心' in texts(root):
                    self.ensure_all_list()
                    root = self.snapshot()
                choices = [(t, n) for t, n in self.choices(root) if t not in self.seen]
                if not choices:
                    break
                title, button = choices[0]
                try:
                    self.apply(title, button)
                    self.seen.add(title)
                except RecoverableUI as e:
                    retry_counts[title] = retry_counts.get(title, 0) + 1
                    self.log('重新定位', title=title, reason=str(e), attempt=retry_counts[title])
                    if retry_counts[title] >= 3:
                        raise RuntimeError('同一活动连续三次定位失败，已停止。') from e
                    self.return_list()
                    self.ensure_all_list()
            if self.args.limit and self.success >= self.args.limit:
                break
            if self.args.max_scrolls and scroll_index >= self.args.max_scrolls:
                break
            fingerprint = hashlib.sha256('\n'.join(texts(root)).encode()).hexdigest()
            fingerprints[fingerprint] = fingerprints.get(fingerprint, 0) + 1
            if fingerprints[fingerprint] >= 3:
                self.log('列表停止变化，结束')
                break
            scrolls = [n for n in root.iter('node') if n.get('scrollable') == 'true' and visible(n)]
            if not scrolls:
                raise RuntimeError('没有可识别的滚动容器，停止以避免误滑。')
            region = max(scrolls, key=lambda n: (bounds(n)[2]-bounds(n)[0])*(bounds(n)[3]-bounds(n)[1]))
            x1, y1, x2, y2 = bounds(region)
            # Start gestures inside the activity area, never on the fixed bottom tabs.
            left, top, right, bottom = list_area(self.width, self.height)
            y1, y2 = max(y1, top), min(y2, bottom)
            self.log('滚动列表', scroll=scroll_index+1)
            # The center of the screen can be the horizontal filter strip on first load.
            # Start near the bottom of the unobscured cards, away from action buttons.
            sx = round(self.width * (.2 if fingerprints[fingerprint] == 1 else .35))
            start_y = y2 - round(self.height*.02)
            end_y = max(y1 + 60, start_y-round(self.height*.4))
            if self.input:
                self.input.swipe(sx, start_y, sx, end_y, self.width, self.height)
            else:
                self.adb('shell', 'input', 'swipe', sx, start_y, sx, end_y, '650')
            time.sleep(self.args.delay)
        self.log('运行结束', success=self.success)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', default=r'D:\Android\platform-tools-latest-windows\platform-tools\adb.exe')
    p.add_argument('--serial', default='90acad9')
    p.add_argument('--limit', type=int, default=0, help='本次成功报名上限；0 表示不限')
    p.add_argument('--max-scrolls', type=int, default=0, help='滚动次数上限；0 表示不限')
    p.add_argument('--delay', type=float, default=2.5)
    p.add_argument('--inspect', action='store_true', help='只读检查，不点击')
    p.add_argument('--input', choices=['uhid', 'adb'], default='uhid')
    args = p.parse_args()
    if args.limit < 0 or args.max_scrolls < 0 or args.delay < 1:
        p.error('limit >= 0, max-scrolls >= 0, delay >= 1')
    bot = Bot(args)
    print('大众点评免费抽自动报名（包含普通活动）', flush=True)
    print('只读检查，不点击。' if args.inspect else
          f'请保持查看全部列表在前台。本次报名：{str(args.limit)+" 项以内" if args.limit else "不限数量"}，按 Ctrl+C 停止。', flush=True)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.log('用户停止', success=bot.success)
        return 130
    except Exception as e:
        bot.log('停止', reason=str(e), success=bot.success)
        if 'INJECT_EVENTS' in str(e):
            print('手机拒绝自动点击：请开启开发者选项中的 USB 调试（安全设置）。这不是编码错误。', flush=True)
        return 1
    finally:
        if bot.input:
            bot.input.close()
        if bot.reader_ready:
            bot.adb('shell', 'rm', '-f', bot.reader_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
