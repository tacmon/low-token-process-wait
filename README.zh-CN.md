# low-token-process-wait

[English](README.md) | **简体中文**

## 动机

这个项目试图解决 Codex 长任务的“最后一公里”。例如，`train.sh` 可能运行数小时，而主会话处在 goal 模式，用户又不希望中断任务。如果没有明确的等待流程，主会话可能反复探测进程状态，在很大的上下文中持续浪费 token。

本项目把精确进程监视交给一个经济型、干净上下文的 subagent，并让检测脚本只输出简短状态。这样可以让主会话获得一种实际可用的“前台等待”行为，同时降低监视成本。它不会改变 Codex 宿主的调度机制，也不保证无限时长的同步执行。

这是一个用于 Codex 的 skill，适合运行预计需要数分钟以上的有限任务，例如模型训练、多轮测试和数据集生成。它把精确 PID 的等待交给一个干净上下文的 subagent，避免大主会话反复探测进程并消耗 token。

这个 skill 不会改变 Codex 宿主的调度机制，也不承诺无限时长的同步阻塞。它会明确要求：

> 启动 subagent 后，主会话停止 thinking、停止探测并停止其他工作。等待 subagent 明确报告进程结束后，才能继续。

## 安装

```bash
cp -r skills/low-token-process-wait ~/.codex/skills/
```

之后可以显式使用 `$low-token-process-wait`，也可以让 Codex 在有限长任务中自动选择它。

检测器只监视一个精确 PID：

```bash
python3 ~/.codex/skills/low-token-process-wait/scripts/wait_pid.py \
  --pid 12345 --interval 60
```

进程存活时每分钟输出 `执行中`，进程退出后输出 `执行完毕`。检测器不会终止目标进程。如果绑定监视时 PID 已经不存在，会报告 `ALREADY_ABSENT`，不会将其视为成功。

## 测试项目

参见 [prompts/12-minute-test.md](prompts/12-minute-test.md)，其中提供了一个低资源、无 GPU 的 12 阶段测试提示词。参考实现位于 [examples/long-pipeline](examples/long-pipeline)。

测试应分别报告流水线是否成功、subagent 是否正确返回、主会话是否保持待机、等待窗口续接情况、被拒绝的错误工具调用以及 token 用量。平台未提供实际用量时，不要估算 token 节省比例。
