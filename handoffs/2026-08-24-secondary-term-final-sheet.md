# 2026-08-24 final secondary-term sheet handoff

- Status: user-confirmed contract synchronized; P1 pending
- Sharing: sanitized
- Cleaning baseline: V2.1
- Word-frequency component: V2.2
- Skill maturity: all twelve remain draft/planned

## Scope

用户确认最终工作簿增加独立`二类词`Sheet，并明确这里的二类词是第二板块`Sheet4_二类词`中的直接替代完整商品，不是F2二级流量词。本次只调整最终装配、质量验证和人类可读合同，不改变二类词定义、V2.1三去向、流量门、分类或下游分析范围。

## Confirmed contract

- 最终工作簿由七个可见Sheet调整为八个，顺序固定为`最终关键词决策总表、SKU事实卡、品类产品通用词库、二类词、关键词竞争性分析、关键词趋势性分析、词频统计、否词库`。
- 最终`二类词`Sheet机械复制分类完成的`Sheet4_二类词`全人口；每个`Keyword_ID`恰好一行，零人口时只保留表头。
- 字段固定为第二板块十二列加分类四列，共十六列；不加入Top3、动态语义列、竞争、趋势、通用词库资格、否词方式、广告资格或投放动作。
- 最终装配不得新增、删除、重判二类词或改变上游值。最终总表仍覆盖三去向51+N全人口，过程目录仍保留原Sheet4；新增Sheet只是独立使用视图，不建立第四去向。
- 两个顶层交付对象和21项门总数不变。Gate 6增加二类词人口/字段/主键/值闭环，Gate 16与18改验八Sheet顺序和渲染。

## Status boundary

- 修改前的七Sheet工作簿只作旧合同运行证据，不代表当前装配合同。
- 本次规则、Skill和P0同步不生成P1证据；必须按八Sheet合同重新装配并通过独立只读QA后，才可形成当前合同候选证据。
- 广告否定方式、广告资格和投放动作仍为后置开放项。

## Next gate

在锁定的新Run或获准重跑中，使用当前revision完成八Sheet装配，验证最终`二类词`Sheet与分类Sheet4人口、十六列、主键和值一致，并完成八Sheet全部渲染及21项独立QA。
