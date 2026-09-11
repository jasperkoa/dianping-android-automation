# Troubleshooting

## `adb` not found

确认 Android SDK Platform-Tools 已安装：

```powershell
adb version
```

否则通过：

```powershell
.\inspect.cmd --adb "C:\path\to\adb.exe"
```

或设置 `ADB_PATH`。

## `adb devices` 显示 `unauthorized`

解锁手机，重新连接 USB，并在手机上允许该电脑的 RSA 调试授权。

## 检测到多台设备

执行：

```powershell
adb devices
```

然后：

```powershell
.\inspect.cmd --serial DEVICE_SERIAL
```

不要把真实序列号提交到 Git；建议写入被忽略的 `config.local.cmd`。

## 能投屏但 ADB 点击被拒绝

错误可能包含 `INJECT_EVENTS` / `SecurityException`。优先使用：

```powershell
.\run.cmd --input uhid
```

部分 MIUI/HyperOS 设备还可以检查“USB 调试（安全设置）”。不要尝试绕过系统或平台验证机制。

## UHID 连接失败

先检查：

```powershell
scrcpy --version
```

如果自动发现失败，在 `config.local.cmd` 指定：

```bat
set "SCRCPY_SERVER_PATH=C:\path\to\scrcpy-server"
set "SCRCPY_SERVER_VERSION=4.1"
```

scrcpy 大版本升级后，control protocol 可能变化；建议先回到已验证版本确认。

## 返回键不工作

根据手机实际导航方式修改：

```text
adb
gesture-left
gesture-right
nav-left
nav-right
```

三键位置特殊时额外设置 `--back-x-ratio` / `--back-y-ratio`。

## 找不到活动

先执行：

```powershell
.\inspect.cmd
```

确保：

- 目标 App 在前台；
- 当前是免费试活动列表；
- 当前可操作行包含程序识别的“免费抽”或“免费抽奖”文案；
- App 页面没有改版为完全不可见于 Accessibility 的自绘/WebView 结构。

## 提交后停止

如果日志显示“提交后未确认报名成功”，程序故意不自动重试。请人工检查 App 当前结果，再决定后续操作。
