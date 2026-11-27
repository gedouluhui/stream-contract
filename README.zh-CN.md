# StreamContract 中文快速开始

[English](README.md)

## 快速开始与支持状态

### 问题
通过显式 SSE 期望值和可重放的失败切分，测试流式客户端是否错误依赖网络分块边界。

### 安装
```sh
python -m pip install .
```

### 成功命令
```sh
python -m streamcontract demo --json demo-report.json
```
预期：正确收集器通过，故意损坏的解码器被拒绝；退出码 0。

### 故意失败命令
```sh
python -m streamcontract check missing.sse --json check-report.json
```
预期：缺失输入被拒绝，退出码 2，且不声称成功。

### 证据与覆盖边界
证据覆盖已知 SSE 用例的每个单一切分、逐字节 Unicode、不完整结尾、错误类型、预算、多 choice、重放、CLI 退出码，以及可选的固定版本 SDK 对比。通过只覆盖提供的 fixture 和被测试切分，不覆盖指数级所有切分或真实传输行为。

### 支持状态
版本 0.1.2 支持 Python 3.10+，无运行时依赖。本地执行验证环境为 Python 3.12.3。文档路径是源码检出；本 README 不声称已发布到 PyPI。维护为尽力而为，不提供 SLA。

### 限制
审计默认最多 65,536 字节输入和 512 个用例。不建模计时、背压、重连、套接字取消、工具调用、拒绝、命名事件或 Responses API 流。适配器是受信任的可执行代码。
