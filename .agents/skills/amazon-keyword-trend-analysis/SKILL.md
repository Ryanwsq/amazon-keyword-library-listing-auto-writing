---
name: amazon-keyword-trend-analysis
description: Build one product-library-eligible monthly and quarterly trend sheet for classified Amazon Sheet2 F1-F3 keywords using exact SellerSprite search volume or a locked Sorftime fallback. Use for月度环同比、季度环同比、实际搜索量折线图和趋势矩阵；do not use for competition, source mining, SIF trends, seasonality labels or ad decisions.
---

# Amazon Keyword Trend Analysis

## 目标

按锁定来源优先级读取精确词月搜索量，为Sheet2中`通用词库资格=纳入`的F1–F3生成至少24完整月证据、最近12月与4季度矩阵，以及月度和季度实际搜索量折线图。

## 输入

锁定分类工作簿、Sheet2总人口与资格人口、`通用词库资格=纳入`的F1–F3人口、Keyword_ID、站点、最新完整月、查询批次、趋势版本、来源优先级、选定提供商和获准趋势接口。

## 输出

只含`Sheet8_品类关键词趋势性`的过程工作簿、trend manifest和紧凑状态；不把24个月逐词数据贴进主任务对话。

## 可调用能力

- `keyword.library.trend.analyze`
- `keyword.trend.sellersprite.query`
- `keyword.trend.sorftime.query`
- `keyword.trend.outputs.write-and-verify`
- `keyword.trend.matrix.calculate`

## 执行步骤

1. 读取知识、判断边界和`references/output-contract.md`，锁定Sheet2资格人口、`纳入`且为F1–F3的人口、主键、站点、最新完整月、至少24月范围、来源优先级和版本；不重算通用词库资格。
2. 默认对每个完整英文关键词执行卖家精灵精确词趋势查询。卖家精灵不可用时允许改用Sorftime精确词月搜索量；一旦某个提供商成为本Run正式来源，全部锁定关键词必须使用同一提供商。主来源在批次中途失败时，保留诊断证据并从头用备用来源重跑全部人口，不混源；主来源中途恢复只影响下一个新Run。
3. 保存选定提供商、入口、查询时间、实际返回和月份；当前未结束月排除。月份为空/不可解析无效，缺值留空，不填0、不插值。不得使用SIF、词根、近义词或跨提供商补月。
4. 至少形成24个已结束完整月的查询范围；把资格纳入F1–F3人口、锁定提供商、最新完整月和逐词月份原值输入`scripts/keyword_deterministic_core.py trend`。最近12完整月进入月度矩阵，额外历史用于同比、季度基准和月度实际搜索量图。
5. 由确定性核心计算月环比/月同比。当前或基准缺失、基准为0时留空。
6. 由确定性核心按完整自然季度求和；任一月缺失则该词该季度搜索量、环比、同比全部留空。表格展示最近4完整季度；季度图只使用锁定观察范围内三个日历月均存在的完整自然季度。脚本不查询来源、不改变提供商、不补0或插值。
7. 写入关键词索引、36行月度矩阵、12行季度矩阵和两张实际搜索量折线图。月度图横轴为全部可用完整年月、纵轴为实际月搜索量；季度图横轴为全部可用完整自然季度、纵轴为三个完整月之和。每个关键词在每张图恰好一条线；环比和同比只留在表格，不进入图表序列。
8. 验证人口、月份、季度、空值、公式、矩阵列、图表范围和序列数；渲染Sheet及两图。Artifact Tool重载后，按`references/output-contract.md`调用`scripts/audit_trend_ooxml.py`遍历全部worksheet及其drawing/chart关系，分别闭合月度图、季度图和实际搜索量引用。审计结果为`auditor_failure`时先停止并修复审计证据链，不得把审计器自身失效误记为工作簿业务失败或静默通过。

## 质量标准

- 人口恰好等于Sheet2中`通用词库资格=纳入`的F1–F3；`不纳入/待复核`和其他人口零混入。
- 每词使用同一锁定提供商的精确完整词且至少查询24个完整月；来源、入口、时间和月份覆盖可追溯。
- 月度固定12×3，季度固定4×3，每词在两矩阵恰好一列。
- 两图各有`关键词数`条实际搜索量序列；月/季环同比百分比序列均为零。
- 确定性计算版本、适用人口、单一提供商和结果JSON哈希进入manifest；仍须执行工作簿、公式、渲染和OOXML包级审计。
- OOXML包级审计覆盖全部worksheet、drawing和chart关系；业务manifest或工作簿声明存在图表/公式而解析结果为零时必须返回`auditor_failure`。
- 无趋势标签、季节性、广告资格或行动建议。
- Skill保持draft/planned，未完成真实三案例不称verified。

## 异常处理

卖家精灵不可用时按合同回退Sorftime；两个来源都不可用或全局无完整月为`not_executed`。至少一词零有效数据或环同比基准整体不足为`incomplete`；各词有数据但部分月份缺失可为`completed_with_gaps`；通用词库资格、主键、人口、来源一致性、矩阵或图表无法闭合为`blocked`。不得回退SIF或静默混合提供商。
