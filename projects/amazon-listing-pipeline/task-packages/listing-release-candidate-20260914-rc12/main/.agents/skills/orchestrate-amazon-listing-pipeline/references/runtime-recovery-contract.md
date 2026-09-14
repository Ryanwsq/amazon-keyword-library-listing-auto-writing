# 当前任务恢复与本轮异常防护

版本：20260914。新Run锁定`runtime_repairs_version=20260914`及`login_gate_policy=per-stage-20260914`；已有Run不补字段、不升级包、不重写交付。它是执行控制补充，不替代原业务Skill、来源、阈值、双确认门或P1标准。

## 1. 输入后登录准备与并行

输入锁定后立即引导全部八个拥有任务的登录/鉴权准备；不减少矩阵。每个业务分支只等待自己的有效会话和实际数据依赖，不因无关SIF或卖家精灵登录阻断Alexa。总门只汇总八会话是否齐全。关键词主任务的输入交接/复用判断属于编排，可在其采集会话尚未齐全时下发；它不得据此跳过关键词项目中各采集拥有任务的独立会话和准入门。没有本任务证明仍不允许采集。

## 2. 一角色一活动目标与当前身份

本机dispatch board在原`listing-dispatch-board/v1`中增添`role_bindings`。每个角色对应一个数组，字段为`state=active|retired、task_id、host、business_cwd、package_manifest、package_manifest_sha256`。每个可派角色必须恰有一个active；相同标题无效，退役记录不作为回退目标。外部keyword-main的绑定由关键词拥有项目提供带role及版本的当前身份清单，不伪造为Listing业务角色包或READY。

缺少/重复活动目标、cwd消失或包变化时planner输出`bind_owner`且不允许直接等待；主任务核对真实任务元数据后解决绑定，不自动创建、重命名、归档任务或重建工作树。更换任务须明确授权，保留旧派发/取消两方证据及旧文件，再在新的目标重新加载和accept；不得改写旧lease为成功，也不能只因idle就取消旧任务。

每次START、压缩恢复、开始读取业务源或写输出前，执行`scripts/runtime_recovery.py`。参数：`--assignment <当前派发JSON> --run-id <明确Run> --role <明确角色> --task-id <实际任务ID> --host <实际host>`；本次业务读写文件分别以重复`--read/--write`给出。身份来自实际任务元数据，不能根据历史聊天或标题推测。

派发文件使用`schema=listing-runtime-assignment/v1`，包含：

- `run_id/role/task_id/host/dispatch_id/mode=PREP|START/asin/marketplace`；
- `run_manifest={path,sha256}`指向当前状态快照；状态合法更新后重新取实际哈希并由主任务派发，不给旧快照改时间；
- `business`与`rule_source`分别为`{cwd,git_root,revision}`；实际app cwd另记在派发证据。允许规则只读源和业务checkout不同，分别核对Git根/HEAD，不要求两个根强行相等；禁止业务恢复自行checkout、merge或push；
- `package_manifest={path,sha256}`及`package_version`；检查实际包角色及所有文件哈希；
- `read_locks=[{path,sha256}]`：明确文件列表，必须包含当前输入及全部用户事实补充；`write_files=[明确新版本文件路径]`。不接受模糊历史目录、glob或只写“上次文件”。本检查的manifest/package/Git等控制读取与业务源读取分开。

PREP只准备、回报，不产业务文件；START通过后继续执行同一任务直到实质检查点、正式回传或具体阻断，不能只回复ACK后当作完成。已有成功槽位不重采，过时产物不覆盖。样例里的类目、材料、尺寸、ASIN均不提供当前事实。

此脚本是显式调用的准入检查，**不是Codex全局工具拦截器或文件系统沙箱**。未调用脚本的任意工具访问不受它强制拦截；历史串任务风险只能称协议缓解，须下一轮实际调用验证，不能宣称彻底根除。

## 3. 已发送不等于仍在运行

原实际send回执继续保持哈希。新board的`observations[node]={path,sha256}`指向实际任务状态观察，内容为`run_id/task_id/host/dispatch_id/observed_at/status`，可附reason/cursor/检查点指针。`observed_at`须为带时区真实采样时间；120秒仅为运行态采样窗口，非业务数据新鲜度阈值。不得把旧观察重盖时间。

无观察、过期或未知状态→`inspect_activity`；已idle/completed/needs_input→`resolve_or_resume`，核对正式回执或最后检查点；returned→`accept_output`。只有新鲜running观察允许显示in_flight，仍不证明已执行多少业务或P1。不得直接把任务completed当作工作簿验收成功。

每次回传/状态变化后先验收产物，再扫完整就绪前沿；有accept_output、resolve_or_resume、bind_owner、reconcile_dispatch等未处理项时不许直接等待。用紧凑任务快照、cursor和本地检查点，不循环读全历史；空items或被截断的日志不是“没有执行”。模型容量/服务故障保留原检查点与真实错误，不能改写为0数据；只在原授权范围恢复，不自动换模型或重启源采集。

运行阶段补进度用`pipeline_state.py update-progress --manifest ... --stage ... --message ... --evidence <本Run已有文件>`；只存元数据，不改变状态、输出或人工门。业务表/证据写文件后返回路径、hash、行数、阶段及缺口，避免巨量stdout截断；confirm-copy输出紧凑回执，完整正文快照仍在manifest保存。

## 4. 正文与事实纠正

所有产品执行[Title/IH知识库](../../../../knowledge-base/listing-title-highlight-writing-rules.md)的前段与有效预算规则。新Run正文JSON增加`front_copy_review`，不增加工作簿Sheet/表头。title和item_highlights各记录`text_sha256、characters、remaining_budget、ordering_rationale、prefix_review、remaining_candidates_and_tradeoffs、buyer_understanding、source_refs=[{path,sha256,locator}]`，另有`bullet_count_rationale`。脚本核对文字/计数/当前来源及说明完整性，语义真实性仍由写作拥有任务自检，不能靠填字符串代替正确写法。

用户纠正产品事实时保留原输入，新增带用户原话/定位、旧值、新值、受影响字段和hash的`user_fact_supplements`。以当前确认纠正覆盖冲突旧值，不能把旧输入错误一概称为模型捏造。重新派SKU拥有任务评估06受影响词，继而重算07/09及正文/ST；不直接用写作过滤冒充重新终筛，不静默改01–05原始证据。原临时“无需再确认”只适用于已明确授权的Run/范围，不成为后续默认。

## 5. 正式回传与同版本质量合同

当前Run已授权的正常业务回传给原委托主任务不再额外索取一次“发送授权”。目标、Run、附件或范围有变化仍需按权限处理。交付至少包含正式工作簿、manifest、检查/缺口与正式回执；检查点不是交付。

装配拥有包内的quality-gates路径与主包不同，不因绝对路径不同重做检查。原精确路径仍有效；新跨包回执添加`quality_contract_binding={owner_manifest:{path,sha256},main_manifest:{path,sha256}}`，必须等于主任务事先登记的`assembly_owner_binding`，角色分别是listing-writing-qa/main、候选版本一致、源路径身份及实际字节哈希一致。全部输出、checker_sha256、规则锁和12项证据照常验证，不能凭同名文件或当前存在的脚本反推历史检查已执行。

检查证据在执行时记入实际工具/脚本版本或可用的运行时标识，不能事后补造。无法取得版本写unknown及范围限制；不将版本未知当P1成功。追加日志采用固定capture或prefix长度+hash，保留raw与规范化对应，禁止替换原始回答。

## 6. 原始数据问题的归属

完整固定Alexa问题由对应拥有Skill提供，发送前核对，不自行缩短；每题保存原回答与定位。联想输入、稳定后可见建议、非关键词项及未知项由关键词采集拥有者保留证据；不以建议数少或固定条数设新停止门，不以DOM未知类型推定不可见。来源导出实际行数和声明总数分开，不能臆造平台2000条上限。显示百分号不证明原值单位，未知单位不得猜；逻辑Sheet按workbook关系定位而非物理sheet2.xml。翻译错误交归翻译拥有模块，保留原词，不改变关键词判断口径。

以上来源问题在关键词原合同/脚本未完成相应改动及回归前，只是跨项目明确修复要求，不能宣称该项目已修好。详见本批维护追踪表。
