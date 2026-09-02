# Task routing

本文件用于主任务向长期副任务发送某一轮执行或规则迭代任务。副任务身份长期保留，但每次收到的工作仍必须只有一个明确目标。

## Main task dispatch

- Goal:
- Run ID and locked repository revision:
- P1 case slot: case-01-normal | case-02-normal | case-03-edge-or-error | not-applicable
- Logical side-task role:
- Mode: read-only validation | approved iteration
- Scope and excluded work:
- Allowed actions: read-only | local draft | repository write | external write
- Risk: low | medium | high | uncertain
- Required sources:
- Acceptance criteria:
- Expected files:
- Required verification:
- Return destination: keyword-main

派发前必须用被Git忽略的`thread-map.local.md`和当前Codex任务列表完成机械身份门，并把本次核对结果只写入本地dispatch：`Logical role、固定任务标题、Task ID、host、execution cwd、Run ID、locked revision、output directory`必须同时匹配。实际Task ID、host和绝对路径不得进入任何tracked文件或最终交付。任一字段不符时停止派发，不得新建临时任务或由主任务代跑。

## Side-task return

- Status: complete | blocked | needs main-task decision | needs user approval
- Run ID and input revision:
- Mode actually executed:
- Branch and Worktree:
- Files changed:
- Sources and assumptions:
- Verification performed:
- Sensitive-data check:
- Durable knowledge candidate: none | describe
- Current-context update: none | describe
- Recommended next action:
- P1 evidence candidate: none | module case slot and acceptance summary

## Parallel dispatch rule

主任务按以下三组并行依赖调度：

1. 用户开头固定提供三组输入，且`产品基础信息配置`已包含目标Amazon类目及该类目是否存在多个稳定产品类型细分；字段齐全后不得在运行途中重复询问，用户不指定核心词。主任务另锁定run_type，未明确测试时默认production。原始直接竞品ASIN超过5个时，先按稳定竞品产品类型每类保留输入顺序中的第一个有效ASIN；类型不明或每类取一后仍超过5个时不派发SIF。SIF副任务装配七列明细与不执行语义晋级的候选摘要后回传；主任务依据产品事实卡、直接竞品身份和SIF候选独立确认唯一一级品类核心大词，并仅在用户确认类目有多个稳定产品类型细分时确认可选唯一细分核心词。存在细分核心词时，主任务必须先对省略一级品类/用途等上位限定词但保留决定性细分表达与完整商品头部的候选完成目标细分强等价闭环，再锁定主执行锚点、强等价/宽泛流量词、Amazon联想锚点和卖家精灵种子集合；同一机械键不得跨层级，缺少上位限定词不得作为宽泛依据，用户未逐项确认的层级不得写成用户确认。存在细分核心词时主执行锚点与Amazon联想锚点等于细分核心词，卖家精灵种子集合包含一级核心词与细分核心词；不存在时三者都只使用一级核心词。随后Amazon联想与卖家精灵扩词副任务并行。卖家精灵副任务逐种子只保留一个成功完整官方导出，在模块内机械去重并完成一个四列合并表再回传；三来源机械合并等待两者和SIF全部正式回传，并只生成两Sheet第一板块业务工作簿。
2. 清洗完成四Sheet工作簿、Sheet2/3/4唯一去向和Sheet2通用词库资格闭环后，资格纳入人口的词频统计与完整Sheet2/Sheet4关键词分类并行。词频不参与分类判断；最终工作簿装配等待词频分支和第三板块分支全部完成。
3. 关键词分类完成后，通用词库资格为`纳入`的适用人口进入竞争性分析与趋势性分析并行；最终工作簿装配等待两者及分类派生表全部回传。

并行任务各自记录输入版本、异常和完成状态；不得把一个分支完成推断成整组完成。每次派发都必须先通过上述固定任务身份门；每个模块必须由通过身份门的拥有副任务执行并正式回传当前Run相对路径、哈希、人口、状态、缺口和验证。主任务不得因副任务不可用、未初始化、操作不便或已能看到证据而代跑，也不得用通用临时子代理替代；只能在用户了解影响后明确批准的一次性Run例外下接收已经产生的证据，并将例外留痕且排除P1。来源副任务默认只回传工作簿、Run相对路径、哈希、数量、完成状态和异常摘要，逐页/逐调用长响应正文只留本机Run目录，避免重复占用主任务上下文。

来源入口按合同锁定：Amazon联想首选Codex内置浏览器并允许普通Chrome备用；SIF和卖家精灵副任务都在首次官网业务动作前验证登录，未登录时只回传主任务`awaiting_login`，由主任务提示用户并冻结分支，不能直接切MCP。只有用户明确无法在当前设备/会话完成SIF登录时才允许同提供商MCP备用；卖家精灵则只有已登录但官网完整导出链路仍不可用时才使用同提供商MCP。备用入口不得改变站点、查询、周期、过滤、字段或完整性门；只有稳定来源事件标识并能证明无遗漏/无重复时才可续采，否则重启受影响完整查询。趋势任务按`SellerSprite -> Sorftime`路由，且同一Run全部趋势人口只使用一个提供商。

## Read-only validation rule

第一次正式验证及后续获准的只读验证中，副任务只能读取锁定的 Skills、知识和流程。原始数据、过程表、工作簿、渲染、检查日志和候选问题只写入 `.local/runs/<Run_ID>/<logical-role>/`；不得修改跟踪文件、提交、推送、更新飞书或升级 Skill maturity。

每个派发必须标明本Run对应的P1案例槽位。一个端到端Run只能为实际执行到的Skill各产生一个独立模块候选；副任务回传候选状态和自身质量门，不直接修改`evidence/index.md`。Run结束并经用户确认后，另行使用获准迭代/发布批次写入脱敏案例文件和更新登记。历史Run、未执行模块、`blocked/partial/not_executed`正常模块不得占用正常案例槽位。

发现规则缺口时，回传真实证据、影响范围和建议方向。主任务向用户汇总并取得确认后，才另行下发 `approved iteration`。

## Quality-validation routing gate

最终装配产生过程文件夹和八Sheet最终工作簿后，按run_type分流。production不路由`keyword-quality-reviewer`；装配任务仍执行Gate 1–20机械全量检查和完整风险人口逐行语义复核，Gate 21写`not_applicable`，质量目录只含`independent-qa-not-applicable.json`，全部适用门闭合后可直接交付，但不得写QA pass或P1。只有test-validation才把锁定Run、revision、阶段清单、合同版本、`qa_mode`和本机产物路由给质量副任务；普通测试用`compact-validation`，Skill/知识/判断边界、字段/Sheet/Schema、公式/图表、封包/检查器变化、P1三案例或compact异常必须`full-regression`。两种测试模式都只读执行全部21项装配门、机械全量检查和完整风险人口逐行语义复核。质量副任务只返回`pass`、`blocked`或`incomplete`，不得修改上游、补造证据或调用业务外部系统。

## Persistent ownership rule

获准迭代时，副任务只修改 `docs/thread-roles.md` 分配给自己的 Skill、直接引用合同和模块知识。项目总决策、知识索引、端到端流程和跨模块冲突由主任务统一整合。

## Branch rule

只读副任务可以不创建分支。任何会写入仓库的并行副任务必须使用仓库根目录 `docs/github-branching.md` 规定的短期分支；同时写入时使用独立 Worktree。

## End-to-end documentation gate

预期修改本项目 `knowledge/` 或 `.agents/skills/` 的任务，必须把 `docs/end-to-end-workflow.md` 同时列入 Expected files 和验收标准。副任务回传时必须说明端到端文档更新了哪些章节；没有流程影响时，也要更新其同步说明并明确报告“已复核，无流程变化”。未完成该同步的任务状态不能标为 `complete`。
