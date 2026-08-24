---
name: amazon-keyword-quality-validation
description: Independently validate a locked Amazon keyword-library run across sources, cleaning, classification, analysis, process artifacts and the eight-sheet final workbook. Use for跨阶段主键人口、二类词Sheet、版本、公式、渲染、图表和21项完成门；do not use to fix files, rerun sources, change rules or publish externally.
---

# Amazon Keyword Quality Validation

## 目标

对锁定Run执行独立只读验收，验证全链路、两个顶层对象、八Sheet最终工作簿和21项装配门，输出可追溯结论而不修复上游。

## 输入

Run_ID、仓库revision、站点、全部模块版本、过程文件夹、最终工作簿、process manifest、上游manifests、唯一问题文档和获准质量目录。

## 输出

- `独立质量验证.xlsx`：固定两个Sheet。
- `quality-manifest.json`。
- 最终八Sheet必要预览和同一问题文档引用。
- QA结论`pass/blocked/incomplete`和交付状态。

## 可调用能力

- `keyword.quality.validate`

## 执行步骤

1. 读取知识、判断边界和`references/quality-contract.md`；锁定Run/revision、版本、哈希和产物清单。
2. 只读验证三来源状态、获准入口类型与回退证据、第一板块两Sheet、机械词池和损失风险。
3. 验证第二板块四Sheet、三去向、主键、理由和人口闭环；核对一级品类核心大词、可选细分核心词、主执行锚点、强等价表达、宽泛/相邻流量词及单一卖家精灵种子没有混层，并核对Sheet2通用词库资格、配置/并列连接、其他语言词序已整批按中心购买对象执行且有Sheet2误放、Sheet3误摘和资格误纳反向抽查。
4. 验证分类两Sheet、N动态列、F1–F5、F5主分组/LT和五列否词库；核对`关键词ABA排名缺失、搜索量缺失、没有搜索量`的状态、原始值和派生留空是否符合合同。
5. 验证词频、竞争和趋势均只使用`通用词库资格=纳入`的适用人口，再验证词频固定介词删除/断点、竞争十二列与Top3矩阵、趋势来源优先级/单一提供商、24月/两矩阵/两张实际搜索量图。
6. 验证最终总表三去向51+N、SKU事实、通用词库按品类相关且资格纳入机械筛选、五个流量块显示表头、最终`二类词`与分类Sheet4人口/十六列/主键/值一致、独立四个分析Sheet及八Sheet顺序。
7. 执行过程文件哈希/敏感信息检查和21项装配门；每个失败Gate引用唯一问题文档中的同一根因问题ID。
8. 为最终八Sheet各生成至少一个可复核预览；趋势图单独核对序列和范围。
9. 写入两Sheet质量工作簿和最小quality manifest。对三种行级数据状态生成一份去重后用户确认清单并回传主任务；用户确认未闭合时结论为`incomplete`，不写`blocked`。若用户要求改值，返回分类拥有副任务后重新装配和QA；质量任务不直接修改。硬门失败不得输出pass。

## 质量标准

- 全程只读，不调用业务外部系统、不重跑、不修改上游、不改规则。
- Gate状态只用`pass/fail/not_executed/not_applicable`。
- 锚点语义审计覆盖全部一级品类核心大词、细分核心词、强等价表达和卖家精灵种子，并对SIF候选摘要头部词及最终通用词库高流量词做有界反向抽查；流量、竞品排名或营销用途不能单独通过核心层级或通用词库资格门。
- 合同允许缺口可为QA pass且交付completed_with_gaps；硬门失败只能blocked/incomplete。
- 三种行级数据状态不是分类整批停止门；未得到用户最终确认前QA为`incomplete`，用户接受其实际状态后可作为合同允许缺口评估。
- 同一根因只在唯一问题文档记录一次，多个Gate复用问题ID。
- 质量目录不复制接口正文、整张关键词表或上游工作簿。
- Skill保持draft/planned，P0不冒充P1。

## 异常处理

缺少revision、manifest、必需产物、哈希、锚点/种子层级、通用词库资格人口、二类词Sheet闭环或预览时结论`incomplete`。已执行检查发现硬门失败为`blocked`。只有待用户确认的`关键词ABA排名缺失、搜索量缺失、没有搜索量`时结论为`incomplete`而不是`blocked`。质量任务只报告所有者和建议下一步，不直接修复。
