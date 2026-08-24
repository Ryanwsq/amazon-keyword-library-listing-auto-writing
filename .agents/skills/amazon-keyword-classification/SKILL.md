---
name: amazon-keyword-classification
description: Classify locked Amazon Sheet2 and Sheet4 keywords by confirmed ABA traffic layers and adaptive semantic columns, then build a minimal semantic negative library. Use for第三板块F1-F5分层、LT分组、动态词性词义多列、二类词分类或否词库；do not use for source collection, category cleaning, word frequency, competition/trend, SKU matching, negative match types or ad eligibility.
---

# Amazon Keyword Classification

## 目标

不改变第二板块三去向，增强Sheet2和Sheet4的流量/语义结构，并从合格Sheet3行生成最小否词库。

## 输入

锁定的第二板块四Sheet、哈希、Sheet2/3/4人口、Keyword_ID、ABA/搜索量、品类关系、通用词库资格、站点、周期、分类版本和输出目录。SKU事实卡不是分类输入；上游资格只原样传递。

## 输出

- 只含增强`Sheet2_品类相关`和`Sheet4_二类词`的分类过程工作簿。
- 五列`否词库`过程工作簿或同模块最小输出。
- 分类manifest和紧凑状态。

## 可调用能力

- `keyword.library.classify`
- `keyword.classification.sheet2.apply`
- `keyword.classification.sheet4.apply`
- `keyword.classification.negative-library.build`
- `keyword.classification.outputs.write-and-verify`

## 执行步骤

1. 读取知识、判断边界和`references/output-contract.md`，锁定第二板块版本、三去向人口、主键和分类版本；不读取SKU事实卡。
2. 复制Sheet2和Sheet4为新过程工作簿，不覆盖第二板块原表，不改变行数、去向、原词、指标或理由。
3. 按ABA应用互斥F1–F5：1–10k、10–20k、20–50k、50–100k、>100k。ABA排名未抓取到或不可用时，流量层、主分组和LT留空，分类状态写`关键词ABA排名缺失`；不根据搜索量反推ABA或流量层。
4. 为Sheet2完整保留原十四列及`通用词库资格`，再追加`流量层、长尾主分组标签、LT分组、分类状态`。
5. 根据当前一级品类、完整Sheet2人口和关键词自身语义设计N个动态语义列。只保留至少一行有值的列；同一列多值用`｜`；不生成重复多标签汇总列。
6. 只有F5填写主分组和LT。每词选择一个`列名:标签值`且只出现一次；组内ABA升序，每20词拆一个LT组。
7. Sheet4保留原十二列并只追加同样四个固定列；不增加完整动态语义列，不重判二类身份，不进入竞争或趋势。
8. 月搜索量未抓取到或为空时，分类状态记`搜索量缺失`；来源明确返回无搜索量或数值为0时记`没有搜索量`。只要ABA有效，仍按ABA完成F1–F5及适用的F5分组；不因这三类行级数据状态停止整批。
9. 从Sheet3筛选语义明确、复核完成且符合否词收录边界的原始完整关键词，生成五列否词库。流量失败/缺失、歧义和待复核词不自动收录。
10. 验证人口、主键、上游品类关系/通用词库资格逐值不变、F1–F5、动态列清单/顺序、F5唯一主分组、LT<=20、否词来源和禁止字段；把`关键词ABA排名缺失、搜索量缺失、没有搜索量`的受影响主键及原始值写入manifest和唯一问题文档，供最终装配后质检确认；渲染所有输出Sheet。

## 质量标准

- Sheet2和Sheet4人口分别等于上游，三去向身份、品类关系和通用词库资格不变。
- 动态列品类自适应、非空且仅由词面支持；无SKU匹配或广告字段。
- F5每词一次、一个主分组、每LT最多20词。
- 三种数据缺口使用精确状态`关键词ABA排名缺失、搜索量缺失、没有搜索量`；不填0、不反推、不伪造派生值。
- Sheet4仅追加四列且无竞争/趋势。
- 否词库只有五列，无否定方式、生成短语或待复核词。
- Skill保持draft/planned；未通过真实三案例不称verified。

## 异常处理

主键/人口/版本无法锁定，或Sheet2品类关系/通用词库资格缺失、非法、与上游不一致时停止。`关键词ABA排名缺失、搜索量缺失、没有搜索量`只是行级数据状态，不停止分类批次；受影响派生字段留空，候选工作簿可继续装配，但用户确认未闭合前最终QA必须为`incomplete`。否词语义或复核状态不满足时保留在Sheet3，不强行收录。
