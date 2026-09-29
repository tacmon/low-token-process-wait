# low-token-process-wait

[English](README.md) | **简体中文**

让 Codex 在等待数分钟或数小时的有限程序时结束当前回答，之后继续原任务。

**本版首选 Desktop 官方定时任务。**CLI 保留本地进程退出唤醒；取代旧版的子 agent 监视方案。

## 安装

把 `skills/low-token-process-wait` 复制到 `${CODEX_HOME:-$HOME/.codex}/skills/`，然后新建 Codex 任务。可以显式使用 `$low-token-process-wait`。希望日常自动触发时，将 [AGENTS.integration.md](AGENTS.integration.md) 的规则加入用户或项目 AGENTS.md。

安装 skill 本身不会修改 shell、权限、提供商或登录信息。

## Desktop：定时返回原任务

长程序启动并确认能持续后台运行后，记录进程身份、主机、日志及退出记录，创建绑定当前任务的官方 heartbeat：长任务通常每30分钟检查，较短任务每5–10分钟检查。

确认创建成功后结束回答。每次调度只检查一次，没有变化时保持安静。程序结束后核验结果、继续原工作，再暂停或删除这次等待的定时任务。不要另开一个独立任务代替原任务跟进。

需要电脑和 Desktop 持续运行。定时检查会调用模型，有检测延迟，不承诺零 token 或退出立即唤醒。[官方文档](https://learn.chatgpt.com/docs/automations)

Goal 有独立生命周期：不能假定定时输入会自动恢复 paused Goal；宿主未验证时不得承诺这一联动。

## CLI：程序退出后唤醒

要求 Linux、Python 3、tmux、默认英文 CLI 输入布局，以及访问宿主进程和面板的权限。详细入口、参数和限制见 [操作说明](skills/low-token-process-wait/references/operation.md)。

监督程序本地等待真实退出，然后向原 CLI 输入框输入完成消息并按 Enter。有授权时可临时暂停、恢复同一个 Goal。接管既有进程不会重跑；无法取得退出码时明确记为 unknown。

不使用非交互 Codex 命令、SDK、app-server 客户端或模型 HTTP 请求。不自动提升权限；沙箱隐藏宿主 PID 或禁止 tmux 时会拒绝注册。

## 已有证据

- CLI：15项自动化测试；65秒真实等待期间没有新增模型轮次，完成消息一次，原 Goal 保留；另有真实 agent 自行启动任务的完整测试。
- Desktop：用户在真实工作中报告成功触发，界面显示绑定原任务的30分钟定时跟进。该证据仅确认创建，尚未确认完整自动收尾及 Desktop Goal 联动。
- 尚不支持监督程序/主机崩溃后自动恢复；不明确的投递不会盲目重试。草稿、任务或 Goal 变化、未识别布局可能阻止 CLI 投递。

测试（不调用模型）：

```bash
python3 -m unittest discover -s tests -v
```

[12分钟 Desktop 实验](prompts/12-minute-test.md)可验证你自己的安装环境是否支持定时继续。
