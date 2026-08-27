# Project Skills

本项目把稳定知识、判定边界和执行流程分开维护：

- 人类可读端到端流程：`../../docs/end-to-end-workflow.md`
- 稳定领域知识：`../../knowledge/product-keyword-library.md`
- 历史案例证据：`../../knowledge/keyword-cleaning-case-evidence.md`
- 版本决策：`../../knowledge/keyword-decision-log.md`
- 当前状态与开放问题：`../../PROJECT.md`
- 判定边界：`../../docs/keyword-judgment-boundaries.md`
- 执行流程：下列单一职责 Skill 包

| Skill | Capability | Responsibility | Maturity |
|---|---|---|---|
| `amazon-keyword-library-operations` | `keyword.library.version.manage`、`keyword.source.merge-and-assemble` | 主任务编排、版本、三来源机械合并、第一板块两Sheet总门与验收 | draft |
| `amazon-keyword-sif-competitor-collection` | `keyword.source.competitor-traffic.query`、`keyword.source.sif.persist-and-verify` | 逐竞品SIF反查、完整响应本机落盘、七列明细和锚点候选证据 | draft |
| `amazon-keyword-amazon-autocomplete` | `keyword.source.autocomplete.capture` | 固定内置浏览器环境的Amazon可见联想矩阵 | draft |
| `amazon-keyword-sellersprite-expansion` | `keyword.source.keyword-mining.query`、`keyword.source.sellersprite.paginate-and-verify` | 官网完整导出优先；有细分核心词时分别使用一级核心词和细分核心词，否则只用一级核心词；四字段机械去重、逐种子2–3个收敛Pass和损失风险 | draft |
| `amazon-keyword-category-cleaning` | `keyword.library.clean` | 第二板块一级品类三去向与Sheet2通用词库资格清洗 | draft |
| `amazon-keyword-word-frequency` | `keyword.library.word-frequency` | 只用资格纳入的Sheet2统计去介词单词和以介词为断点的相邻双词 | draft |
| `amazon-keyword-classification` | `keyword.library.classify` 及分类/输出子能力 | Sheet2 F1–F5/LT与动态语义列、Sheet4流量分类和五列最小否词库 | draft |
| `amazon-keyword-competition-analysis` | `keyword.library.competition.analyze`、`keyword.competition.sif-top3.query`、`keyword.competition.outputs.write-and-verify` | 为资格纳入的Sheet2 F1–F4建立Top3-only独立竞争Sheet | draft |
| `amazon-keyword-trend-analysis` | `keyword.library.trend.analyze` 及两个查询/输出子能力 | 为资格纳入的F1–F3生成至少24月、月/季度环同比矩阵和两图 | draft |
| `amazon-keyword-final-workbook-assembly` | `keyword.workbook.final.assemble`、`keyword.workbook.sheet-manifest.verify` | 装配过程文件夹和八Sheet最终工作簿，以三去向全人口建立51+N总表并机械复制二类词Sheet | draft |
| `amazon-keyword-quality-validation` | `keyword.quality.validate` | 独立只读复核全链路、两对象交付、八Sheet、二类词闭环和21项装配门 | draft |
| `amazon-keyword-library-publication` | `keyword.library.publish` | 经审查知识的脱敏项目内发布 | draft |

当前共有十个业务Skill（SIF、Amazon联想、卖家精灵、品类清洗、词频、关键词分类、竞争、趋势、最终装配、独立质量验证）和两个项目维护Skill（operations、publication）。2026-08-26合同固定分层核心、多细分类目的目标细分简称强等价闭环、条件式Amazon联想锚点、卖家精灵官网完整导出优先及一至两个锁定种子、两Sheet第一板块、四Sheet清洗与Sheet2通用词库资格、资格纳入人口的介词过滤词频/Top3-only竞争/24月趋势、三去向51+N总表、分类Sheet4机械复制的二类词独立Sheet和八Sheet最终工作簿；质量验证只读执行21项装配门并按行审计简称族，不能由共享理由模板外推整组。十二个Skill均为`draft`，全部能力为`planned`，没有真实P1三案例前不得声称已验证。

2026-08-27起，十二个包都必须从`draft`阶段维护`evidence/index.md`，固定登记`case-01-normal`、`case-02-normal`和`case-03-edge-or-error`三个槽位。当前全部槽位为`planned`；索引不是案例证据，不得用历史运行倒填。一个真实端到端Run可以为实际执行到的每个Skill各贡献一个案例，但必须分别形成模块证据并通过该Skill自身质量门。

2026-08-20 已完成以下结构调整，并通过当前仓库 P0：

- `amazon-keyword-source-collection` 拆为 SIF竞品反查、Amazon联想采集和卖家精灵扩词三个单一职责 Skill；三来源机械合并继续由主任务控制。
- `amazon-keyword-competition-trend-analysis` 拆为竞争性分析和趋势性分析两个单一职责 Skill。
- 新增独立质量验证 Skill，统一执行数量、主键、版本、公式、渲染和图表闭环检查。

旧组合包文件已移除，原包到新包的映射保留在 `docs/thread-roles.md` 和版本决策记录中。结构拆分未改变业务规则，也不把任何能力升级为`verified`。

现有十二个包都遵守仓库根目录 `docs/skill-package-standard.md`。P0只表示结构可审查；历史案例或迁入前本地试算发生在当前包建立之前，不能反向当作新 Skill 的 P1 evidence。每个 Skill 需重新完成两个正常案例和一个边界/异常案例，才可考虑升级为 `verified`。

任何项目知识或 Skill 变更都必须在同一批变更中同步 `../../docs/end-to-end-workflow.md`；没有流程影响时也要更新其同步说明。

本仓库全部 Skills 都位于根目录 `.agents/skills/`。不要复制本机全局 Skill，也不要把原始业务数据、完整聊天或本机路径写入 Skill。
