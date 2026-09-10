# 工作流编排：上游需求、开发分支与实施建议

调研日期：2026-09-07

本地基线：`qaihub_multica` / `77dc2e27d`（此前已合入 v0.4.37）

参考实现：GitLab `langgraph` / `06cdf2baf0fa91016cf6c5e6fa530b0158ac8c7f`

文档性质：需求与架构决策建议，不是实施承诺或上游发布计划。

后续深入分析：[#7990 合入后的工作流集成设计](workflow-lifecycle-integration-design.zh.md)，补充转换事务、策略快照、执行状态同步和分阶段集成方案。下文保留初次调研范围；后端源码层面的补充与限制以配套设计为准。

## 1. 结论摘要

**上游确实有相关方向的实际开发，但不能说“完整 Workflow 引擎即将发布”。**

1. [#1943](https://github.com/multica-ai/multica/issues/1943) 仍为 Open。维护者明确表示固定工作流仍在路线图中，可能作为小队的另一种执行模式；没有公开交付日期。
2. 当前最值得跟踪的是维护者 @forrestchang 的 [PR #7990：Project-scoped Issue Lifecycle](https://github.com/multica-ai/multica/pull/7990)。它来自上游仓库自己的 `agent/emacs/042965a42844` 分支，仍为 Open，已经有生命周期、状态进入自动化和声明式配置的实际变更。
3. **#7990 明确排除通用 DAG / 无代码 Workflow Engine**，因此它是重要基础设施及部分业务能力，不是 #1943 的完整交付。
4. 更直接的 [PR #8012：ordered workflow engine v1](https://github.com/multica-ai/multica/pull/8012) 来自社区 fork，已因作者删除来源仓库而关闭，未合并，不能作为近期可依赖的上游版本。
5. 历史工作流 PR #1170、#1945 也已关闭，不能把“曾经有代码”理解为“正在维护的官方特性分支”。

**建议：上游优先、差异化补齐。先对齐 #7990 的生命周期与执行契约，立即整理验收场景和扩展 RFC；暂不在当前基线上大规模建设第二套状态体系，也不直接迁移 GitLab LangGraph 分支。**

## 2. 证据范围和限制

- 已读取 #1943 正文、评论及 Development 元数据，并核对相关需求与 PR 页面。
- 已检索 PR 的 `workflow`、`orchestration`、`"workflow engine"` 和 Open PR 的 `langgraph` 关键词；检索结果中的一般 CI workflow、提示词 workflow 不作为引擎证据。
- 已查看 #7990 的变更文件页及其中 API 类型、前端和 E2E 测试片段；未对其全部后端实现做完整审计，也未在本地执行该分支。
- 已核对本地小队文档、任务执行服务、触发服务和子任务完成路径。
- GitHub REST 网页请求遇到 403，终端直连 GitHub 的远程分支枚举超时；公开分支页未返回可用分支行。因此，**没有完成所有远程分支的穷举**。本文的分支身份与存续结论以具体 PR 的来源信息和活动记录为依据。
- 本地缓存的 `origin/main` 指向 `387f76d32` / v0.2.13，明显陈旧，不能当成 2026-09-07 的上游 main。
- 本文不声称完整核验了最新 main 的全部功能，也不排除未公开、未关联 PR 或关键词未命中的工作。
- PR 作者列出的测试通过情况属于作者报告，不是本次独立验证；本文不作 CI 就绪或可合并判断。

## 3. #1943 的原始需求

### 3.1 核心问题

多智能体协作依赖提示词、协调者 skill 和人工约定时，执行顺序、条件分支、审批、失败重试缺少服务端强制保障。借助外部工作流系统可以补齐，但增加部署和调试成本。

原始目标是：**在 Multica 内部提供可配置、可视化、可审计、由服务端强制推进的工作流，而不是让模型自行记住流程。**

### 3.2 需求追踪表

| 编号 | 原始需求 | 应如何理解与验收 |
| --- | --- | --- |
| R1 | 内置 Workflow section / builder | 用户能定义并查看节点和连线；编辑定义与查看运行是不同能力 |
| R2 | Agent、skill、CLI、Webhook、人工审批节点 | 既包括模型推理，也包括无需模型的确定性执行；skill 本身不等同于一种执行器 |
| R3 | 条件网关与强状态机 | 非法跳转在 API/服务端被拒绝，不能只靠 UI 或提示词 |
| R4 | 多角色协作 | 阶段职责明确，结果及交付物能传给下一阶段 |
| R5 | retry、fallback、timeout、人工接管 | 必须区分执行重试、业务返工、人工接管和取消 |
| R6 | 可视化追踪 | 显示当前节点、执行者、阻塞原因和历史；不能只展示静态图 |
| R7 | 任务、项目、模板、工作区绑定 | 需要定义继承和版本规则，不应只支持一种小队绑定方式 |
| R8 | 创建、状态、评论、输出、CI 等事件 | 明确哪些事件启动、哪些恢复；需要鉴权、关联标识和去重 |

### 3.3 评论中的关键信号

- @Bohan-J（5 月 14 日，Collaborator）：已交付小队，但没有交付严格的预定义工作流；固定工作流仍在路线图中，可能建立在小队之上。
- @forrestchang（5 月 7 日，Collaborator）：曾表示当周实施。结合后续范围澄清，不能把这句话继续解释为完整引擎的交付日期。
- @egouilliard-leyton：建议集成 Archon YAML 工作流。这是社区技术建议，**不是官方引擎选型**。
- @HenryQW：报告特定环境中小队 token 消耗较高；@Bohan-J 回复正在优化。评论中的约 6 倍是单个用户的观察，不作为通用性能指标。
- @taogejiang：强调批量任务中固定流程的稳定性和依赖可见性。
- @Cheng-777：强调并非每一步都需要 LLM，确定性步骤应降低 token 开销。

原评论附图（仅保留来源，不作为性能测量证据）：

<img width="298" height="666" alt="Image" src="https://github.com/user-attachments/assets/be794e17-a277-4db4-b46b-c2b3a2c79f5a" />

### 3.4 相比此前 LangGraph 需求分析的修正

- 不能将需求缩减成“多个 Agent 按图运行”：原始需求包含非 LLM 执行和外部事件。
- 单个父任务内协作是参考分支的设计，不是 #1943 要求禁止子任务的依据。
- 同模板多编队、角色快照、AI 草案发布等来自参考实现与可靠性设计，应标成扩展需求，而非声称全部出自 #1943。
- LangGraph、YAML、独立 Python 服务和 SQLite checkpoint 都不是原始需求的必选项。

## 4. 上游分支与 PR 调查

| PR / 标题 | 来源 | 调研时状态 | 与工作流的关系 |
| --- | --- | --- | --- |
| [#7990：项目级任务生命周期](https://github.com/multica-ai/multica/pull/7990) | 上游仓库 `agent/emacs/042965a42844`；@forrestchang | Open，仍在实施 | 最重要的官方相邻能力：Lifecycle、Transition、Entry Automation、Lifecycle-as-Code |
| [#8012：有序工作流引擎 V1](https://github.com/multica-ai/multica/pull/8012) | `oaslananka:feat/workflow-engine-v1` | Closed、未合并；活动记录显示删除来源仓库导致关闭 | 直接的社区实现，限制为有序阶段；不是当前活跃上游分支 |
| [#1945：agent_workflow RFC](https://github.com/multica-ai/multica/pull/1945) | `talspin:proposal/agent-workflow-engine` | Closed；记录显示来源分支已删除 | 单 Agent 顺序步骤、人工门控；团队路径为占位，幂等与版本冻结尚有缺口 |
| [#1170：工作流、人工评审及调度](https://github.com/multica-ai/multica/pull/1170) | `natsukuu:feat/workflow-engine-and-ui-improvements` | Closed、未合并 | 历史完整方向尝试；维护者因长期冲突关闭，允许基于新 main 重新提案 |

**应严格区分四件事：官方路线图、官方活跃实现、社区尝试、已经发布。它们不互相等价。**

### 4.1 #1943 目前是否直接关联开发分支

页面显示：无 assignee、无 milestone、无 project，Development 为 “No branches or pull requests”。

这说明没有在该需求上直接登记的开发分支，不说明整个仓库没有相关工作。#7990 就是需要通过跨需求检索发现的相邻实现。

### 4.2 #7990 的实际范围

PR 描述和可见代码体现以下概念：

- `Lifecycle`：工作区默认或项目自定义的生命周期定义。
- `Status Node`：稳定节点 ID，显示名称可以变更，避免以状态名称作为身份。
- `Phase / Outcome`：跨项目汇总和兼容投影使用的语义。
- `Issue Transition`：不可变转换记录，配合 revision / transition ID 防止陈旧写入。
- `Entry Policy`：进入节点后如何分配负责人、启动 Agent 或小队、传入指令，以及由谁确认后续转换。
- `Automation Execution`：每次进入节点的执行记录，记录策略快照并关联实际 task。
- `Lifecycle-as-Code`：YAML/JSON 的 dry-run、apply、版本冲突检测；V1 不是持续同步仓库文件。

可见 E2E 用例覆盖：进入 Agent 节点入队、进入 Squad 节点派发队长、人工接管取消执行、人工节点不自动派发、重入产生新执行、同节点重复请求不产生新记录。

但 PR 仍列出未完成项：剩余状态修改入口统一、跨端切换、策略消费者迁移、自动链熔断、在途兼容与回滚验证等。作者明确不希望按未完成的局部能力合并。

明确不在范围内：

- 通用 DAG / 无代码工作流引擎。
- 新的顶层 Approval、Decision、Result 等实体。
- 自动父任务状态汇总。
- V1 的单项目多生命周期或逐任务生命周期覆盖。

**关键区别：允许执行者显式切换状态，不等于已经根据结构化结果严格选择唯一合法后继。节点排序也不等于执行依赖图。**

### 4.3 #8012 的借鉴价值与限制

有价值的思路包括：不可变定义快照、单任务一个活跃运行、持久化转换历史、有序阶段准入、批量更新的原子性和子任务完成后的对账。

它把每个阶段映射到子任务，和 GitLab 参考实现的“父任务内派发节点 task”不是同一产品模型。不要混合移植两者的数据模型。

范围不含任意分支、循环、人工审批门控，也没有完整可视化 Builder。关闭原因是来源仓库被删除，不能解读为维护者否定此架构，也不能解读为已经接管开发。

### 4.4 相关后续需求

- [#5972：服务端强制步骤流转](https://github.com/multica-ai/multica/issues/5972)：Open，进一步说明长上下文下提示词流程会跳步，提出顺序步骤、guardrails 或状态列等方向；#8012 是其社区尝试。
- [#6202：非 LLM Command Agent](https://github.com/multica-ai/multica/issues/6202)：Open，提出直接在现有 runtime 执行获准命令、结构化结果、零模型 token，以及显式 AI fallback。它是执行原语，不依赖先建 DAG 引擎。
- Open PR 的 `langgraph` 关键词查询未返回结果。只能说明该查询未命中，不能证明没有私有或未公开的 LangGraph 工作。

## 5. 当前基线的可复用能力

| 当前能力 | 代码或文档依据 | 设计含义 |
| --- | --- | --- |
| 小队先派发队长，再通过协作继续 | [小队文档](../apps/docs/content/docs/squads.mdx) | 已有自主协调；角色描述主要是上下文，不是固定流程契约 |
| 自动化派发 | [server/internal/service/autopilot.go](../server/internal/service/autopilot.go) | 保留触发职责，不把完整工作流硬塞入 Autopilot |
| Agent 执行及队长派发 | [server/internal/service/task.go](../server/internal/service/task.go) | 复用执行、并发和取消能力；新增节点关联时需要显式契约 |
| 任务变更触发 | [server/internal/service/issue_trigger.go](../server/internal/service/issue_trigger.go) | 与未来 Lifecycle Entry Automation 高度重叠，是优先对齐边界 |
| 子任务完成后的协调 | [server/internal/handler/issue_child_done.go](../server/internal/handler/issue_child_done.go) | 已有阶段/子任务协作基础，但不等于通用可配置编排器 |
| 前端共享与服务端状态规范 | [CLAUDE.md](../CLAUDE.md) | Web/Desktop 共用业务层，运行状态由 API/Query 管理 |

本地相关目录的符号检索未找到上述新 Lifecycle 标识及工作流定义表；`workflow_run` 的部分命中是 GitHub Actions Webhook 事件，不是 Multica 内置引擎。

## 6. 推荐方案：先对齐生命周期，再补严格编排

### 6.1 对此前方案的调整

此前建议直接在 Go 服务内增加独立持久化工作流领域。这个方向并非不可行，但在发现 #7990 后，应降低直接实施的优先级：

> 不先固定第二套 Lifecycle / Transition / Execution 模型；先验证上游模型可复用范围，再对缺口建立工作流扩展。

这不是“等上游做完一切”，也不是“把 #7990 当成完整工作流”。现在就可以做需求契约、测试场景、模板语义和独立原型。

### 6.2 建议的职责边界

| 层次 | 建议职责 |
| --- | --- |
| Autopilot / 事件入口 | 触发业务流程；验证事件来源、去重和关联 |
| Lifecycle / Transition | 任务业务状态的唯一转换入口、授权及并发保护 |
| Workflow 扩展 | 允许的边、完成契约、结构化结果、等待与有限返工；按需增加实例与节点状态 |
| Agent / Squad / Command 执行器 | 负责具体工作，不拥有任意跳转权限 |
| 现有 task / Daemon | 运行、取消、超时、执行日志；不新建第二套调度队列 |
| 任务界面 / Builder | 配置、发布和观测；不能成为正确性保证的唯一位置 |

未来若有 DAG，内部节点状态与任务业务状态可以不同，但要明确映射：不是每个内部节点都应变成一个看板状态。并行节点不能强行压进单个 `lifecycle_status_id`。

### 6.3 需要补齐或验证的差异

| 能力 | #7990 的依据 | 建议 |
| --- | --- | --- |
| 项目/工作区定义、节点身份、转换审计 | 已有实际变更 | 优先复用，避免平行建模 |
| 进入节点后派发 Agent/Squad | 已有实际变更 | 只保留一个派发责任方，防止工作流与 Entry Policy 双重派发 |
| 人工接管、人工确认模式 | 已有实际变更 | 验证能否满足审批审计；不将手动改状态自动等同于正式审批 |
| 条件边和结果校验 | 未证明覆盖通用需求 | 增加明确枚举、证据 schema 和合法后继校验 |
| 完整运行的定义冻结 | 有生命周期绑定、版本和执行策略快照 | 进一步验证后续节点策略修改对在途流程的影响，不能假设整图已冻结 |
| 角色编队及版本冻结 | 小队/执行者不等于模板角色绑定 | 仅在同模板多编队场景确需时增加 |
| CLI/HTTP/CI 确定性节点 | #7990 所示执行类型不覆盖 | 单独设计命令执行契约，参考 #6202，不启动 LLM 代跑确定性脚本 |
| 并行、子流程、复杂循环 | 通用 DAG 明确不在范围 | 后续用真实场景评估 LangGraph 等引擎 |

### 6.4 引擎选择

- 简单项目状态流转：优先评估上游 Lifecycle + Entry Automation，不额外引入引擎。
- 有限分支、返工和人工决策：先验证在上游转换服务旁增加受限编排契约的可行性。
- 动态图、复杂并行、嵌套流程：再做 LangGraph 与其他成熟引擎的选型验证，避免逐渐自研通用引擎。

采用外部引擎时，Multica 继续负责身份、权限、业务状态和执行派发；外部引擎负责图状态及 checkpoint。必须定义权威状态边界、幂等消息、恢复和对账机制。

### 6.5 必须先明确的正确性与安全约束

1. 人工操作、Agent 结果、CI 回调、批量编辑和普通评论都不得绕过受控转换入口。
2. 结果关联实际执行和尝试编号；返工再次进入同一节点不能接受上次迟到的结果。
3. 重复回调、服务重启、取消竞态不得造成重复推进；事务内记录待派发意图，恢复时可对账。
4. 普通评论默认是上下文；评论触发需显式规则，不能用自然语言猜测审批结果。
5. 命令执行使用获准入口、版本/摘要校验、受限 runtime、结构化输入和超时；不得拼接不可信输入为 shell 命令。
6. HTTP/Webhook 节点应限制目标地址、防止 SSRF、引用而非导出凭据，并验证回调身份与重放。
7. 关闭功能开关只能禁止新启动，不能让在途运行失去控制或静默退化为普通小队派发。

## 7. 推进建议与决策门槛

### A. 现在：需求对齐与 RFC

- 在本地维护 R1–R8 与验收案例，不立即提交完整引擎实现。
- 向上游确认 #7990 与 #1943 的关系、后续固定流程形态及是否接受扩展贡献。
- 核对三个关键扩展点：转换准入、执行完成结果、可恢复的事件消费。
- 确认工作流节点与任务状态、阶段子任务之间的关系，避免照搬任一参考分支。

建议向维护者提出的问题：

1. 固定工作流仍计划作为 Squad mode，还是主要基于 Project Lifecycle？
2. #7990 后是否计划 allowed transitions、结构化 completion contract 和人工决策记录？
3. 工作流完成能否通过统一 Transition 服务提交，不额外派发 task？
4. 如何支持在途流程的整份定义冻结？
5. #6202 的确定性执行原语是否有负责人或可贡献的最小范围？

本文未代用户发布评论、Issue 或 PR。

### B. 上游实现可评估时：独立环境验证

- 固定 #7990 的具体提交，使用独立数据库、独立测试数据验证，不连接生产数据库。
- 按实际合并/发布状态安排基线升级，不因 PR Open 或作者测试通过就部署生产。
- 验证安装版 Web/Desktop、现有自动化、普通小队、Webhook、子任务和本地 SDK 的兼容性。
- 以“关键入口切换完成、稳定 API、故障恢复通过”为门槛，而不是只看能否演示正常流程。

### C. 业务不能等待时：可丢弃的最小原型

- 在独立特性分支和测试环境实现受限串行流程、条件结果与人工确认。
- 通过窄的状态转换适配层与现有服务对接；不要把最终上游字段名和未稳定 API 写死在多处。
- 只做一个主场景，暂缓通用画布、多层 DAG、全量导入导出和独立租户系统。
- 接受原型将被替换的成本；不承诺无损迁移上游未发布的状态模型。

### D. 最小验收集

| 场景 | 验收标准 |
| --- | --- |
| 规划→实现→评审→人工确认 | 未满足结果契约不能进入下一阶段 |
| 评审退回实现 | 生成新的节点执行，保留历史，不误用上次结果 |
| 重复完成回调 | 只推进一次，只有一次后继派发 |
| 运行中修改定义 | 已运行实例遵循明确冻结规则，新实例使用新定义 |
| 人工接管后旧 Agent 回写 | 陈旧转换被拒绝，审计可查 |
| 重启/超时/取消 | 可以恢复或确定结束，没有孤儿执行 |
| CLI/CI 确定性检查 | 无 LLM 也能执行；结果能决定分支，模型用量为零 |
| 普通任务回归 | 原有评论、提及、自动化及小队行为不受影响 |
| 越权和重放 | 跨工作区、无权限审批和过期回调被拒绝 |

### E. 跟踪周期

建议每周复查 #7990、#1943、#5972、#6202，或在新版本发布时复查。两次复查仍无明确进展且业务阻塞时，重新决定是否扩大本地原型；这只是本地决策节奏，不是上游交付估算。

## 8. 最终建议

**不建议现在直接迁移 LangGraph 分支，也不建议立即投入一套完整、自有的工作流状态体系。**

最佳路径是：跟踪并参与上游生命周期基础设施，保留当前执行体系；以结构化结果、严格转换、人工决策及非 LLM 执行为差异化能力，先做契约和验收，再决定最小实现。

若要一句话回答“原始仓库有没有分支在做”：**有，#7990 是上游正在开发的相关基础能力分支；但当前公开证据不足以确认有一个活跃、官方负责且承诺交付完整 #1943 的通用工作流引擎分支。**

## 9. 主要来源

- [原始需求 #1943 与维护者讨论](https://github.com/multica-ai/multica/issues/1943)
- [上游 PR #7990](https://github.com/multica-ai/multica/pull/7990)、[变更文件](https://github.com/multica-ai/multica/pull/7990/files)、[来源分支](https://github.com/multica-ai/multica/tree/agent/emacs/042965a42844)
- [社区 PR #8012 及关闭记录](https://github.com/multica-ai/multica/pull/8012)
- [历史 PR #1945](https://github.com/multica-ai/multica/pull/1945)、[历史 PR #1170](https://github.com/multica-ai/multica/pull/1170)
- [强制步骤需求 #5972](https://github.com/multica-ai/multica/issues/5972)、[确定性执行需求 #6202](https://github.com/multica-ai/multica/issues/6202)
- [PR 检索：orchestration](https://github.com/multica-ai/multica/pulls?q=is%3Apr+orchestration+sort%3Aupdated-desc)
- [PR 检索：workflow engine](https://github.com/multica-ai/multica/pulls?q=is%3Apr+%22workflow+engine%22+sort%3Aupdated-desc)
- [Open PR 检索：langgraph](https://github.com/multica-ai/multica/pulls?q=is%3Apr+is%3Aopen+langgraph+sort%3Aupdated-desc)
- [GitLab 参考实现的工作流协议](https://gitlab2.quectel.com/larson.li/multica_langgraph/-/blob/06cdf2baf0fa91016cf6c5e6fa530b0158ac8c7f/docs/langgraph/workflow-authoring-protocol.md)

所有在线状态均为调研时快照，重新立项或实施前应复查。