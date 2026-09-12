# Mi 9 SE 实机实例：大众点评免费抽自动报名

> 本分支是针对 **Xiaomi Mi 9 SE** 的可运行实机实例，重点展示如何在 Windows + ADB + scrcpy UHID 环境下，对大众点评“免费试 / 免费抽”列表进行**只读检测、单项测试、限量自动报名和连续自动报名**。
>
> 仓库：<https://github.com/jasperkoa/dianping-android-automation>  
> 当前实机分支：<https://github.com/jasperkoa/dianping-android-automation/tree/mi9se>  
> 返回通用说明：<https://github.com/jasperkoa/dianping-android-automation/tree/main>

---

## 1. 这个实例能做什么

本实例面向大众点评“免费试”的“查看全部”列表，自动识别页面中可见的 **“免费抽” / “免费抽奖”** 按钮，并按列表顺序执行报名。

当前逻辑**不再以橙 V、会员徽标或会员身份作为筛选条件**。只要活动卡片中存在可识别、可见且位于安全点击区域内的“免费抽 / 免费抽奖”按钮，就可以成为候选活动。

自动报名的主流程为：

```text
读取当前页面
    ↓
识别可报名活动
    ↓
打开活动详情
    ↓
点击“我要报名”
    ↓
识别“确认报名信息”
    ↓
点击“确认报名”
    ↓
等待并核验“报名成功”
    ↓
返回免费试列表
    ↓
上移约一个活动卡片高度
    ↓
重新读取页面并处理下一项
```

脚本不会自动处理以下流程：

- 0 元领、兑换、付费购买等非“免费抽”流程；
- 需要“立即支付 / 确认支付 / 支付报名”的页面；
- 要求消耗 PASS、使用 PASS 卡或兑换资格的流程；
- 滑块验证、人机验证、短信验证码；
- 平台提示“操作频繁 / 操作太频繁”等风控状态；
- 无法识别的新弹窗、新页面或大众点评后续改版页面。

遇到上述情况时，程序优先**停止而不是继续猜测点击**。

---

## 2. 本分支的实机环境

这一分支不是纯通用模板，而是已经针对一台真实的小米 9 SE 做过适配和验证。

当前代码中的默认实机参数为：

| 项目 | 当前实例值 |
|---|---|
| 手机 | Xiaomi Mi 9 SE |
| ADB 设备序列号 | `90acad9` |
| 屏幕方向 | 竖屏 |
| 实机分辨率 | `1080 × 2340` |
| Android 导航方式 | 三键导航 |
| 大众点评包名 | `com.dianping.v1` |
| 默认输入方式 | scrcpy 4.1 UHID |
| ADB 默认路径 | `D:\Android\platform-tools-latest-windows\platform-tools\adb.exe` |
| Python | 本机优先 Python 3.11，兼容脚本中的 3.12 回退 |
| Python 图像依赖 | Pillow |
| 页面控件读取 | `build/ui-dump.jar` |

`uhid_input.py` 当前还会直接查找下面的 scrcpy 4.1 server：

```text
%LOCALAPPDATA%\Microsoft\WinGet\Packages\
Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe\
scrcpy-win64-v4.1\scrcpy-server
```

因此，如果你的手机序列号、ADB 安装位置、分辨率、导航方式或 scrcpy 版本与本实例不同，需要先修改配置，不能假定复制目录后即可直接运行。

---

## 3. 目录结构

本实例的主要文件如下：

```text
Mi9SE\
├─ start-dianping.bat          # 自动报名入口
├─ check-dianping.bat          # 只读检查入口，不执行点击和报名
├─ start-mi9se.bat             # 启动 Mi 9 SE 的 scrcpy 投屏/UHID 环境
├─ watch-mi9se.bat             # scrcpy 看门狗，断开后自动等待并重启
└─ dianping-auto\
   ├─ auto_apply.py            # 自动报名主程序
   ├─ screen_guard.py          # 屏幕安全区域、橙色按钮、底部导航识别
   ├─ uhid_input.py            # scrcpy 4.1 UHID 触控输入
   ├─ run.cmd                  # Python 启动器
   ├─ start.bat                # dianping-auto 内部启动入口
   ├─ inspect.bat              # dianping-auto 内部只读检查入口
   ├─ test_parser.py           # 活动解析单元测试
   ├─ test_screen_guard.py     # 点击保护、滚动及恢复逻辑单元测试
   ├─ UiDump.java              # 页面控件读取工具源码
   ├─ build\ui-dump.jar        # 已构建的页面控件读取工具
   └─ logs\                    # 每次运行生成的日志目录
```

目录中的 `debug-*.png`、`current.png`、`logs\...`、`__pycache__` 等文件主要属于调试或运行产物，不是自动报名核心代码。

---

## 4. 首次使用前准备

### 4.1 Windows 端需要的软件

需要准备：

1. **ADB / Android Platform Tools**
2. **Python 3**
3. **Pillow**
4. **scrcpy 4.1**
5. USB 数据线和可正常进行 ADB 调试的小米 9 SE

本实例的 `run.cmd` 会按以下顺序寻找 Python：

```text
%LOCALAPPDATA%\Programs\Python\Python311\python.exe
D:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe
PATH 中的 python.exe
```

安装 Pillow：

```cmd
python -m pip install Pillow
```

当前版本**不依赖 NumPy**，也不再使用旧的橙 V 徽标图片模板。

### 4.2 手机端设置

手机需要：

- 已开启开发者选项；
- 已开启 USB 调试；
- 首次连接电脑时已经在手机上允许该电脑进行 USB 调试；
- 运行自动化时保持大众点评位于前台；
- 保持竖屏；
- 保持三键导航；
- 自动化运行过程中不要手动操作手机页面。

如果改成全面屏手势、横屏或其他分辨率，现有安全区域和底部导航坐标可能不再适用。

---

## 5. 第一步：确认 ADB 能找到手机

打开 CMD：

```cmd
D:\Android\platform-tools-latest-windows\platform-tools\adb.exe devices
```

本实例期望看到类似：

```text
List of devices attached
90acad9    device
```

如果显示 `unauthorized`，需要解锁手机并确认 USB 调试授权。

如果没有设备，则先检查 USB 数据线、USB 模式、驱动和开发者选项。

还可以单独检查目标设备：

```cmd
D:\Android\platform-tools-latest-windows\platform-tools\adb.exe -s 90acad9 get-state
```

正常结果应为：

```text
device
```

---

## 6. 第二步：启动 Mi 9 SE 投屏环境

双击：

```text
start-mi9se.bat
```

这个脚本会：

1. 检查固定路径中的 `adb.exe`；
2. 检查 `scrcpy.exe` 是否存在于 PATH；
3. 启动 ADB server；
4. 检查设备 `90acad9` 是否在线；
5. 使用 scrcpy 启动 Mi 9 SE 投屏。

当前 scrcpy 启动参数为：

```text
--mouse=uhid
--turn-screen-off
--stay-awake
--max-size=1280
--max-fps=30
--video-bit-rate=4M
--no-audio
```

这意味着可以在电脑上观察手机画面，同时使用 UHID 模式向 Android 注入触控，避免占用 Windows 系统鼠标进行模拟点击。

如果希望 scrcpy 关闭或断开后自动重新等待手机并再次启动，可以使用：

```text
watch-mi9se.bat
```

`watch-mi9se.bat` 会每 5 秒检查一次指定设备，设备恢复后重新启动 scrcpy。

> `watch-mi9se.bat` 只负责投屏守护，不负责自动报名。

---

## 7. 第三步：把大众点评停在正确页面

推荐先手动打开大众点评并进入：

```text
免费试 → 查看全部
```

也可以从类似下面的入口进入：

```text
评友中心 → 橙V专享免费试 → 查看全部
```

这里的“橙V专享免费试”只是一个**入口名称**，不是脚本的报名筛选条件。

脚本进入综合列表后，会同时识别普通活动和带会员标识的活动。

如果“查看全部”靠近顶部工具栏、当前页面结构无法安全识别，脚本会要求先手动进入列表，而不是冒险点击顶部区域。

---

## 8. 强烈建议先做只读检查

第一次运行、App 更新后、切换账号后或页面布局发生变化后，不要直接开始连续报名。

先双击：

```text
check-dianping.bat
```

等价命令为：

```cmd
dianping-auto\run.cmd --inspect
```

只读检查会读取当前大众点评页面，输出当前屏幕识别到的候选活动，例如：

```json
{"event":"只读检查","candidates":["活动 A","活动 B"]}
```

`--inspect` 模式：

- 不点击；
- 不报名；
- 不滚动列表；
- 只读取当前屏幕；
- 会生成本次运行日志。

如果候选列表为空，不一定代表整个免费试列表没有活动，也可能只是当前可视区域没有露出可报名按钮。可以手动向下滚动一段后再次检查。

---

## 9. 第四步：先做 1 项实机报名测试

确认只读识别正常后，建议先执行 **1 项限量测试**：

```cmd
start-dianping.bat --limit 1 --max-scrolls 5
```

或者：

```cmd
dianping-auto\run.cmd --input uhid --limit 1 --max-scrolls 5
```

参数含义：

- `--limit 1`：本次最多成功报名 1 项；
- `--max-scrolls 5`：最多执行有限次数的列表滚动；
- `--input uhid`：使用 scrcpy UHID 输入。

第一次实机验证时，建议全程观察投屏窗口，确认以下行为均正确：

```text
识别“免费抽”
→ 打开正确活动
→ 点击“我要报名”
→ 出现“确认报名信息”
→ 点击“确认报名”
→ 出现“报名成功”
→ 返回列表
→ 页面上移约一个活动卡片
```

只有单项流程验证无误后，再扩大报名数量。

---

## 10. 限量自动报名

例如最多成功报名 10 项：

```cmd
start-dianping.bat --limit 10
```

同时限制列表滚动次数：

```cmd
start-dianping.bat --limit 10 --max-scrolls 20
```

还可以调整每次点击后的等待时间：

```cmd
start-dianping.bat --limit 10 --max-scrolls 20 --delay 3
```

`--delay` 单位为秒，代码要求不能小于 `1`。

如果页面加载较慢，适当增大 `--delay` 会比盲目加快点击更安全。

---

## 11. 连续自动报名

直接双击：

```text
start-dianping.bat
```

当前文件中的默认值为：

```bat
set "LIMIT=0"
set "MAX_SCROLLS=0"
```

这里：

- `LIMIT=0` 表示不限制本次成功报名数量；
- `MAX_SCROLLS=0` 表示不限制滚动次数。

因此默认运行模式会持续处理列表，直到发生以下情况之一：

- 列表内容连续停止变化；
- 遇到无法识别的页面；
- 遇到验证或频率限制；
- 出现支付、PASS、兑换等不允许自动处理的流程；
- 同一活动连续 3 次重新定位失败；
- 页面恢复次数超过限制；
- ADB/UHID/页面读取出现错误；
- 用户按 `Ctrl+C` 主动停止。

### 停止运行

激活运行脚本的 CMD 窗口后按：

```text
Ctrl+C
```

如果 Windows 询问是否终止批处理，输入：

```text
Y
```

然后回车。

不要同时启动多个自动报名窗口操作同一台手机。

---

## 12. 完整命令行参数

`auto_apply.py` 当前支持：

```text
--adb PATH
--serial SERIAL
--limit N
--max-scrolls N
--delay SECONDS
--inspect
--input {uhid,adb}
```

### `--adb`

指定 ADB 可执行文件路径。

默认：

```text
D:\Android\platform-tools-latest-windows\platform-tools\adb.exe
```

换电脑后可以临时指定：

```cmd
dianping-auto\run.cmd --adb "C:\Android\platform-tools\adb.exe" --inspect
```

### `--serial`

指定 ADB 设备序列号。

默认：

```text
90acad9
```

如果连接另一台手机：

```cmd
dianping-auto\run.cmd --serial YOUR_SERIAL --inspect
```

但要注意：**修改序列号只解决 ADB 目标设备问题，并不代表现有 Mi 9 SE 的坐标和屏幕保护逻辑自动兼容另一台手机。**

### `--limit`

本次最多成功报名多少项。

```text
0 = 不限
1 = 最多成功 1 项
10 = 最多成功 10 项
```

### `--max-scrolls`

限制列表滚动次数。

```text
0 = 不限
```

### `--delay`

点击或页面动作后的等待时间，默认：

```text
2.5 秒
```

代码要求：

```text
--delay >= 1
```

### `--inspect`

只读检查，不点击、不报名。

### `--input uhid`

默认模式。使用 scrcpy 4.1 UHID 模拟触摸屏输入。

优点是不会占用 Windows 鼠标，并且当前 Mi 9 SE 实机验证主要基于此模式。

### `--input adb`

使用 Android `input tap / input swipe`。

例如：

```cmd
dianping-auto\run.cmd --input adb --limit 1
```

部分 MIUI / Android 环境可能会拒绝此类事件注入。如果日志出现 `INJECT_EVENTS` 或 ADB 权限相关错误，需要检查开发者选项中的 USB 调试安全设置；本实例默认仍推荐 UHID。

---

## 13. 自动报名时脚本做了哪些保护

这不是简单的“固定坐标连点”。当前代码包含多层保护。

### 13.1 每次点击活动前重新读取页面

脚本不会直接复用很早以前保存的按钮坐标。

打开活动前会重新读取 UI，并核对活动标题及按钮坐标；如果列表位置已经变化，会放弃本次旧坐标并重新定位。

日志中会出现：

```text
重新定位
```

### 13.2 排除顶部工具栏和底部导航区

Mi 9 SE 当前实机安全列表区域大约限制在：

```text
顶部：屏幕高度的 10.5% 以下不点击
底部：屏幕高度的 85% 以后不点击
```

这样可以避免把顶部菜单或底部导航中的元素误认成活动按钮。

### 13.3 点击前检查按钮颜色

对于：

```text
免费抽
免费抽奖
我要报名
确认报名
```

脚本在点击前还会截图检查目标区域是否符合当前观察到的橙色按钮特征。

颜色不符合时取消点击并重新定位。

### 13.4 报名成功后再继续

点击“确认报名”以后，脚本必须识别到：

```text
报名成功
```

才会把成功计数加 1。

如果提交后无法确认“报名成功”，程序会停止，并且**不会自动重复提交该活动**，避免因页面状态不明确造成重复动作。

### 13.5 检测支付、PASS 和兑换流程

如果确认页面出现类似：

```text
立即支付
确认支付
支付报名
消耗PASS
使用PASS卡
兑换报名
```

程序立即停止，要求人工检查。

### 13.6 检测验证码和平台频率限制

如果页面出现：

```text
安全验证
滑块验证
操作频繁
操作太频繁
短信验证码
人机验证
```

程序停止，等待用户手动处理。

### 13.7 页面恢复

当前实机已经针对两类误导航做过恢复：

- 误入带底部导航的“我的”等页面时，尝试点击左侧“免费试”页签返回；
- 误打开已识别的“更多 / 分享”弹层时，通过再次点击右上角菜单触发点关闭。

自动恢复次数最多为 3 次，超过后停止。

---

## 14. 为什么每报名成功一项都要上移一个活动

成功报名后，程序不是把当前屏幕所有按钮全部点完再翻页，而是固定执行：

```text
报名成功 → 返回列表 → 上移一个活动卡片 → 重新识别
```

滑动距离优先通过相邻活动标题的纵向间距动态测量。

如果当前页面无法计算出可靠间距，则 Mi 9 SE 使用约：

```text
335 px
```

作为回退值。

UHID 滑动松手前还会增加短暂停顿，减少惯性导致一次滑过多个活动的概率。

日志可能看到：

```json
{"event":"报名后上移一个活动","pixels":381}
{"event":"活动上移核验","target_pixels":381,"actual_pixels":374}
```

---

## 15. 测试：先验证代码，再验证真机

本实例包含两层测试：

1. **Python 单元测试**：验证解析、安全区域、按钮识别及关键流程；
2. **Mi 9 SE 实机测试**：验证真实 App 页面、ADB、UHID、报名弹窗和返回流程。

### 15.1 运行全部单元测试

进入目录：

```cmd
cd /d D:\Android\Mi9SE\dianping-auto
```

执行：

```cmd
python -m unittest -v test_parser.py test_screen_guard.py
```

也可以使用自动发现：

```cmd
python -m unittest discover -v
```

当前上传的这版源码共包含 **13 个单元测试**。本 README 编写时已对该源码执行：

```text
Ran 13 tests
OK
```

### 15.2 `test_parser.py` 主要验证什么

包括：

- 普通活动和会员活动都能被识别；
- 不要求存在橙 V 徽标；
- 隐藏的“免费抽”按钮不会成为候选；
- 已报名活动会被排除；
- 活动标识不会错误包含价格；
- 价格/名额/按钮容器不会被误判为活动标题。

### 15.3 `test_screen_guard.py` 主要验证什么

包括：

- 报名成功后确实按“返回列表 → 确认列表 → 上移一个活动”的顺序执行；
- 活动卡片高度计算包含已经报名的行；
- 无法计算卡片高度时回退到约 335 px，而不是整页大幅滚动；
- “更多”菜单能被识别，而“更多筛选”不会被错误识别成菜单；
- 顶部工具栏和底部导航中的按钮被排除；
- 灰色“我的”页签不会被误判为橙色报名按钮；
- 被底部区域遮挡的按钮不会进入重试候选。

### 15.4 单元测试通过不等于实机一定安全

单元测试验证的是代码逻辑，无法完全模拟：

- 大众点评线上页面更新；
- 网络加载速度；
- 不同账号的弹窗；
- 不同城市的活动样式；
- Android 系统权限；
- scrcpy / ADB 版本差异；
- 手机分辨率和导航方式变化。

因此每次重大改动后仍应依次做：

```text
单元测试
→ --inspect 只读检查
→ --limit 1 单项实机测试
→ 少量限量报名
→ 连续运行
```

---

## 16. 实机测试记录

### 2026-09-12

当前源码和日志中已经验证：

- 普通活动与会员活动均可进入候选；
- “湘识府”报名成功；
- “八爷涮肉”报名成功；
- 故意进入“我的”后，可以自动返回“免费试”；
- 返回后保留本次已经处理的活动记录；
- 误打开右上角“更多”菜单后可以关闭并继续停留在免费试流程；
- 报名成功后按活动卡片高度继续滚动；
- 上传实例中的 `20260912-174514` 运行日志在用户主动停止前记录到 `success = 22`。

这说明当前代码已经有真实设备连续运行记录，但**不代表大众点评后续版本、其他账号、其他城市或其他手机一定保持相同页面结构**。

---

## 17. 日志在哪里

每次运行都会创建：

```text
dianping-auto\logs\YYYYMMDD-HHMMSS\
```

主要日志：

```text
events.jsonl
```

UHID 模式还会生成：

```text
uhid-server.log
```

`events.jsonl` 每一行都是一个 JSON 对象，适合人工查看，也适合后续程序分析。

常见事件包括：

```text
只读检查
UHID 输入已连接
打开活动
提交报名
报名成功
报名后上移一个活动
活动上移核验
重新定位
返回底部免费试页签
关闭误开的更多菜单
滚动列表
列表停止变化，结束
运行结束
用户停止
停止
```

脚本不会把完整页面 XML 直接写进日志，以减少把电话号码等页面字段落盘的风险。

---

## 18. 如何判断程序是否正常结束

`run.cmd` 最后会打印：

```text
Exit code: N
```

常见含义：

| Exit code | 含义 |
|---:|---|
| `0` | 正常结束，例如达到数量限制或列表停止变化 |
| `1` | 运行过程中发生错误并停止 |
| `2` | 找不到 Python |
| `130` | 用户通过 `Ctrl+C` 停止 |

注意：

```text
Exit code: 0
```

只代表程序按当前逻辑正常结束，**不等于平台上的所有活动都已经报名**。

---

## 19. 常见问题

### 19.1 `Device ... is not available`

先执行：

```cmd
adb devices
```

确认目标序列号存在且状态为 `device`。

如果换了手机，需要修改：

- `start-mi9se.bat` 中的 `SERIAL`；
- `watch-mi9se.bat` 中的 `SERIAL`；
- 或运行 `run.cmd` 时传入新的 `--serial`。

### 19.2 `adb.exe not found`

本实例写死了：

```text
D:\Android\platform-tools-latest-windows\platform-tools\adb.exe
```

如果你的 Platform Tools 在其他位置，需要修改 BAT 和/或通过 `--adb` 指定。

### 19.3 `scrcpy.exe is not available in PATH`

执行：

```cmd
where scrcpy
```

如果找不到，需要安装 scrcpy 或把 `scrcpy.exe` 所在目录加入 PATH。

### 19.4 `找不到已安装的 scrcpy 4.1 server`

自动报名的 UHID 代码当前查找固定 WinGet 路径下的：

```text
scrcpy-win64-v4.1\scrcpy-server
```

如果你升级了 scrcpy、改用 ZIP 版或者安装目录不同，需要修改 `uhid_input.py` 中的 server 路径。

### 19.5 `大众点评未在前台`

把大众点评切回前台，并进入免费试相关页面后重新启动。

### 19.6 `屏幕方向或尺寸变化，请保持手机竖屏`

当前实例会读取设备分辨率，并且截图尺寸必须与竖屏状态一致。

不要在运行过程中旋转手机。

### 19.7 `当前不是可识别的免费抽列表`

先手动进入：

```text
免费试 → 查看全部
```

然后先执行：

```text
check-dianping.bat
```

确认候选识别正常。

### 19.8 `检测到验证或频率限制`

手动处理验证，并评估是否应该继续运行。

脚本不会尝试绕过验证码、滑块验证或平台频率限制。

### 19.9 `出现支付或兑换选项，停止`

这是保护逻辑。

当前脚本只处理免费抽报名，不自动确认支付、兑换或 PASS 消耗。

### 19.10 `同一活动连续三次定位失败`

说明活动位置或页面布局持续变化。

不要马上无限重试。先用 `--inspect` 查看当前页面，必要时重新适配页面解析或安全区域。

### 19.11 `没有可识别的滚动容器`

当前页面可能不是活动列表，或者大众点评页面结构已经变化。

先人工确认页面，再执行只读检查。

---

## 20. 修改配置的位置

如果只是在同一台 Mi 9 SE 上调整每次运行数量，可以直接编辑：

```text
start-dianping.bat
```

例如：

```bat
set "LIMIT=10"
set "MAX_SCROLLS=20"
```

如果换 ADB 路径或设备，需要重点检查：

```text
start-mi9se.bat
watch-mi9se.bat
dianping-auto\auto_apply.py
```

如果 scrcpy 4.1 安装目录发生变化，需要检查：

```text
dianping-auto\uhid_input.py
```

如果换分辨率、导航方式或页面安全区域，需要重新测试：

```text
dianping-auto\screen_guard.py
```

修改后至少重新执行：

```cmd
python -m unittest -v test_parser.py test_screen_guard.py
check-dianping.bat
start-dianping.bat --limit 1 --max-scrolls 5
```

---

## 21. 推荐的实际使用顺序

每次重新部署或修改代码后，建议严格按照下面的顺序：

```text
1. USB 连接并解锁 Mi 9 SE
2. adb devices 确认 90acad9 = device
3. 启动 start-mi9se.bat
4. 手动打开大众点评
5. 进入“免费试 → 查看全部”
6. 运行 Python 单元测试
7. 双击 check-dianping.bat 做只读检查
8. 执行 start-dianping.bat --limit 1 --max-scrolls 5
9. 核对这 1 项的完整报名与返回流程
10. 再执行 --limit 5 或 --limit 10 的小批量测试
11. 确认日志正常后，再考虑默认不限数量运行
12. 需要停止时在 CMD 中按 Ctrl+C
```

这个顺序比直接双击无限报名模式更容易发现页面改版、权限变化和坐标适配问题。

---

## 22. 使用边界与风险说明

这是一个基于真实设备和当前大众点评 UI 行为制作的自动化实例，不是大众点评官方工具。

请注意：

- App 更新后页面结构可能变化；
- 自动化行为可能受到账号状态、城市、网络和平台风控影响；
- 不应尝试绕过验证码、人机验证或平台访问限制；
- 连续自动操作前应先使用只读模式和少量报名验证；
- 使用者应自行确认其使用方式符合大众点评当前服务规则及账号使用要求；
- 本实例优先在无法确认状态时停止，避免进行支付、兑换或不确定的重复提交。

---

## 23. 快速命令速查

```cmd
:: 1. 查看 ADB 设备
D:\Android\platform-tools-latest-windows\platform-tools\adb.exe devices

:: 2. 运行代码单元测试
cd /d D:\Android\Mi9SE\dianping-auto
python -m unittest -v test_parser.py test_screen_guard.py

:: 3. 只读检查
D:\Android\Mi9SE\check-dianping.bat

:: 4. 最多报名 1 项，用于实机验证
D:\Android\Mi9SE\start-dianping.bat --limit 1 --max-scrolls 5

:: 5. 最多报名 10 项
D:\Android\Mi9SE\start-dianping.bat --limit 10

:: 6. 最多报名 10 项，并限制滚动 20 次
D:\Android\Mi9SE\start-dianping.bat --limit 10 --max-scrolls 20

:: 7. 默认配置运行：LIMIT=0 / MAX_SCROLLS=0
D:\Android\Mi9SE\start-dianping.bat
```

---

## 24. 当前版本总结

当前 `mi9se` 分支的定位是：

> **一套针对 Xiaomi Mi 9 SE 做过真实报名验证的 Windows + ADB + scrcpy UHID 大众点评免费抽自动化实例。**

它不仅包含自动报名脚本，还包含：

- ADB 设备检查；
- Mi 9 SE scrcpy 启动与守护；
- 页面只读检查；
- 候选活动解析测试；
- 点击区域和按钮颜色保护测试；
- 页面误导航恢复；
- 单项、小批量、连续报名模式；
- JSONL 运行日志；
- 验证码、支付、PASS、未知页面等停止保护。

对于第一次使用本分支的人，最重要的不是直接运行不限数量模式，而是先完成：

```text
单元测试 → 只读检查 → --limit 1 实机测试
```

确认当前手机、当前大众点评版本和当前账号页面仍与这套 Mi 9 SE 实例匹配后，再进行连续运行。
