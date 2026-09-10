# 执行减负与防漏派（2026-09-07）

只调整执行方式。业务Skills、知识判断、两道人机确认、网站/会话门、全部编号输出和字段不减少；旧Run不静默迁移。

## 全图扫描与派发对账

主任务在输入预检、登录门、任何阶段终态验收、关键词正式回执/READY、确认/解阻、续接后以及进入等待前，调用`scripts/dispatch_plan.py`。不能只处理上一条消息的后继。

```text
python3 scripts/dispatch_plan.py --manifest <run-manifest.json> --board <dispatch-board.json> --mode <full_pipeline|downstream_intake>
```

`full_pipeline`总登录门后同轮派商品审计、五维洞察、痛点频率和关键词主任务；五维完成即派标签，不等关键词；关键词正式回执通过原核验并由Listing主任务发READY后即派SKU，不等Alexa其他支线。02/03与04/05的接收整理仍保留，但只核验/登记，不重写源表。08与09在07确认后按原条件并行；正文仍等待09计划，最终装配仍等待正文确认，不把有依赖任务强行并行。同一个实际浏览器会话不并发操作。

本机board字段（不进入工作簿或Git）：

- `schema=listing-dispatch-board/v1、run_id、jobs={node: {path,sha256}}`；path指向不可变实际派发/状态回执。空jobs只用于已核对实际任务为空闲的新Run，不用于恢复旧任务。
- 每份回执含`run_id、node、stage_key（扫描输出）、role、dispatch_id、task_id、host、state`；sent/accepted/running必须带实际发送工具`response.threadId`或tool_call_id。主任务先依据当前本机映射核对身份，不能用拟派名单自证已发送。
- state为reserved/不确定时先查证不重发；returned时先验收产物；awaiting_login/busy/needs_input必须附具体reason并冻结该节点，其他就绪节点继续。忙任务恢复时保留原派发记录并重新扫描。
- `keyword_ready={path,sha256,formal_receipt:{path,sha256}}`指向既有Listing主任务签发READY和关键词正式回执，继续原双Run/事实/哈希/人口/XLSX核验，扫描器不能自行颁发READY；READY的input_locks保存来源指针数组并含当前锁定主输入。
- `accepted_intakes={node:{path,sha256}}`指向接收整理回执，含run_id、role、output_sha256（原表路径→哈希），不能用布尔true伪造接收。
- `painpoint_phrasing_required`由主任务按确认07的既有适用条件记录boolean，false时按原状态命令登记08=skipped，不生成空08。`downstream_intake`的keyword_source_admitted仅记录关键词主任务已完成原采集/复用入口门，不豁免任何来源或登录检查。

扫描列全`dispatch/main_action/in_flight/blocked/accept_output/reconcile_dispatch/resolve_or_resume`。存在未处理即时动作时wait_allowed=false，退出码1；锁错误退出码2。把全部就绪节点实际派发并留回执后重新扫描，再用最新cursor同时等待在跑任务。某一任务阻断不隐藏其他分支；无法立即处理的错误先登记并通知，不能循环空扫或盲重发。该脚本是强制入口协议，不是对全部Codex工具的全局拦截器。

## 删除独立重复QA，保留原装配检查

新建Run锁定`quality_execution.final_checks=inline、independent_qa=not_requested、p1=false`。`final_qa`旧阶段键保留供状态兼容，但新Run仅表示装配自身检查回执，不另派独立审查、不额外等待另一轮审核。原写作任务继续负责正文、ST、14Sheet和原Gate 7全部硬规则及软性自检；不删除这个拥有任务或质量规则。

装配一次形成业务表、检查结果和唯一预览；主任务读取同一结果验收。装配完成后使用`pipeline_state.py finish-inline-checks --manifest <manifest> --receipt <receipt>`收口，不得set-stage强写通过。

receipt固定含`run_id、kind=assembly_self_check、input_sha256、copy_sha256、output_sha256、checker_sha256、rule_locks、independent_qa=not_executed、p1=false、gaps=[]、checks={ID:{status,evidence:[{path,sha256}]}}`。checker_sha256锁定pipeline_state.py字节；rule_locks含quality-gates.md及本次适用拥有规则的path/sha256，不用空列表代替。output_sha256必须覆盖当前已登记的全部最终文件；checks的ID由脚本INLINE_CHECK_IDS列出，对应质量合同Gate 7的十一项及原软性写作自检，每项附真实检查证据。状态pass表示该项按原门已闭合；后台未核验、软性可优化等合同允许状态仍在证据/gaps如实保留，不能宣称Amazon审核通过。这个命令只核验身份、覆盖和文件哈希，不代替检查本身，也不产生独立QA/P1。

历史QA取消保持原not_executed/cancelled_by_user和未完成状态。若用户另行要求正式独立回归或能力验证，单独明确范围和原质量合同，不把新inline回执提升为独立验证。

## 复用已有输出，减少重写

1. 表格名称、顺序、字段、公式图表按原input/output/展示合同固定；优先使用已有模板、状态/检查脚本与copy_preserved_sheets.py，不每Run重新设计Schema。未有通用builder的模块仍按原表格Skill执行，不声称已实现全模块模板化。
2. 对同Run、同输入/规则/检查器、同人口/检查范围、同输出和证据字节哈希的已通过结果，接收者直接引用原检查/唯一预览，重复通知不重做。任一版本、字节、布局或范围变化则重新执行受影响检查；原表搬到新目标的保真和新最终包检查不能省略。
3. 同一结构化记录派生原manifest/handoff/verification，保留原字段和证据，不由多个任务重复手抄；检查回执的接受不重写业务文件。
4. 只续跑失败或输入变化影响的节点及后代；首次必要检查、完整语义人口、身份/事实核验、人工确认和实时登录不使用缓存豁免。

合成测试只证明控制层行为；真实提速、业务输出等价与P1仍待新Run验证。
