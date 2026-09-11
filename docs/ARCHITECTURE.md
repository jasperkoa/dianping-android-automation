# Architecture

## 1. Overview

本项目是单设备、闭环的 Android UI 自动化执行器。主要由五层构成：

1. **Transport**：ADB 负责 Windows 与 Android 设备之间的进程、文件和端口传输。
2. **Perception**：`UiDump.java` 通过 Android `UiAutomation` 读取当前 Accessibility 树，并输出 XML。
3. **Domain parsing**：`auto_apply.py` 将 XML 节点转换成页面状态和活动候选。
4. **Actuation**：`uhid_input.py` 使用 scrcpy control channel 创建临时 UHID 触摸设备，执行 tap/swipe。
5. **Audit**：所有关键状态转换记录为 `logs/<timestamp>/events.jsonl`。

## 2. Control flow

```text
resolve adb/device
    |
read current UI
    |
validate target package / risk state
    |
parse visible candidates
    |
open one candidate
    |
verify detail state
    |
verify confirmation state
    |
reject payment / PASS / verification
    |
submit
    |
require explicit success state
    |
return to list
    |
re-read UI and continue
```

系统采用“观察 → 判断 → 操作 → 再观察”的闭环模式，不假设上一步一定成功。

## 3. Data flow

### UI read channel

```text
Android Accessibility tree
  -> UiAutomation
  -> UiDump.java
  -> XML stdout over adb shell
  -> xml.etree.ElementTree
  -> page/candidate model
```

完整 UI XML 仅在内存中解析，不写入正常业务日志。

### Input channel

```text
Python
  -> local TCP socket
  -> adb forward
  -> scrcpy Server control channel
  -> UHID_CREATE / UHID_INPUT
  -> Android input subsystem
  -> target app
```

UHID 输入与 scrcpy GUI 投屏相互独立。

## 4. Device abstraction

设备不再硬编码序列号。启动时：

- 如果 `--serial` / `ANDROID_SERIAL` 已设置，使用指定设备；
- 否则查询 `adb devices`；
- 恰好一台 `device` 时自动选择；
- 多台设备时拒绝猜测并要求显式指定。

ADB 路径同样通过 `--adb` / `ADB_PATH` / `PATH` 解析。

## 5. Navigation abstraction

Android 的“返回”不是所有设备都能通过同一种方式完成，因此提供：

- `adb`: `input keyevent 4`
- `gesture-left`
- `gesture-right`
- `nav-left`
- `nav-right`

UHID 触摸模式只模拟触摸事件，因此三键/手势返回本质上是对 Android 导航区域的可配置触摸或滑动。

## 6. Failure model

以下状态 fail closed：

- 目标 App 不在前台；
- UI helper 无法读取页面；
- 未出现预期页面；
- 验证码/人机验证/频率限制；
- 支付/PASS/兑换；
- 提交后无法确认成功；
- 无法识别滚动容器；
- UHID 未被 Android 识别为 direct input device。

提交动作不自动重试，避免“服务器已成功、客户端未看到回执”时重复提交。

## 7. Runtime files

每次运行生成：

```text
logs/YYYYMMDD-HHMMSS/events.jsonl
logs/YYYYMMDD-HHMMSS/uhid-server.log
```

这些文件均被 `.gitignore` 排除。
