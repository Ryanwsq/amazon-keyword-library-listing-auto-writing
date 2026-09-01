# Thread roles

本项目使用一个长期主任务和多个长期单一职责副任务。任务在多轮真实验证与规则迭代之间持续存在；实际任务 ID、绝对路径、授权和 Worktree 只保存在被忽略的本机映射中。

## Main task

| Logical role | Task title | Supporting Skills | Responsibility |
|---|---|---|---|
| `keyword-main` | `Amazon关键词词库｜主任务｜main` | `amazon-keyword-library-operations`、`amazon-keyword-library-publication` | 输入与版本锁定、核心层级及多细分类目强等价简称闭环、长期副任务调度、三来源机械合并、完成门、跨模块裁决、总知识与端到端同步、最终验收和交付 |

当前 Codex 任务已绑定 `keyword-main` 逻辑角色。主任务不替代副任务执行其模块，也不在只读验证中边运行边修改规则；副任务不可用、未初始化、操作不便或证据在主任务可见都不是代跑理由。每次派发前必须用本机忽略映射核对逻辑角色、固定标题、Task ID/host、执行cwd、Run、revision和输出目录，任一不符即停止，不创建临时替代任务。只有用户了解影响并明确批准的一次性Run例外才可接收已经产生的证据，且不得成为默认路由或P1证据。

## Persistent side tasks

| Logical role | Task title | Target Skill | Migrated source package | Status before first formal validation |
|---|---|---|---|---|
| `keyword-sif-collector` | `Amazon关键词词库｜SIF竞品反查｜main` | `amazon-keyword-sif-competitor-collection` | `amazon-keyword-source-collection` | draft package; P0 passed |
| `keyword-autocomplete-collector` | `Amazon关键词词库｜Amazon联想采集｜main` | `amazon-keyword-amazon-autocomplete` | `amazon-keyword-source-collection` | draft package; P0 passed |
| `keyword-sellersprite-collector` | `Amazon关键词词库｜卖家精灵扩词｜main` | `amazon-keyword-sellersprite-expansion` | `amazon-keyword-source-collection` | draft package; P0 passed |
| `keyword-cleaner` | `Amazon关键词词库｜关键词清洗｜main` | `amazon-keyword-category-cleaning` | same | migrated draft |
| `keyword-word-frequency-analyst` | `Amazon关键词词库｜词频统计｜main` | `amazon-keyword-word-frequency` | same | migrated draft |
| `keyword-classifier` | `Amazon关键词词库｜关键词分类｜main` | `amazon-keyword-classification` | same | migrated draft |
| `keyword-competition-analyst` | `Amazon关键词词库｜竞争性分析｜main` | `amazon-keyword-competition-analysis` | `amazon-keyword-competition-trend-analysis` | draft package; P0 passed |
| `keyword-trend-analyst` | `Amazon关键词词库｜趋势性分析｜main` | `amazon-keyword-trend-analysis` | `amazon-keyword-competition-trend-analysis` | draft package; P0 passed |
| `keyword-final-workbook-assembler` | `Amazon关键词词库｜最终工作簿装配｜main` | `amazon-keyword-final-workbook-assembly` | same | migrated draft |
| `keyword-quality-reviewer` | `Amazon关键词词库｜独立质量验证｜main` | `amazon-keyword-quality-validation` | current checks were distributed across Skills | draft package; compact/full modes; P0 passed |

上述十个长期副任务已在本设备的独立 Codex 项目中创建、完成只读初始化并进入空闲等待，实际任务 ID、路径、授权和 Worktree 只保存在被忽略的本机映射。所有目标包仍是`draft/planned`而不是已验证能力；十二个Skill已分别建立三个证据登记槽位且当前均为`planned`，全新正常案例01才产生首轮真实 P1 候选证据。

## Ownership rule

每个副任务长期拥有自己的 Skill 目录、直接引用合同和模块知识。只读验证时这些文件不可修改；用户确认问题后，副任务进入获准迭代模式，只修改自己的拥有文件并回传主任务。

项目级 `PROJECT.md`、`knowledge/INDEX.md`、`knowledge/keyword-decision-log.md`、`docs/end-to-end-workflow.md`、`docs/thread-architecture.md` 和跨模块冲突由主任务拥有。副任务只能提出对这些文件的候选更新，不能并行直接修改。

## Shared status rules

- 所有迁入或新建 Skills 均保持 `draft`，直到取得两个真实正常案例和一个真实边界/异常案例的完整 P1 证据。
- `evidence/index.md`只登记槽位和状态；历史运行不得倒填，正式运行中不得更新。一个端到端Run只能为实际执行到的Skill分别产生独立模块候选。
- 第一次正式验证必须在独立仓库固定基线上执行，且所有规则文件只读。
- 词频不产生清洗、分类、竞争、趋势或广告结论。
- 第三板块不读取 SKU 事实卡，不输出广告资格或投放动作。
- 多细分类目的目标细分简称/紧凑表达强等价闭环由主任务在清洗前锁定；清洗发现锚点与完整词组合证据冲突时停止回传，不自行改层级。产品关系与通用词库资格只由第二板块依据已闭合分层锚点、SKU事实和完整词中心对象判定；分类只传递，词频、竞争、趋势和最终通用词库只消费资格为`纳入`的人口。
- 用户开头三组输入中的产品基础信息必须已包含目标类目与多稳定类型回答；齐全后不在运行途中重复询问。日常质量模式compact与触发式full共享全部21项门和完整风险人口，compact不得作为P1三案例的替代。
- 当前 gaming-chair 运行是迁移前问题发现证据，不是独立仓库的第一次正式只读验证。
