# Task routing

本文件用于主任务向长期副任务发送某一轮执行或规则迭代任务。副任务身份长期保留，但每次收到的工作仍必须只有一个明确目标。

## Main task dispatch

- Goal:
- Run ID and locked repository revision:
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

## Parallel dispatch rule

主任务按以下三组并行依赖调度：

1. 用户先确认目标Amazon类目及该类目是否存在多个稳定产品类型细分；用户不指定核心词。SIF副任务装配七列明细与不执行语义晋级的候选摘要后回传；主任务依据产品事实卡、直接竞品身份和SIF候选独立确认唯一一级品类核心大词，并仅在用户确认类目有多个稳定产品类型细分时确认可选唯一细分核心词，再锁定主执行锚点、强等价/宽泛流量词、Amazon联想锚点和卖家精灵种子集合。存在细分核心词时主执行锚点与Amazon联想锚点等于细分核心词，卖家精灵种子集合包含一级核心词与细分核心词；不存在时三者都只使用一级核心词。随后Amazon联想与卖家精灵扩词副任务并行。卖家精灵副任务逐种子保留原始官方导出，在模块内机械去重并完成一个四列合并表再回传；三来源机械合并等待两者和SIF全部正式回传，并只生成两Sheet第一板块业务工作簿。
2. 清洗完成四Sheet工作簿、Sheet2/3/4唯一去向和Sheet2通用词库资格闭环后，资格纳入人口的词频统计与完整Sheet2/Sheet4关键词分类并行。词频不参与分类判断；最终工作簿装配等待词频分支和第三板块分支全部完成。
3. 关键词分类完成后，通用词库资格为`纳入`的适用人口进入竞争性分析与趋势性分析并行；最终工作簿装配等待两者及分类派生表全部回传。

并行任务各自记录输入版本、异常和完成状态；不得把一个分支完成推断成整组完成。每次派发都必须先通过上述固定任务身份门；每个模块必须由通过身份门的拥有副任务执行并正式回传当前Run相对路径、哈希、人口、状态、缺口和验证。主任务不得因副任务不可用、未初始化、操作不便或已能看到证据而代跑，也不得用通用临时子代理替代；只能在用户了解影响后明确批准的一次性Run例外下接收已经产生的证据，并将例外留痕且排除P1。来源副任务默认只回传工作簿、Run相对路径、哈希、数量、完成状态和异常摘要，逐页/逐调用长响应正文只留本机Run目录，避免重复占用主任务上下文。

来源入口按合同锁定：Amazon联想首选Codex内置浏览器并允许普通Chrome备用；SIF首选MCP并允许同提供商已登录网页备用；卖家精灵关键词挖掘首选其拥有副任务内置浏览器中的已登录官网和完整官方导出，官网不可用时才使用同提供商MCP。备用入口不得改变站点、查询、周期、过滤、字段或完整性门；只有稳定来源事件标识并能证明无遗漏/无重复时才可续采，否则重启受影响完整查询。趋势任务按`SellerSprite -> Sorftime`路由，且同一Run全部趋势人口只使用一个提供商。

## Read-only validation rule

第一次正式验证及后续获准的只读验证中，副任务只能读取锁定的 Skills、知识和流程。原始数据、过程表、工作簿、渲染、检查日志和候选问题只写入 `.local/runs/<Run_ID>/<logical-role>/`；不得修改跟踪文件、提交、推送、更新飞书或升级 Skill maturity。

发现规则缺口时，回传真实证据、影响范围和建议方向。主任务向用户汇总并取得确认后，才另行下发 `approved iteration`。

## Independent quality-validation gate

最终装配产生过程文件夹和八Sheet最终工作簿后，主任务必须把锁定的Run、仓库revision、阶段清单、合同版本和本机产物路由给`keyword-quality-reviewer`。质量副任务只读执行21项装配门，特别核对最终`二类词`Sheet与分类Sheet4的人口、十六列、主键和值一致，输出两Sheet质量工作簿、quality manifest、必要预览并复用同一问题文档；只返回`pass`、`blocked`或`incomplete`，不得修改上游、补造证据或调用业务外部系统。`关键词ABA排名缺失、搜索量缺失、没有搜索量`不在分类阶段停止整批；质量副任务核对其状态、原值、受影响派生值和待确认清单，回传主任务在最终质检阶段集中询问用户。用户确认未闭合时QA保持`incomplete`而不是`blocked`；需要改值时回到分类拥有副任务后重新装配和质检。没有独立质量回传或必要用户确认时，主任务不得把正式只读验证标记完成。

## Persistent ownership rule

获准迭代时，副任务只修改 `docs/thread-roles.md` 分配给自己的 Skill、直接引用合同和模块知识。项目总决策、知识索引、端到端流程和跨模块冲突由主任务统一整合。

## Branch rule

只读副任务可以不创建分支。任何会写入仓库的并行副任务必须使用仓库根目录 `docs/github-branching.md` 规定的短期分支；同时写入时使用独立 Worktree。

## End-to-end documentation gate

预期修改本项目 `knowledge/` 或 `.agents/skills/` 的任务，必须把 `docs/end-to-end-workflow.md` 同时列入 Expected files 和验收标准。副任务回传时必须说明端到端文档更新了哪些章节；没有流程影响时，也要更新其同步说明并明确报告“已复核，无流程变化”。未完成该同步的任务状态不能标为 `complete`。
