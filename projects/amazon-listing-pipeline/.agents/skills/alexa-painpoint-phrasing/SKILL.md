---
name: alexa-painpoint-phrasing
description: Read the Excel workbook produced by alexa-painpoint-frequency and use Alexa for Shopping to generate natural, conversational ways shoppers might describe and ask about each confirmed pain point. Use only when the input is that upstream workbook; label results as Alexa-generated phrasing rather than verified shopper quotes, and do not write Listing Q&A answers or other Listing copy.
---

# Alexa Pain-Point Phrasing

## Outcome and boundary

Use the previous pain-point workbook as the only input. For every confirmed `标准化痛点 + ASIN` pair, ask Alexa for:

1. Natural everyday descriptions of the pain point.
2. Natural pre-purchase questions about the pain point.

Deliver one `.xlsx` workbook containing only:

1. `口语表达明细`
2. `口语表达汇总`

The output is `Alexa归纳的口语化表达`, not verified shopper wording. Never call it a direct quote, consumer original wording, review frequency, or statistically representative consumer language. Stop before writing Listing Q&A answers, titles, bullets, keywords, tags, selling points, or priorities.

## Required upstream input

Accept only the `.xlsx` output created by `alexa-painpoint-frequency`. It must contain both required sheets and columns:

### Sheet `痛点明细`

- `ASIN`
- `处理状态`
- `标准化痛点`
- `Supporting wording`
- `是否计入统计`

### Sheet `痛点频率统计`

- `标准化痛点`
- `出现ASIN数`
- `有效ASIN总数`
- `痛点频率`
- `涉及ASIN`

Use only rows where `处理状态 = 有效` and `是否计入统计 = 是`. Cross-check every `标准化痛点 + ASIN` pair against `涉及ASIN`; do not invent missing pairs. Remove exact duplicate pairs while preserving the upstream order.

If the required sheets or columns are missing, stop and request the correct upstream workbook. Do not infer a replacement schema from an unrelated spreadsheet.

## Build the pain-point cue

Alexa needs a short English cue to replace `[PAIN POINT]` in the fixed questions.

1. Prefer the upstream English `Supporting wording` when it clearly represents the standardized pain point.
2. Otherwise translate `标准化痛点` into a neutral English concept.
3. Keep the cue at or below 120 characters.
4. Do not add causes, consequences, user groups, scenarios, or severity absent from the upstream pain point.
5. Record the cue as `查询线索`; never present it as shopper language.

Example:

- `标准化痛点`: `容易漏气`
- `查询线索`: `air leakage or difficulty staying inflated`

## Alexa access and execution

Use the available authenticated Alexa for Shopping browser or app connection. For each deduplicated `标准化痛点 + ASIN` pair:

1. Open or bind Alexa to the exact ASIN and confirm the product matches.
2. Insert the English cue into Q1 and Q2.
3. Ask both questions in order and preserve the complete raw answers.
4. Keep ASIN sessions separate to avoid cross-product contamination.
5. Retry a failed question once. If it still fails, mark that pair `询问失败` and continue with the remaining pairs.

If Alexa access or authentication is unavailable, stop and request access. Do not substitute a general model, ordinary web search, or fabricated expressions.

## Fixed questions

Do not mention Customer Reviews or Customer Q&A in either question. Do not add more discovery or validation questions.

### Q1 — How shoppers describe the pain point

> How do shoppers typically describe “[PAIN POINT]” in casual, everyday language when talking about this type of product? Provide short, natural expressions only, one per line. Do not explain, rank, or use technical or marketing language.

Base length with the placeholder: 236 characters.

### Q2 — How shoppers ask about the pain point

> How would shoppers naturally ask about “[PAIN POINT]” before buying this type of product? Provide short, conversational questions only, one per line. Do not explain, rank, or use technical or marketing language.

Base length with the placeholder: 211 characters.

Because the replacement cue is capped at 120 characters, both final questions remain below 500 characters.

## Parse and normalize expressions

- Split Alexa's answer into individual expressions without turning explanations into expressions.
- Preserve each expression exactly as Alexa returned it, except for trimming surrounding whitespace and list markers.
- Label Q1 results `描述式表达` and Q2 results `问句式表达`.
- Exclude technical definitions, marketing copy, rankings, explanations, incomplete fragments with no understandable meaning, and content unrelated to the target pain point.
- Within one `ASIN + 标准化痛点 + 表达类型`, remove exact duplicates.
- Group semantically equivalent expressions into a short Chinese `表达模式`, while preserving every original Alexa expression.
- Do not merge expressions that imply materially different questions. For example, `Will it stay inflated overnight?` and `How long does inflation take?` belong to different patterns.

Any apparent recurrence is recurrence across Alexa outputs for queried ASINs. It is not consumer usage frequency.

## Workbook schema

### Sheet `口语表达明细`

Use one row per Alexa expression. Add one status row when a pair produces no usable expression or fails.

Columns, in order:

1. `标准化痛点`
2. `上游痛点频率`
3. `ASIN`
4. `查询线索`
5. `问题编号` — `Q1` or `Q2`
6. `表达类型` — `描述式表达` or `问句式表达`
7. `Alexa归纳表达`
8. `表达模式`
9. `Alexa原始回答`
10. `处理状态` — `有效` / `未返回可用表达` / `询问失败` / `商品不匹配`
11. `是否计入汇总` — `是` / `否`
12. `排除原因`

### Sheet `口语表达汇总`

Use one row per `标准化痛点 + 表达模式`.

Columns, in order:

1. `标准化痛点`
2. `上游痛点频率`
3. `表达模式`
4. `表达类型`
5. `表达覆盖ASIN数`
6. `该痛点涉及ASIN数`
7. `Alexa表达覆盖率`
8. `代表性Alexa归纳表达` — retain up to five distinct expressions
9. `涉及ASIN`
10. `性质说明` — fixed value `Alexa归纳表达，非消费者原话`

Calculate:

`Alexa表达覆盖率 = 返回该表达模式的ASIN数 ÷ 上游该痛点涉及ASIN数`

This metric describes recurrence across Alexa outputs only. Do not interpret it as the percentage of consumers using that wording.

Sort the summary by:

1. `上游痛点频率` descending.
2. `标准化痛点` ascending.
3. `表达类型`, with `问句式表达` before `描述式表达`.
4. `Alexa表达覆盖率` descending.

Format both percentage fields with two decimals. Do not assign high/medium/low tiers or produce a recommended final Q&A question.

## Completion check

Before delivery, verify that:

- The input is the upstream pain-point workbook with both required sheets.
- Every processed pair existed in the upstream output.
- Every final prompt is under 500 characters.
- Q1 and Q2 do not mention Reviews or Customer Q&A.
- All expressions are labeled as Alexa-generated phrasing rather than shopper quotes.
- The workbook contains exactly the two required output sheets.
- No Listing Q&A answer, title, bullet, keyword, tag, selling-point ranking, or consumer-frequency claim appears.

Deliver the `.xlsx` file and report only the numbers of upstream pain points, processed ASIN-pain-point pairs, failed pairs, and retained Alexa expressions.

<!-- listing-structure-2: navigation only; original SOP above is preserved -->

本节仅补齐角色包结构导航；上方原SOP及其完整reference继续拥有业务规则和读取顺序。

## 目标

仅对合格上游痛点生成Alexa归纳表达，不写Listing正文

## 输入

合格04中已有的标准化痛点与ASIN配对

## 输出

08口语明细与汇总两Sheet，标为Alexa归纳而非消费者原话

## 执行步骤

完整执行上方[Alexa access and execution](SKILL.md#alexa-access-and-execution)及其必读合同，不以结构导航替代正文。

## 质量标准

执行上方[Completion check](SKILL.md#completion-check)的全部条件。

## 异常处理

按上方[Required upstream input](SKILL.md#required-upstream-input)及必读合同处理；各模块原有来源、停止及重试边界不变。

## 可调用能力

- `listing.painpoint-phrasing.execute`：仅对合格上游痛点生成Alexa归纳表达，不写Listing正文。

登记见[capabilities.yaml](capabilities.yaml)。planned仅为工具化需求，非已验证工具；真实执行前仍须按原SOP确认可用能力、输入和授权。[角色边界](Agent.md)、[知识索引](knowledge/index.md)、[证据状态](evidence/index.md)不授予额外权限。
