# Contributing

感谢提交改进。请遵循以下约定：

1. 不在 Issue、PR、测试夹具或截图中提交真实账号、手机号、验证码、Token、Cookie、ADB 序列号或本机绝对路径。
2. 新的页面解析规则优先添加无需真机的单元测试。
3. 不提交绕过验证码、人机验证、频率限制、支付确认或平台风控的实现。
4. 对 scrcpy control protocol 的修改应注明已验证的 scrcpy 版本。
5. PR 前运行：

```bash
python -m unittest discover -s tests -v
```

代码应保持 fail-closed：无法确认页面或业务结果时停止，而不是猜测下一步。
