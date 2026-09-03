---
name: prioritize-amazon-insight-tags
description: 将本品产品信息 Excel 与竞品场景、人群、用途洞察 Excel 转换为固定五 Sheet 的标签归一化、Coverage、Listing Expression、市场分类、产品参数对比和内容优先级工作簿。适用于场景、人群、用途、频率标签优先级决策；不负责上游 Alexa 提问、ASIN 洞察采集或双问并集生成。
---

# Amazon 场景人群用途标签优先级

## 唯一工作流

本 Skill 只执行一个下游决策流程：

```text
本品产品信息 Excel + 竞品洞察并集 Excel
→ 有效竞品判定与父体去重
→ 人群 / 场景 / 用途 / 频率标签归一化
→ Coverage
→ Amazon Listing Expression
→ 标签市场分类
→ 本品参数与竞品事实对比
→ 五 Sheet 内容优先级工作簿
```

不执行 Alexa 提问，不从纯 ASIN 开始抓取五维洞察，也不生成“抓取结果 + 说明”的二 Sheet 并集工作簿。若用户尚未提供上游竞品洞察并集表，应要求其提供该输入，或改用专门的上游采集 Skill。

## 开始前读取

每次执行必须完整读取：

1. [references/tag-priority-sop-v2.md](references/tag-priority-sop-v2.md)：V2.0 业务规则、阈值、公式和五 Sheet 字段的唯一完整来源。
2. [references/final-workbook-format.md](references/final-workbook-format.md)：最终工作簿的排序、分区、配色和可读性规范。

生成工作簿时，将 [assets/golden-tag-priority-workbook.xlsx](assets/golden-tag-priority-workbook.xlsx) 作为黄金版式样例，只复用结构、公式逻辑和视觉语言；不得复用其中的 57D 示例 ASIN、标签、分数、产品事实或结论。

## 输入合同

- 固定接收两个 Excel，不要求用户额外整理第三张输入表。
- 输入 1 读取“新品基础信息”“新品基础配置”“竞品对标ASIN”。
- 输入 2 读取“抓取结果”；存在“说明”时必须读取字段执行状态。
- Amazon US Listing 与图片核验属于执行动作，不是第三个用户输入。
- 不得用模型常识、营销推断或未提供的产品参数补全事实。
- 无法核验的数据写“未知 / 未验证”，不得按 0 处理。

## 关键不变量

- 竞品以 ASIN 为唯一统计单位；同父体重复子体只保留一个代表 ASIN。
- 有效竞品少于 10 个时可以试算，但最终优先级必须标记“样本不足，不得作为正式结论”。
- 标签类型固定为人群、场景、用途、频率；频率只提取明确的时长、频次或强度表达。
- 同义表达必须归一；一个 ASIN 对同一标签最多贡献一次 Coverage。
- `未执行`、`身份异常`、`未抓取到`、页面不可访问和技术停止都不是 0。
- Coverage、Expression Score、Market Expression、市场分类、Product Advantage 与最终优先级必须公式驱动且可追溯。
- 最终优先级只允许使用 SOP 固定的 Coverage、Market Expression、Direct Fit、Differentiation、Proofability 闸门，不增加主观评分。

## Listing Expression 证据

- 对每个有效竞品核验 Amazon US Listing 的 Title、Image 2–4、Bullet 1–2、A+ 核心、后部副图、Bullet 3–5、A+ 其他。
- 主图默认不计入标签 Expression。
- 同一 ASIN、同一标签、同一资源位最多计一次。
- Listing 无法访问时标记“未验证”，不进入 Market Expression 分母。
- 保留原始证据摘要、Amazon 来源 URL 与抓取状态。

## 固定交付

只交付一个 `.xlsx`，并且严格包含以下五个 Sheet：

1. `竞品打标签`
2. `标签覆盖率`
3. `标签介绍度`
4. `标签分类`
5. `产品参数对比与优先级`

Sheet 名称、列名、列顺序、计算口径、排序与配色不得随意改变。使用 Spreadsheets Skill 和规定的工作簿工具创建、公式检查、渲染与导出；不得用聊天文字代替固定 Sheet。

## 交付前验收

- 输入 Sheet、ASIN 状态、父体去重与有效竞品分母闭环。
- 标签归一化、类型归属和频率证据符合 SOP。
- 五张表的 ASIN 主键、标签主键、公式引用和行数一致。
- 最终表按优先级 1、2、3、不采用/观察依次排列；每个标签只填写一个对应的最终类型列。
- 公式错误扫描不包含 `#REF!`、`#DIV/0!`、`#VALUE!`、`#NAME?` 或 `#N/A`。
- 五个 Sheet 已完成视觉检查：有效/无效 ASIN、标签类型、ASIN 介绍度分区和最终优先级清晰可扫读。


<!-- listing-structure-2: navigation only; original SOP above is preserved -->

本节仅补齐角色包结构导航；上方原SOP及其完整reference继续拥有业务规则和读取顺序。

## 目标

05接收；获明确处理授权后按固定五Sheet合同处理标签

## 输入

本品三表和竞品五维洞察并集两个工作簿

## 输出

05固定五Sheet标签、Coverage、Expression和参数优先级

## 执行步骤

完整执行上方[唯一工作流](SKILL.md#唯一工作流)及其必读合同，不以结构导航替代正文。

## 质量标准

执行上方[交付前验收](SKILL.md#交付前验收)的全部条件。

## 异常处理

按上方[关键不变量](SKILL.md#关键不变量)及必读合同处理；各模块原有来源、停止及重试边界不变。

## 可调用能力

- `listing.tag-priority.execute`：05接收；获明确处理授权后按固定五Sheet合同处理标签。

登记见[capabilities.yaml](capabilities.yaml)。planned仅为工具化需求，非已验证工具；真实执行前仍须按原SOP确认可用能力、输入和授权。[角色边界](Agent.md)、[知识索引](knowledge/index.md)、[证据状态](evidence/index.md)不授予额外权限。
