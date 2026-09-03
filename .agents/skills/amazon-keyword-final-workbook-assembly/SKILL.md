---
name: amazon-keyword-final-workbook-assembly
description: "Assemble the Amazon keyword project's two-object delivery: a process-artifact folder plus an eight-sheet final workbook with a three-destination 51+N master, a mechanically copied secondary-term sheet and an eligibility-filtered general library. Use for最终决策总表、二类词、通用词库、最终Sheet装配、跨板块主键质检或主任务锁定的近期词库副本换卡；do not use for reuse eligibility decisions, collection, cleaning/classification judgments, frequency calculation, data retrieval, ad decisions, Feishu or GitHub publication."
---

# Amazon Keyword Final Workbook Assembly

## 目标

锁定全部阶段产物，不改变上游判断，装配一个过程文件夹和一个八Sheet最终工作簿，并执行21项装配门。

## 输入

先锁定彼此独立的`execution_mode=fresh-collection|recent-library-reuse`与`run_type=production|test-validation`、当前SKU事实卡和新Run输出目录。

- `fresh-collection`：第一板块两Sheet工作簿；第二板块四Sheet工作簿；分类两Sheet、否词库、词频、竞争和趋势过程工作簿；全部manifests/哈希/版本及稳定Keyword_ID。
- `recent-library-reuse`：主任务冻结的`reuse-contract.json`及其外置SHA-256、当前三项输入哈希/新事实卡、源八Sheet最终工作簿及必要历史证据。完整读取[主任务复用合同](../amazon-keyword-library-operations/references/recent-library-reuse-contract.md)和本Skill直接合同的`Recent-library reuse`章节；资格由主任务锁定，本Skill不重判类目/细分，不重跑来源或分析。

production不需要qa_mode或独立QA产物；test-validation再锁定`compact-validation|full-regression`，compact封包锁定`compact-qa-result.json`及按需问题引用，full封包锁定独立QA工作簿、quality manifest、独立预览和问题文档或引用。execution_mode不改变这一路由，变更后的复用验证使用full-regression。

## 输出

1. `过程性文件/`及唯一`process-manifest.json`。
2. `<Run_ID>-最终关键词词库.xlsx`，恰好八个可见Sheet。

## 可调用能力

- `keyword.workbook.final.assemble`
- `keyword.workbook.sheet-manifest.verify`
- `keyword.workbook.delivery-privacy.audit`
- `keyword.workbook.post-qa-package.seal`
- `keyword.workbook.runtime-preflight.verify`

## 脚本路由

- 候选装配冻结前运行`node scripts/normalize-module-metadata.mjs --delivery-root <delivery>`：只改进入交付的结构化JSON副本，覆盖前三个过程分区内每个模块的manifest、handoff和verification，把含任务ID或机器绝对路径的文件引用重写为包内稳定相对路径；无法唯一映射时阻断。非JSON元数据由独立隐私审计零容忍兜底，不得带入不安全路径。不得修改上游原件。
- `scripts/post-qa-package.mjs`只用于`run_type=test-validation`。QA后先运行`node scripts/post-qa-package.mjs prepare --delivery-root <delivery> --quarantine-dir <delivery外目录> --qa-mode <compact-validation|full-regression>`，把装配阶段遗留的QA占位和重复检查/预览移出两对象交付并保留可恢复副本。production不得调用该脚本，也不得伪造QA产物。
- 再运行`node scripts/delivery-privacy-audit.mjs --delivery-root <delivery> --report <delivery外报告.json>`。该独立报告不得进入交付。
- test-validation的隐私报告通过后运行`node scripts/post-qa-package.mjs seal --delivery-root <delivery> --privacy-report <delivery外报告.json> --qa-mode <mode>`；质量任务最后只读运行同脚本的`verify-final`，不得再写文件。production由装配任务核对同一隐私报告与包内指纹后一次性写最终process manifest，Gate 21写`not_applicable`。脚本不支持锁定mode时不得绕过，必须阻断并修复检查器后再运行。
- 变更本Skill时运行`node scripts/run-fixtures.mjs`；fixture只在系统临时目录生成并清理测试包。
- 仅`fresh-collection`及其同Run精确stage-key续跑在装配前运行仓库级`scripts/runtime_contract.py verify/ready`，锁定全部上游stage key、输出/证据哈希、人口和状态。`recent-library-reuse`按独立复用合同逐项核对source/current双锁，不调用该全采集图强求ready，不伪造当前上游completed，也不放宽旧脚本。两种预检均不替代重载、风险人口复核、渲染或21项Gate。

## 执行步骤

1. 读取知识、判断边界和`references/workbook-contract.md`，按execution_mode验证run contract或独立reuse contract，锁定run_type、适用输入/来源身份、名称、哈希、版本、人口和状态。任何适用stage key、合同、输入/证据、规则文件哈希或人口漂移都在写入前阻断并回主任务重锁。未明确为测试、回归、能力案例或P1评估时run_type为`production`；只有`test-validation`才锁定qa_mode并路由独立质量验证。步骤3、5–7为fresh-collection作者流程；复用分支改按直接合同另存源工作簿，只替换步骤4的新事实卡及明确列出的交付身份/血缘字段，并比较其余七Sheet等值，随后执行共同检查。
2. 建立过程目录四分区，把真实过程工作簿、manifests、原始证据、计算、渲染和检查写入相对路径清单；排除缓存、依赖、临时脚本、重复副本、凭据、账号、任务ID和绝对路径。对前三分区所有模块元数据副本统一执行稳定相对路径重写，并分别记录上游原件哈希与交付副本哈希。复用时隔离标记历史source证据与当前输入/换卡说明；源文件只读，源QA不得放入新Run质量目录冒充当前QA。
3. 以第一板块机械去重全人口建立`最终关键词决策总表`。合并Sheet2/3/4唯一去向、分类、竞争摘要、趋势摘要、否词状态和版本；每个Keyword_ID一行。
4. 从当前锁定输入生成四列`SKU事实卡`，不复制标题和五点全文。复用时完整替换旧卡，当前缺失事实保留缺失，不用旧卡补空；不得全工作簿替换历史品牌关键词或ASIN。
5. 只从总表中同时满足`最终去向=品类相关`且`通用词库资格=纳入`的行生成`品类产品通用词库`流量层与动态语义三列块，不重新判断。上半区五个流量块的显示表头依次为`F1 核心大词、F2 二级词、F3 中流量词、F4 中长尾词、F5 长尾词`；只改显示表头，不改内部F1–F5值、阈值或人口。`不纳入/待复核`零混入。
6. 从分类完成的`Sheet4_二类词`机械复制全人口生成最终`二类词`Sheet，固定保留上游十二列和分类四列共十六列；每个主键一行，零人口只保留表头。不得从总表或原始词池重筛、重判、增删或改值。
7. 原样接入固定十二列竞争Sheet、单Sheet趋势、两表词频和五列否词库；只调整最终Sheet名称与视觉，不改变值。
8. 最终工作簿只保留八个可见Sheet并按合同顺序排列；除面向使用的`二类词`机械视图外，其他过程表只在过程目录。
9. 生成候选process manifest，记录execution_mode、run_type、适用run/reuse contract SHA-256、各适用stage身份/输出与证据哈希、相对文件清单、模块版本、人口、Sheet尺寸、公式/图表/渲染和21项门；test-validation另记录qa_mode。复用按直接合同分别记录source状态与current锁，未执行上游为`execution=not_executed、data_origin=historical_reuse`，不虚构stage key或ready/completed。真实本机合同和stage status不带入账号/任务ID/绝对路径。完整传递三种行级数据状态的计数、主键和原始值。test-validation候选Gate 21为`pending_quality_validation`；production候选Gate 21为`not_applicable`并注明`production_run_no_independent_qa`。
10. 两种run_type都由装配任务执行Gate 1–20的机械装配门、公式/外链/宏/主键/表名检查、完整风险人口生成与逐行语义复核，并只生成一套八Sheet渲染和`render-manifest.json`；风险集合不得抽样或截断。复用不重判业务，逐行核对源判断一致性及与当前事实的兼容性；品牌授权裁决或旧SKU专属理由冲突回主任务，不在装配改值。Gate 2/10/19分别核对历史source与当前fact/output锁。production的`04_独立质量验证/`只允许装配任务生成`independent-qa-not-applicable.json`，记录run_type、原因、21个Gate状态及`p1=false`，不得写QA pass。
11. production不调度独立质量验证副任务。装配任务执行文本、路径、XLSX业务字符串和OOXML结构隐私审计，重算最终工作簿锁与所有过程文件哈希；Gate 1–20全部适用硬门通过且Gate 21为`not_applicable`后，最终process manifest排除自身并只写一次。无允许缺口时交付`completed`，只有准确记录的允许缺口时交付`completed_with_gaps`；两者均记录`independent_qa=not_applicable`和`p1=false`。
12. test-validation把锁定候选交给模式对应质量验证。compact-validation只接收最小锁、21项机械结果、风险人口、八Sheet工作簿和render manifest，并只生成`compact-qa-result.json`及按需问题引用；full生成一次性完整质量工作簿、quality manifest和独立预览。两种测试模式都不得生成装配manifest、handoff、verification或重复上游工作簿。
13. test-validation在QA返回后执行最终封包：清理装配占位和重复检查，核对mode对应质量目录白名单，执行隐私审计，重算最终工作簿锁与所有过程文件哈希。最终process manifest排除自身，其他文件冻结后只写一次；未列入文件必须为零。质量任务只读复核最终封包Gate 19–21且不再写文件。全部适用硬门通过时主任务在包外标记`completed`或`completed_with_gaps`。本次规则同步本身仍不产生P1。

## 质量标准

- 顶层恰好两个对象，过程目录与最终XLSX各司其职。
- 总表人口等于第一板块词池，三去向全量、主键唯一、固定51列+N动态列，并完整传递通用词库资格。
- `二类词`Sheet人口、主键、十六列和值与分类Sheet4机械一致，零人口合法且只保留表头；不含Top3、动态语义列、竞争、趋势或广告字段。
- 通用词库可由总表的品类相关且资格纳入行机械复算；竞争、趋势和词频只含资格纳入的适用人口，否词人口符合范围。
- 通用词库五个流量块显示表头与合同一致；内部F1–F5编码、阈值和行人口未因表头改写。
- 最终工作簿恰好八个可见Sheet且顺序固定，无隐藏过程Sheet。
- 质量目录严格匹配run_type白名单：production只含`independent-qa-not-applicable.json`且不得出现QA结论；test-validation的compact-validation无质量工作簿和重复预览，full保留完整不可变质量产物。装配占位、装配manifest/handoff/verification及重复checks/previews零残留。
- 真实Codex task/thread UUID和机器绝对路径在文件名、文本、XLSX业务字符串或非许可OOXML结构中零命中；普通64位SHA-256不因含`01a`被误报，Office内部GUID只按精确结构位置许可。
- 最终process manifest列全所有过程文件且哈希闭合，只排除自身；最终工作簿另行锁哈希，未列入文件为零，不建立自哈希或循环写入。
- 业务工作簿只在对应模式预检闭合后开始单次作者写入；写入后仍完整执行重载、公式、图表、八Sheet渲染、隐私、人口和Gate验证，不能因“单次写入”减少检查。复用只写新Run副本，七个非事实Sheet通过源值等值检查，封口前再次核对原始输出0至30天期限；复制、换卡或连用不刷新期限。
- process manifest和21项门完整。production在Gate 1–20通过、Gate 21为`not_applicable`且隐私/哈希闭合后可完成；test-validation在模式对应质量验证只读复核最终封包增量前不完成。
- Skill保持draft/planned，旧工作簿不冒充当前合同P1。

## 异常处理

上游哈希/版本/人口/通用词库资格不闭合、风险人口不完整、动态列不一致、二类词Sheet与分类Sheet4不一致、最终Sheet或顶层对象不符、外链/宏/公式错误、过程文件缺失、隐私扫描命中、模块路径不能唯一重写、run_type白名单不符或process manifest漏列/错哈希时阻断交付；test-validation还在QA失败或最终封包增量复核失败时阻断。production若出现QA产物、QA pass或Gate 21非`not_applicable`同样阻断。三种行级数据状态本身不阻断；准确传递时自动形成`completed_with_gaps`，不等待用户确认。本Skill不重算上游业务结果，不补拉数据，不生成广告判断。

复用资格未知、过期或类目/条件式细分不符时只拒绝复用入口，回主任务走正常流程，不新增逐Run授权门；源已知错误、业务不兼容、七Sheet非白名单差异或新旧事实混用时停止换卡并回传。旧revision不同本身不是不兼容，历史品牌文本也不自行构成污染；历史缺口/QA取消不因复用升级为通过或P1。
