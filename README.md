# Amazon Keyword Library

本仓库是 Amazon 关键词词库项目的独立、可审查工作区，负责从用户开头提供的三组输入开始，完成三来源采集、品类清洗、分类、词频、竞争、趋势、最终装配和独立质量验证。

## 当前阶段

- 当前长期主任务：`Amazon关键词词库｜主任务｜main`。
- 远端私有仓库：`Ryanwsq/amazon-keyword-library`；`main`是唯一长期基线。
- 十个长期业务副任务已建立；当前共十二个项目Skills，全部为`draft`且能力均为`planned`。
- 十二个Skill现已各自建立`evidence/index.md`，固定登记两个正常案例和一个边界/异常案例；当前36个槽位为11个`accepted`、1个`candidate`和24个`planned`，索引与单个案例均不构成P1。
- 2026-08-24已在既有减负输出合同上增加最终`二类词`独立Sheet，最终工作簿固定为八Sheet；这次规则同步不构成P1。
- 2026-08-24又锁定输入核心门、卖家精灵网页完整导出优先和严格副任务执行边界；用户不指定核心词，主任务只在类目确有多个稳定产品类型细分时判断可选细分核心词。
- 2026-08-26增加多细分类目的目标细分简称/紧凑表达强等价闭环：省略一级品类或用途等上位限定词不能成为机械摘除依据；锚点冲突必须停止，清洗与QA按行反查而不由共享理由模板外推整组。
- 2026-08-31锁定三组开头输入；2026-09-02进一步锁定运行类型：产品基础信息必须已经包含目标类目和多稳定类型回答；未明确为测试时默认production且不调度独立质量验证，装配仍执行适用机械门与风险人口检查；只有test-validation使用compact-validation/full-regression，规则/结构/检查器变化和P1案例必须full-regression。分类三种数据缺口准确传递后自动按允许缺口闭合，不等待运行途中人工确认。
- 2026-09-02新增无损运行性能层：以规则文件哈希和stage key支持精确断点续跑、并行登录预检、失败后代隔离和纯机械确定性计算；完整短语语义、强等价闭环、风险人口、八Sheet及21项Gate不削减。当前只通过P0/夹具，下一次test-validation必须full-regression后才能评价无损与实际提速。
- 最近一次真实Run的八Sheet候选与冻结QA为`blocked/P1=false`。当前已获准在规则校验后从最早受影响的锚点交接生成新版本并重跑依赖输出；旧工作簿保持问题证据。下一次正常案例仍须在新固定revision上由各拥有副任务完整只读执行。
- 下一次测试验证因本批质量合同和封包检查器发生变化，必须使用`run_type=test-validation + full-regression`；普通production不调用独立质量验证。仍需按各Skill剩余槽位补齐两个正常加一个边界案例，不能以人工确认或production运行倒填P1。

## 最终交付

每个正式Run只交付两个顶层对象：

1. `过程性文件/`：保存各板块工作簿、manifests、原始证据、检查、渲染、唯一问题文档和独立质量报告。
2. `<Run_ID>-最终关键词词库.xlsx`：固定八个可见Sheet——最终关键词决策总表、SKU事实卡、品类产品通用词库、二类词、关键词竞争性分析、关键词趋势性分析、词频统计、否词库。通用词库、词频、竞争和趋势只使用第二板块已判定`通用词库资格=纳入`的适用人口；`二类词`Sheet机械复制分类完成的Sheet4全人口，不重新判断且允许零行。

## 主要入口

- 项目状态：`PROJECT.md`
- 项目规则：`AGENTS.md`
- 端到端流程：`docs/end-to-end-workflow.md`
- 任务架构：`docs/thread-architecture.md`
- 任务角色：`docs/thread-roles.md`
- 判定边界：`docs/keyword-judgment-boundaries.md`
- 运行性能合同：`docs/runtime-optimization-contract.md`
- 规则覆盖映射：`contracts/runtime-rule-map.json`
- 知识索引：`knowledge/INDEX.md`
- 项目Skills：`.agents/skills/`

## 数据边界

真实产品资料、ASIN、原始接口响应、业务工作簿、浏览器状态、任务ID、绝对路径、Token和账号信息只保存在本机忽略目录。Git和飞书只同步脱敏、稳定、经用户确认的规则、Skills、知识、合同和状态摘要。
