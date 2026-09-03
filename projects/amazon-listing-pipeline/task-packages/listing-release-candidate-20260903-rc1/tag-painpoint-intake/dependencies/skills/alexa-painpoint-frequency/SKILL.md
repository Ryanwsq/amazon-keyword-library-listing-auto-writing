---
name: alexa-painpoint-frequency
description: Use Alexa for Shopping to extract evidence-backed shopper pain points and pre-purchase concerns from an Amazon ASIN list, normalize equivalent issues, and calculate cross-ASIN frequency for later Listing Q&A planning. Use when the input is an ASIN list and the required output is pain-point detail plus frequency statistics; do not use it to write Q&A, keywords, titles, bullets, or selling-point priorities.
---

# Alexa Pain-Point Frequency

## Outcome and boundary

Take an Amazon ASIN list, query Alexa for Shopping for each ASIN, and deliver one `.xlsx` workbook containing only:

1. `痛点明细`
2. `痛点频率统计`

This workflow ends after pain-point frequency is calculated. Do not generate Listing Q&A copy, keywords, titles, bullets, tags, selling points, or priority recommendations. Do not replace Alexa for Shopping with a general model, ordinary web search, or an inferred review summary.

## Input contract

Accept a pasted list or an Excel/CSV/TSV file with one required field: `ASIN`.

- Default marketplace: Amazon US.
- Normalize ASINs to uppercase, trim whitespace, preserve first-seen order, and remove exact duplicates.
- Treat an ASIN as syntactically valid only when it contains 10 letters or digits.
- Do not add product facts, keywords, titles, or proposed pain points to the input.
- If an ASIN is invalid, unavailable on Amazon US, resolves to the wrong product, or cannot be queried completely, record its processing status in `痛点明细` and exclude it from the frequency denominator.

## Alexa access

Use the available authenticated Alexa for Shopping browser or app connection. For each ASIN:

1. Open or bind Alexa to that exact product.
2. Confirm that the returned product/ASIN matches the target before collecting answers.
3. Keep product sessions separate so one ASIN's answers do not contaminate another ASIN.
4. Ask Q1 through Q7 in order and preserve every raw answer.
5. Retry a failed question once. If any of Q1-Q7 still cannot be completed, mark the ASIN `抓取失败` and exclude it from the effective-ASIN denominator.

If live Alexa access is unavailable or authentication blocks the workflow, stop and request access or user-exported Alexa answers. Do not silently substitute another source.

## Fixed questions

Ask all seven questions for every ASIN. Do not add a third validation round.

Require the answer format:

`Issue | Source | Supporting wording`

When no supported issue exists, Alexa should answer `Not found`.

### Q1 — Review pain points

> Based only on customer reviews for this product, what specific problems, drawbacks, or limitations do shoppers explicitly report? List one issue per line in this format: Issue | Source | Supporting wording. Do not infer problems or treat missing information as a problem. If no supported issue is found, answer “Not found.”

### Q2 — Customer Q&A concerns

> Based only on Customer Questions & Answers for this product, what problems, concerns, or limitations do shoppers explicitly ask about? List one concern per line in this format: Issue | Source | Supporting wording. Do not infer concerns that were not actually raised. If no supported concern is found, answer “Not found.”

### Q3 — Function and performance

> Do customer reviews or Customer Q&A explicitly mention any problems with this product’s functions, performance, or ability to deliver the expected result? List one issue per line in this format: Issue | Source | Supporting wording. Include only supported issues. If none are found, answer “Not found.”

### Q4 — Materials, quality, and durability

> Do customer reviews or Customer Q&A explicitly mention any problems with materials, construction quality, damage, wear, durability, or reliability over time? List one issue per line in this format: Issue | Source | Supporting wording. Include only supported issues. If none are found, answer “Not found.”

### Q5 — Setup and use difficulty

> Do customer reviews or Customer Q&A explicitly mention any difficulties with assembly, setup, operation, adjustment, cleaning, maintenance, storage, or transportation? List one issue per line in this format: Issue | Source | Supporting wording. Include only supported issues. If none are found, answer “Not found.”

### Q6 — Size, fit, and compatibility

> Do customer reviews or Customer Q&A explicitly mention any problems involving size, fit, capacity, compatibility, available space, or suitability for particular users or situations? List one issue per line in this format: Issue | Source | Supporting wording. Include only supported issues. If none are found, answer “Not found.”

### Q7 — Use limitations and unmet expectations

> Do customer reviews or Customer Q&A explicitly describe situations where this product is difficult to use, unsuitable, or does not meet shoppers’ expectations? List one issue per line in this format: Issue | Source | Supporting wording. Do not speculate. If no supported issue is found, answer “Not found.”

All seven prompts are under 500 characters, including spaces and punctuation.

## Evidence rules

Count a result only when Alexa explicitly attributes a concrete problem or concern to `Customer Reviews` or `Customer Q&A`.

- Preserve the complete Alexa raw answer for auditability.
- Preserve the shopper wording or Alexa-provided supporting wording when available.
- A Review result represents a reported use problem.
- A Customer Q&A result represents a pre-purchase concern. Phrase it as a concern, not as a proven defect. For example, convert a question about whether an item fits a vehicle into `车型兼容性顾虑`, not `无法适配该车型`.
- Exclude inference, generic possibilities, missing Listing information, seller claims, unrelated products, unsupported conclusions, and content without a Review or Customer Q&A attribution.
- `Not found` means no supported result was returned; it does not prove that the product has no such problem.
- Never claim a review-count frequency. Alexa is not being used to count individual review occurrences.

## Normalize and deduplicate

Normalize accepted issues into concise Chinese pain-point labels before statistics.

- Merge only semantically equivalent expressions, such as `padding compresses quickly`, `seat goes flat`, and `cushion loses support` into `坐垫容易塌陷`.
- Do not merge merely related issues with different causes or purchase implications. For example, `充气困难` and `气泵压力表不准` remain separate.
- Within one ASIN, count the same normalized pain point once even when Q1-Q7 surface it repeatedly.
- Preserve all triggering question IDs and supporting evidence in the detail row when duplicates are merged.
- Across different ASINs, count each ASIN once for that normalized pain point.

## Workbook schema

### Sheet `痛点明细`

Use one row per `ASIN + 标准化痛点`. When an ASIN has no supported pain point or fails processing, add one status row so the denominator remains auditable.

Columns, in order:

1. `ASIN`
2. `产品标题`
3. `处理状态` — `有效` / `有效但未发现痛点` / `抓取失败` / `无效ASIN` / `商品不匹配`
4. `触发问题` — one or more of Q1-Q7
5. `标准化痛点`
6. `具体表现`
7. `证据来源` — `Review` / `Customer Q&A` / both when independently supported
8. `Supporting wording`
9. `Alexa原始回答`
10. `是否计入统计` — `是` / `否`
11. `排除原因`

### Sheet `痛点频率统计`

Columns, in order:

1. `排名`
2. `标准化痛点`
3. `出现ASIN数`
4. `有效ASIN总数`
5. `痛点频率`
6. `涉及ASIN`
7. `典型Supporting wording` — retain 1–3 representative entries
8. `数据状态` — `正式统计` when effective ASINs are at least 10; otherwise `样本不足，仅供试算`

Calculate:

`痛点频率 = 出现该痛点的有效ASIN数 ÷ 有效ASIN总数`

The denominator is the number of ASINs that successfully completed Q1-Q7, including successfully processed ASINs for which no supported pain point was found. Exclude invalid, mismatched, unavailable, and incompletely queried ASINs.

Sort by `痛点频率` descending. For ties, sort by `标准化痛点` ascending to keep output deterministic. Format frequency as a percentage with two decimals. Do not create high/medium/low thresholds or convert frequency into a selling-point priority.

## Completion check

Before delivery, verify that:

- Every effective ASIN completed Q1-Q7.
- Every counted detail row has Review or Customer Q&A support.
- Duplicate ASIN-level pain points were merged before counting.
- The frequency denominator matches the effective-ASIN definition.
- The workbook contains exactly the two required sheets.
- No Listing Q&A copy, keyword, title, bullet, tag, selling-point ranking, or unsupported interpretation appears in the output.

Deliver the `.xlsx` file and report only the counts of input ASINs, effective ASINs, failed/excluded ASINs, and normalized pain points found.

<!-- listing-structure-2: navigation only; original SOP above is preserved -->

本节仅补齐角色包结构导航；上方原SOP及其完整reference继续拥有业务规则和读取顺序。

## 目标

04接收；获明确采集授权后执行七题及有效ASIN频率统计

## 输入

锁定ASIN列表及Alexa采集授权

## 输出

04痛点明细与有效ASIN频率两Sheet

## 执行步骤

完整执行上方[Alexa access](SKILL.md#alexa-access)及其必读合同，不以结构导航替代正文。

## 质量标准

执行上方[Completion check](SKILL.md#completion-check)的全部条件。

## 异常处理

按上方[Evidence rules](SKILL.md#evidence-rules)及必读合同处理；各模块原有来源、停止及重试边界不变。

## 可调用能力

- `listing.painpoint-frequency.execute`：04接收；获明确采集授权后执行七题及有效ASIN频率统计。

登记见[capabilities.yaml](capabilities.yaml)。planned仅为工具化需求，非已验证工具；真实执行前仍须按原SOP确认可用能力、输入和授权。[角色边界](Agent.md)、[知识索引](knowledge/index.md)、[证据状态](evidence/index.md)不授予额外权限。
