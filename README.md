# Amazon Keyword Library

本仓库是 Amazon 关键词词库项目的独立、可审查工作区，负责从一次用户输入开始，完成三来源采集、品类清洗、分类、词频、竞争、趋势、最终装配和独立质量验证。

## 当前阶段

- 当前长期主任务：`Amazon关键词词库｜主任务｜main`。
- 远端私有仓库：`Ryanwsq/amazon-keyword-library`；`main`是唯一长期基线。
- 十个长期业务副任务已建立；当前共十二个项目Skills，全部为`draft`且能力均为`planned`。
- 2026-08-24已在既有减负输出合同上增加最终`二类词`独立Sheet，最终工作簿固定为八Sheet；这次规则同步不构成P1。
- 首轮旧结构真实案例因Amazon联想`not_executed`且合同已变化，只作为问题发现证据。下一步是在新固定revision上完整只读重跑。

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
- 知识索引：`knowledge/INDEX.md`
- 项目Skills：`.agents/skills/`

## 数据边界

真实产品资料、ASIN、原始接口响应、业务工作簿、浏览器状态、任务ID、绝对路径、Token和账号信息只保存在本机忽略目录。Git和飞书只同步脱敏、稳定、经用户确认的规则、Skills、知识、合同和状态摘要。
