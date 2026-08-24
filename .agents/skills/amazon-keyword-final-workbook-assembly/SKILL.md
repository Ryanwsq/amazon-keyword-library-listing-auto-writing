---
name: amazon-keyword-final-workbook-assembly
description: "Assemble the Amazon keyword project's two-object delivery: a process-artifact folder plus an eight-sheet final workbook with a three-destination 51+N master, a mechanically copied secondary-term sheet and an eligibility-filtered general library. Use for最终决策总表、二类词、通用词库、最终Sheet装配或跨板块主键质检；do not use for collection, cleaning/classification judgments, frequency calculation, data retrieval, ad decisions, Feishu or GitHub publication."
---

# Amazon Keyword Final Workbook Assembly

## 目标

锁定全部阶段产物，不改变上游判断，装配一个过程文件夹和一个八Sheet最终工作簿，并执行21项装配门。

## 输入

第一板块两Sheet工作簿；第二板块四Sheet工作簿；分类两Sheet、否词库、词频、竞争和趋势过程工作簿；全部manifests/哈希/版本；稳定Keyword_ID；锁定SKU事实卡和输出目录。

## 输出

1. `过程性文件/`及唯一`process-manifest.json`。
2. `<Run_ID>-最终关键词词库.xlsx`，恰好八个可见Sheet。

## 可调用能力

- `keyword.workbook.final.assemble`
- `keyword.workbook.sheet-manifest.verify`

## 执行步骤

1. 读取知识、判断边界和`references/workbook-contract.md`，锁定全部上游名称、哈希、版本、人口和适用状态。
2. 建立过程目录四分区，把真实过程工作簿、manifests、原始证据、计算、渲染、检查、唯一问题文档和QA位置写入相对路径清单；排除缓存、依赖、临时脚本、重复副本、凭据、任务ID和绝对路径。
3. 以第一板块机械去重全人口建立`最终关键词决策总表`。合并Sheet2/3/4唯一去向、分类、竞争摘要、趋势摘要、否词状态和版本；每个Keyword_ID一行。
4. 从锁定SKU事实卡生成`SKU事实卡`，不复制标题和五点全文。
5. 只从总表中同时满足`最终去向=品类相关`且`通用词库资格=纳入`的行生成`品类产品通用词库`流量层与动态语义三列块，不重新判断。`不纳入/待复核`零混入。
6. 从分类完成的`Sheet4_二类词`机械复制全人口生成最终`二类词`Sheet，固定保留上游十二列和分类四列共十六列；每个主键一行，零人口只保留表头。不得从总表或原始词池重筛、重判、增删或改值。
7. 原样接入固定十二列竞争Sheet、单Sheet趋势、两表词频和五列否词库；只调整最终Sheet名称与视觉，不改变值。
8. 最终工作簿只保留八个可见Sheet并按合同顺序排列；除面向使用的`二类词`机械视图外，其他过程表只在过程目录。
9. 生成唯一process manifest，记录相对文件清单、SHA-256、模块版本、人口、Sheet尺寸、公式/图表/渲染和21项门。
10. 执行21项装配门、公式扫描、外链/宏/主键/表名检查，并渲染八Sheet目视复核。
11. 把锁定两个对象交给独立质量验证；QA未通过时不得标记完成。

## 质量标准

- 顶层恰好两个对象，过程目录与最终XLSX各司其职。
- 总表人口等于第一板块词池，三去向全量、主键唯一、固定51列+N动态列，并完整传递通用词库资格。
- `二类词`Sheet人口、主键、十六列和值与分类Sheet4机械一致，零人口合法且只保留表头；不含Top3、动态语义列、竞争、趋势或广告字段。
- 通用词库可由总表的品类相关且资格纳入行机械复算；竞争、趋势和词频只含资格纳入的适用人口，否词人口符合范围。
- 最终工作簿恰好八个可见Sheet且顺序固定，无隐藏过程Sheet。
- process manifest和21项门完整，独立QA未通过不完成。
- Skill保持draft/planned，旧工作簿不冒充当前合同P1。

## 异常处理

上游哈希/版本/人口/通用词库资格不闭合、动态列不一致、二类词Sheet与分类Sheet4不一致、最终Sheet或顶层对象不符、外链/宏/公式错误、过程文件缺失或QA失败时阻断交付。本Skill不重算上游业务结果，不补拉数据，不生成广告判断。
