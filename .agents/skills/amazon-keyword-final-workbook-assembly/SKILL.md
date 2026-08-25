---
name: amazon-keyword-final-workbook-assembly
description: "Assemble the Amazon keyword project's two-object delivery: a process-artifact folder plus an eight-sheet final workbook with a three-destination 51+N master, a mechanically copied secondary-term sheet and an eligibility-filtered general library. Use for最终决策总表、二类词、通用词库、最终Sheet装配或跨板块主键质检；do not use for collection, cleaning/classification judgments, frequency calculation, data retrieval, ad decisions, Feishu or GitHub publication."
---

# Amazon Keyword Final Workbook Assembly

## 目标

锁定全部阶段产物，不改变上游判断，装配一个过程文件夹和一个八Sheet最终工作簿，并执行21项装配门。

## 输入

第一板块两Sheet工作簿；第二板块四Sheet工作簿；分类两Sheet、否词库、词频、竞争和趋势过程工作簿；全部manifests/哈希/版本；稳定Keyword_ID；锁定SKU事实卡和输出目录。QA后封包还必须锁定独立QA工作簿、quality manifest、独立预览和唯一问题文档或引用。

## 输出

1. `过程性文件/`及唯一`process-manifest.json`。
2. `<Run_ID>-最终关键词词库.xlsx`，恰好八个可见Sheet。

## 可调用能力

- `keyword.workbook.final.assemble`
- `keyword.workbook.sheet-manifest.verify`
- `keyword.workbook.delivery-privacy.audit`
- `keyword.workbook.post-qa-package.seal`

## 脚本路由

- 候选装配冻结前运行`node scripts/normalize-module-metadata.mjs --delivery-root <delivery>`：只改进入交付的结构化JSON副本，覆盖前三个过程分区内每个模块的manifest、handoff和verification，把含任务ID或机器绝对路径的文件引用重写为包内稳定相对路径；无法唯一映射时阻断。非JSON元数据由独立隐私审计零容忍兜底，不得带入不安全路径。不得修改上游原件。
- QA后先运行`node scripts/post-qa-package.mjs prepare --delivery-root <delivery> --quarantine-dir <delivery外目录>`，把装配阶段遗留的QA占位和重复检查/预览移出两对象交付并保留可恢复副本。
- 再运行`node scripts/delivery-privacy-audit.mjs --delivery-root <delivery> --report <delivery外报告.json>`。该独立报告不得进入交付。
- 隐私报告通过后运行`node scripts/post-qa-package.mjs seal --delivery-root <delivery> --privacy-report <delivery外报告.json>`；独立QA最后只读运行同脚本的`verify-final`，不得再写文件。
- 变更本Skill时运行`node scripts/run-fixtures.mjs`；fixture只在系统临时目录生成并清理测试包。

## 执行步骤

1. 读取知识、判断边界和`references/workbook-contract.md`，锁定全部上游名称、哈希、版本、人口和适用状态。
2. 建立过程目录四分区，把真实过程工作簿、manifests、原始证据、计算、渲染和检查写入相对路径清单；排除缓存、依赖、临时脚本、重复副本、凭据、账号、任务ID和绝对路径。对前三分区所有模块元数据副本统一执行稳定相对路径重写，并分别记录上游原件哈希与交付副本哈希。
3. 以第一板块机械去重全人口建立`最终关键词决策总表`。合并Sheet2/3/4唯一去向、分类、竞争摘要、趋势摘要、否词状态和版本；每个Keyword_ID一行。
4. 从锁定SKU事实卡生成`SKU事实卡`，不复制标题和五点全文。
5. 只从总表中同时满足`最终去向=品类相关`且`通用词库资格=纳入`的行生成`品类产品通用词库`流量层与动态语义三列块，不重新判断。上半区五个流量块的显示表头依次为`F1 核心大词、F2 二级词、F3 中流量词、F4 中长尾词、F5 长尾词`；只改显示表头，不改内部F1–F5值、阈值或人口。`不纳入/待复核`零混入。
6. 从分类完成的`Sheet4_二类词`机械复制全人口生成最终`二类词`Sheet，固定保留上游十二列和分类四列共十六列；每个主键一行，零人口只保留表头。不得从总表或原始词池重筛、重判、增删或改值。
7. 原样接入固定十二列竞争Sheet、单Sheet趋势、两表词频和五列否词库；只调整最终Sheet名称与视觉，不改变值。
8. 最终工作簿只保留八个可见Sheet并按合同顺序排列；除面向使用的`二类词`机械视图外，其他过程表只在过程目录。
9. 生成候选process manifest，记录相对文件清单、SHA-256、模块版本、人口、Sheet尺寸、公式/图表/渲染和21项门；完整传递分类manifest中`关键词ABA排名缺失、搜索量缺失、没有搜索量`的计数、主键和原始值。候选阶段Gate 21只能为`pending_independent_QA`。
10. 执行21项装配门、公式扫描、外链/宏/主键/表名检查，并渲染八Sheet目视复核。
11. 把锁定候选交给独立质量验证。独立QA只生成一次不可变最小集合：`独立质量验证.xlsx`、`quality-manifest.json`、`independent-qa-previews/`，以及`issues.md`或`issue-reference.json`二选一；不得生成装配manifest、handoff、verification、占位状态或重复预览。
12. QA返回后由装配任务执行最终封包：清除自己的QA占位/重复检查与预览，核对固定质量目录白名单，执行文本、路径、XLSX业务字符串和OOXML结构隐私审计，重算最终工作簿锁与所有过程文件哈希。最终process manifest排除自身，其他文件全部冻结后只写一次；未列入文件必须为零。
13. 最终封包状态保持`incomplete`、Gate 21保持`pending_post_packaging_QA`、P1为false。独立QA仅只读复核最终封包增量且不再写文件；其复核结论由主任务在包外接收，避免为记录结论而再次改变被验证对象。

## 质量标准

- 顶层恰好两个对象，过程目录与最终XLSX各司其职。
- 总表人口等于第一板块词池，三去向全量、主键唯一、固定51列+N动态列，并完整传递通用词库资格。
- `二类词`Sheet人口、主键、十六列和值与分类Sheet4机械一致，零人口合法且只保留表头；不含Top3、动态语义列、竞争、趋势或广告字段。
- 通用词库可由总表的品类相关且资格纳入行机械复算；竞争、趋势和词频只含资格纳入的适用人口，否词人口符合范围。
- 通用词库五个流量块显示表头与合同一致；内部F1–F5编码、阈值和行人口未因表头改写。
- 最终工作簿恰好八个可见Sheet且顺序固定，无隐藏过程Sheet。
- QA后质量目录严格匹配固定白名单；装配占位、装配manifest/handoff/verification、装配checks/previews零残留。
- 真实Codex task/thread UUID和机器绝对路径在文件名、文本、XLSX业务字符串或非许可OOXML结构中零命中；普通64位SHA-256不因含`01a`被误报，Office内部GUID只按精确结构位置许可。
- 最终process manifest列全所有过程文件且哈希闭合，只排除自身；最终工作簿另行锁哈希，未列入文件为零，不建立自哈希或循环写入。
- process manifest和21项门完整，独立QA未只读复核最终封包增量前不完成。
- Skill保持draft/planned，旧工作簿不冒充当前合同P1。

## 异常处理

上游哈希/版本/人口/通用词库资格不闭合、动态列不一致、二类词Sheet与分类Sheet4不一致、最终Sheet或顶层对象不符、外链/宏/公式错误、过程文件缺失、QA失败、隐私扫描命中、模块路径不能唯一重写、质量白名单不符、process manifest漏列/错哈希或最终封包增量复核失败时阻断交付。`关键词ABA排名缺失、搜索量缺失、没有搜索量`本身不阻断候选工作簿装配，但必须带入最终QA用户确认清单；确认未闭合时不得标记完成。本Skill不重算上游业务结果，不补拉数据，不生成广告判断。
