# Dianping Android Physical-Device Automation

基于 **ADB + Android UiAutomation + scrcpy UHID** 的大众点评免费试真机 UI 自动化项目。控制端读取真实 Android 手机的当前控件树，通过结构化状态判断执行 UI 操作，并在结果不明确、出现验证码/频控、支付或兑换流程时停止。

> **适用范围**：Android 真机。项目不支持 iOS，也无法保证所有厂商 ROM、Android 版本和未来 App 页面都保持兼容。仓库已移除设备序列号、用户名、绝对路径、实机截图、历史日志和真实活动记录；所有本机配置通过 CLI 或 `config.local.cmd` 注入。

## 特性

- 单台 Android 真机通过 USB/ADB 运行，不依赖模拟器。
- 当只连接一台已授权设备时自动选择设备；多设备时必须显式指定 `--serial`。
- ADB 路径从 `PATH` 自动发现，也可通过 `--adb` / `ADB_PATH` 指定。
- UHID 输入不依赖 Windows 鼠标坐标，适合部分拒绝 `adb shell input` 的 ROM。
- scrcpy-server 不再绑定固定 WinGet 目录；支持自动发现或显式指定路径。
- 支持多种返回导航策略：ADB keyevent、左右边缘返回手势、左右三键导航。
- 免费试活动候选不再以“橙V”作为硬性条件；普通免费试活动和橙V活动都可被识别。
- 每次操作后重新读取当前 UI，避免依赖固定坐标和固定页面顺序。
- 仅明确读取到“报名成功”才计入成功；提交结果不明确时不会自动重复提交。
- 检测到验证码、频控、支付/PASS 等状态时停止并要求人工处理。
- 运行日志采用 JSONL，`logs/` 默认被 `.gitignore` 排除。

## 架构

```text
Windows / Python
      |
      +-- ADB -----------------------> Android device
      |                                 |
      |                                 +-- app_process + UiDump.java
      |                                 |       |
      |<----------- XML UI tree --------+
      |
      +-- scrcpy control channel ----> UHID virtual touchscreen
                                        |
                                        v
                                  Target Android App
```

详细设计见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 环境要求

### 控制端

- Windows 10/11（当前启动脚本以 Windows 为主）。
- Python 3.10+。
- Android SDK Platform-Tools，要求 `adb devices` 能识别真机。
- scrcpy。UHID 控制协议已按 scrcpy 4.x 方式实现，建议优先使用已验证版本；若升级后协议发生变化，请先执行只读检查并验证输入通道。

### 手机端

- Android 真机。
- 开启“开发者选项 → USB 调试”。
- 首次连接时在手机上确认电脑的 RSA 调试授权。
- 某些 MIUI/HyperOS 设备如需使用 ADB 输入，可能还需要“USB 调试（安全设置）”；使用 UHID 时通常不依赖普通 `input tap` 权限，但 OEM 行为仍可能不同。
- 目标 App 已安装、已登录，并保持在前台。

## 安装

### 1. 克隆仓库

```powershell
git clone https://github.com/jasperkoa/dianping-android-automation.git
cd dianping-android-automation
```

### 2. 检查 ADB

```powershell
adb devices
```

理想输出：

```text
List of devices attached
XXXXXXXX    device
```

如果 `adb` 不在 PATH，可以在后续命令中使用：

```powershell
.\run.cmd --adb "C:\path\to\platform-tools\adb.exe" --inspect
```

### 3. 本地配置（推荐）

复制：

```powershell
Copy-Item .\config.example.cmd .\config.local.cmd
```

`config.local.cmd` 已加入 `.gitignore`，可安全写入本机路径和设备序列号，不会被 Git 默认提交。

只有一台手机时，通常无需填写 `ANDROID_SERIAL`。多台设备时填写：

```bat
set "ANDROID_SERIAL=YOUR_DEVICE_SERIAL"
```

### 4. 选择返回方式

不同手机导航方式不同。先从：

```bat
set "ANDROID_BACK_MODE=adb"
```

开始测试。

如果 ROM 拒绝 `adb shell input keyevent 4`，使用 UHID 返回：

| 手机导航方式      | 建议配置            |
| ----------- | --------------- |
| 全面屏手势，左边缘返回 | `gesture-left`  |
| 全面屏手势，右边缘返回 | `gesture-right` |
| 三键导航，返回键在左侧 | `nav-left`      |
| 三键导航，返回键在右侧 | `nav-right`     |

例如：

```bat
set "ANDROID_BACK_MODE=nav-right"
```

如果三键位置与默认比例不同，可通过 CLI 调整：

```powershell
.\run.cmd --back-mode nav-right --back-x-ratio 0.72 --back-y-ratio 0.97
```

## 首次运行：只读检查

**强烈建议先运行只读模式。** 手动进入大众点评免费试活动的“查看全部”列表并保持页面前台，然后：

```powershell
.\inspect.cmd
```

它会：

1. 连接目标 Android 设备；
2. 读取当前 UiAutomation 控件树；
3. 验证目标 App 在前台；
4. 输出当前可识别的活动候选；
5. 不创建点击动作、不提交报名。

多设备：

```powershell
.\inspect.cmd --serial YOUR_DEVICE_SERIAL
```

## 执行

确认只读检查结果正确后：

```powershell
.\run.cmd --input uhid --limit 3 --max-scrolls 10 --back-mode adb
```

常用参数：

| 参数                 | 默认值               | 说明                    |
| ------------------ | -----------------:| --------------------- |
| `--serial`         | 自动                | 目标 ADB 设备；连接多台设备时必须指定 |
| `--adb`            | 自动                | `adb` 可执行文件路径         |
| `--package`        | `com.dianping.v1` | 目标 Android 包名         |
| `--input`          | `uhid`            | 输入通道：`uhid` / `adb`   |
| `--limit`          | `10`              | 单次成功操作上限              |
| `--max-scrolls`    | `30`              | 最大向下滚动次数              |
| `--delay`          | `2.5`             | 每次 UI 操作后的等待时间（秒）     |
| `--inspect`        | false             | 只读取，不点击               |
| `--back-mode`      | `adb`             | 返回方式                  |
| `--scrcpy-server`  | 自动                | scrcpy-server 文件路径    |
| `--scrcpy-version` | 自动                | scrcpy server 版本      |

停止运行：在终端中按 `Ctrl+C`。

## 投屏观察

仓库附带：

```powershell
.\mirror-device.cmd
```

默认使用：

```text
--mouse=uhid --turn-screen-off --stay-awake --max-size=1280 --max-fps=30 --video-bit-rate=4M --no-audio
```

它只用于人工观察和接管，不是业务自动化执行通道。

## 数据与隐私

公开仓库不应提交以下内容：

- `config.local.cmd`
- `logs/`
- 实机截图
- ADB 设备序列号
- 本机用户名或绝对目录
- 账号、手机号、Cookie、Token、验证码

`.gitignore` 已覆盖常见本地文件，但在 `git push` 前仍建议执行：

```powershell
git status
git diff --cached
```

确认暂存区没有私密数据。

## 兼容性说明

“通用 Android 真机支持”意味着代码不再绑定某个设备型号、序列号或固定安装目录，并提供可配置导航策略；它不意味着所有 ROM 都必然兼容。主要变量包括：

- OEM 对 ADB/UiAutomation/UHID 的限制；
- Android 版本差异；
- 三键导航位置或手势实现；
- App 页面结构、文案、WebView/自绘组件变化；
- scrcpy server/control protocol 版本变化。

任何 App 大版本更新后，应先运行 `inspect.cmd`，再以小的 `--limit` 验证。

## 安全边界

本项目不会尝试绕过验证码、人机验证、短信验证、频率限制、支付确认或平台风控。检测到这些状态时应停止自动执行并由人工处理。请仅在你有权操作的设备与账号上使用，并遵守目标服务的使用条款及当地法规。

## 测试

本地运行纯解析单元测试：

```powershell
python -m unittest discover -s tests -v
```

GitHub Actions 会在 push / pull request 时运行同一组无需真机的测试。

## 项目文件

```text
.
├─ .github/workflows/tests.yml
├─ android/
│  ├─ UiDump.java
│  └─ prebuilt/ui-dump.jar
├─ docs/
│  ├─ ARCHITECTURE.md
│  └─ TROUBLESHOOTING.md
├─ src/
│  ├─ auto_apply.py
│  └─ uhid_input.py
├─ tests/
│  └─ test_parser.py
├─ config.example.cmd
├─ inspect.cmd
├─ mirror-device.cmd
├─ run.cmd
├─ CONTRIBUTING.md
├─ SECURITY.md
├─ THIRD_PARTY_NOTICES.md
├─ LICENSE
└─ README.md
```

## License

MIT。第三方依赖和协议说明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
