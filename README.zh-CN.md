# low-token-process-wait

[English](README.md) | **简体中文**

让 Codex 在等待数分钟或数小时的有限程序时结束当前回答，之后继续原任务。

**本版优先预测剩余时间，无法预测时逐档退避。** Desktop 仅在宿主允许时使用同任务官方调度，CLI 保留本地进程退出唤醒。

## 安装

把 `skills/low-token-process-wait` 复制到 `${CODEX_HOME:-$HOME/.codex}/skills/`，然后新建 Codex 任务。可以显式使用 `$low-token-process-wait`。希望日常自动触发时，将 [AGENTS.integration.md](AGENTS.integration.md) 的规则加入用户或项目 AGENTS.md。

安装 skill 本身不会修改 shell、权限、提供商或登录信息。

## Desktop：定时返回原任务

长程序启动后记录进程身份、主机、日志及退出记录。每次探测优先估计整个程序的剩余时间：不超过30分钟就等待该时长，超过则等30分钟后重估；例如预计7分钟就等7分钟。无法可信预测时，依次等待 **30秒、1分钟、2分钟、5分钟、10分钟、30分钟**，之后每30分钟探测。

不超过30秒的等待在当前会话完成；更长等待仅在宿主允许时安排同任务 heartbeat。每次重估后核对并更新实际调度，保存等待状态；不能只改提示词却一直沿用旧的5分钟周期。

确认创建成功后结束回答。每次调度只检查一次，没有变化时保持安静。程序结束后核验结果、继续原工作，再暂停或删除这次等待的定时任务。不要另开一个独立任务代替原任务跟进。

需要电脑和 Desktop 持续运行。定时检查会调用模型，有检测延迟，不承诺零 token 或退出立即唤醒。[官方文档](https://learn.chatgpt.com/docs/automations)

Goal 有独立生命周期：不能假定定时输入会自动恢复 paused Goal；宿主未验证时不得承诺这一联动。

## CLI：程序退出后唤醒

要求 Linux、Python 3、tmux、默认英文 CLI 输入布局，以及访问宿主进程和面板的权限。详细入口、参数和限制见 [操作说明](skills/low-token-process-wait/references/operation.md)。

监督程序本地等待真实退出，然后向原 CLI 输入框输入完成消息并按 Enter。有授权时可临时暂停、恢复同一个 Goal。接管既有进程不会重跑；无法取得退出码时明确记为 unknown。

不使用非交互 Codex 命令、SDK、app-server 客户端或模型 HTTP 请求。不自动提升权限；沙箱隐藏宿主 PID 或禁止 tmux 时会拒绝注册。

## 已有证据

- CLI：20项监督程序测试及3项启动入口测试；65秒真实等待期间没有新增模型轮次，完成消息一次，原 Goal 保留；另有真实 agent 自行启动任务的完整测试。
- Desktop Linux：90秒后台程序跨轮次完成，2分钟 heartbeat 自动返回原任务、验证输出并停用定时任务。另有回调进入 paused Goal 的实测，但未验证恢复 active。见 [验证记录与5分钟演示步骤](skills/low-token-process-wait/references/desktop-validation.md)。
- 尚不支持监督程序/主机崩溃后自动恢复；不明确的投递不会盲目重试。草稿、任务或 Goal 变化、未识别布局可能阻止 CLI 投递。

测试（不调用模型）：

```bash
python3 -m unittest discover -s tests -v
```

[12分钟 Desktop 实验](prompts/12-minute-test.md)可验证你自己的安装环境是否支持定时继续。

## v0.3.0 更新

修复Goal日志事件缺失时的身份读取，改用只读持久身份核验。180秒真实CLI重测已通过，完成消息一次，同一Goal恢复并续跑完成。可选WezTerm/zsh入口增加鼠标、剪贴板、隐藏底栏、十万行历史和CLI内联显示；具体操作及未验证项见操作说明。

## v0.4.0 更新

补充 Desktop Linux 普通对话后台等待、定时返回原任务和自动收尾的实测；明确区分 CLI Goal 恢复能力；增加5分钟演示步骤，以及沙箱进程存活和 PID 命名空间注意事项。CLI 脚本保持不变。

## v0.6.0 更新

新增 ETA 优先策略、30分钟上限和含10分钟档的未知退避；保留宿主限制与 CLI 退出即唤醒。完整自适应调度时序尚未实测。
