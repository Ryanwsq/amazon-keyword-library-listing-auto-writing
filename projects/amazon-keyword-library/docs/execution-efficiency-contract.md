# 执行减负与全量就绪派发

2026-09-07用户确认。仅拥有执行调度和独立QA调用策略；业务来源、语义逐行判断、全部风险人口、阈值、字段/Sheet、登录门、历史Run和P1标准不变。

## 独立QA不再自动追加

本节替代当前入口中“只要test-validation就自动派发独立QA”的表述；不是把测试改称production，也不删除质量Skill或独立回归能力。

| 新Run | quality_routing / qa_mode | 调度与交付 |
|---|---|---|
| production | not_applicable | 原装配Gate 1–20全部适用检查；Gate 21=not_applicable；不派独立QA，P1=false |
| 普通test-validation，未明确请求独立验证 | not_executed | 不派独立QA，不等待QA；装配检查后可输出测试表格，但Gate 21=not_executed、delivery_status=incomplete、P1=false |
| 明确请求独立QA、正式回归或P1案例 | compact-validation / full-regression | 原独立QA门、完整风险人口和封包生命周期不变；所有原full-regression触发条件继续有效 |

新测试spec省略qa_mode时固定为not_executed；显式compact/full即启用独立QA，主任务不得仅因普通测试或change_flags而自行启用。需要能力验证但用户取消时如实标未完成，不把取消改成不适用。已锁定历史合同保持旧路由，不静默重建。

普通测试的质量目录仅放`independent-qa-not-executed.json`，由装配输出`schema、run_type、qa_mode=not_executed、reason=independent_qa_not_requested、independent_qa_status=not_executed、delivery_status=incomplete、p1=false、gates`（21项）；历史用户取消保留原`cancelled_by_user`原因。不写QA pass，不调用仅支持compact/full的post-qa-package脚本。Gate 1–20仍全部执行，最终manifest列全文件、排除自身，当前包的哈希与隐私检查仍完成。recent-library-reuse同样显式锁qa_mode；不改历史source质量。

## 防漏派循环

每次输入锁完成、核心词锁定、拥有任务终态验收、登录恢复、人工解阻或主任务续接后，以及任何进入等待前：

1. 执行一次全图`scan-ready`，不能只检查刚结束任务的下一项。输入/规则/状态一次读取、一次校验，扫描全部分支。
2. 将所有`dispatch`逐个走原build → reserve → 实际send → sent；同波次不等兄弟任务完成。`main_action`由主任务执行自己原有职责，不代跑副任务。
3. `reserved/retry_authorized`不是已送达，必须查证；`returned/completed`事件不是已验收，先做原验收；忙任务、登录阻断和错误分别登记原因。某一路有问题仍处理其他已就绪分支。
4. 派发与验收后重新扫描。`wait_allowed=false`时不能宣称“全部已派发”并被动等待；可以等待正在运行的其他分支，但必须先报告并登记无法消除的人工/技术阻断，不能盲重发、循环空扫或清空ledger。
5. `wait_allowed=true`仅表示没有遗漏的即时动作，不是业务完成。按最新cursor一次等待所有在跑任务；状态无变化不重读全文，不重新生成已收取文件。

固定并行波次为`core-lock → 联想+卖家精灵`、`cleaning → 词频+分类`、`classification → 竞争+趋势`。装配汇合门不变。

```text
python3 scripts/dispatch_guard.py scan-ready --run <当前Run> --ledger <固定本机journal> --input <scan-request.json>
```

scan-request固定使用`contract_path、status_dir、preflight`，均为本机锁定文件。扫描只读、不调用任务API；真正发送仍归主任务。缺journal时先核验本机任务状态并初始化/恢复原ledger，不把缺文件当空闲证明。该命令用于fresh-collection；recent-library-reuse只有当前适用的assembly（明确独立验证时再接QA），继续原独立admission/build/reserve，不伪造fresh上游状态。复用开始与回传时同样核对当前唯一适用派发是否送达。

## 固定输出与减少重复工作

- 工作簿字段、Sheet顺序和公式图表继续由各拥有合同定义；生成前一次锁定Schema和上游哈希。优先复用所属Skill已有脚本/模板；不在每个Run另造另一套字段解释或反复重写装配代码。没有对应通用builder时按原合同执行并记录缺口，不能宣称所有模块已全自动模板化。
- 同一Run、stage key、输入/规则/检查器版本、输出字节哈希、检查范围/人口和证据哈希均未变且原检查通过时，接收者引用原完整检查及唯一渲染，不为重复通知再次生成。首次检查、原表移入新目标后的保真检查、最终输出/封包检查不省略；文件、规则、工具版本、范围任一变化或证据丢失即缓存失效。登录态、人工确认和新语义判断不能用文件缓存代替。
- 同一结构化模块结果用于生成原有manifest、handoff和verification视图；保留全部既定字段、状态与证据，不维护内容相同但手抄互相漂移的三份事实。过程manifest仍列全原合同要求的产物。
- 只重跑失败节点及受影响后代，已完成且锁一致的其他支线保留；恢复查询仍按来源完整性门，不以性能要求绕过单源趋势或完整导出。

## 验证边界

合成测试覆盖三组并行、仅发一侧、未送达占位、旧Run/旧锁、重复状态文件、失败隔离及QA显式路由；与原机械计算、来源、人口、字段回归一起运行。它们不构成真实浏览器运行、全量业务等价验证或实测提速。正式能力验证仍需新锁定full-regression，不提升draft/planned/P1。
