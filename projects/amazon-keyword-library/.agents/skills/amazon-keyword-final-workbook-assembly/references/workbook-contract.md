# Final delivery and workbook contract

## Top-level delivery

顶层恰好两个对象：

1. `过程性文件/`
2. `<Run_ID>-最终关键词词库.xlsx`

过程目录固定：

- `01_第一板块_来源采集/`
- `02_第二板块_品类清洗/`
- `03_第三板块_分类与分析/`
- `04_独立质量验证/`
- `process-manifest.json`

保存真实过程工作簿、模块manifests、原始响应、分页清单、计算、渲染、检查、唯一问题文档或引用和质量报告。禁止缓存、依赖、临时脚本、重复副本、凭据、账号、任务ID和绝对路径。

前三个分区中每个模块的manifest、handoff和verification副本都必须递归检查。结构化JSON中的文件引用统一重写为相对其元数据文件、指向同一过程分区内真实封装对象的POSIX相对路径；不能只修某一个模块或某一种元数据。非JSON元数据也必须接受最终隐私审计，存在不安全路径时重建脱敏副本或阻断。重写只发生在交付副本，不改上游原件或业务值；process manifest同时锁定上游原件哈希和重写后副本哈希。含机器路径或任务ID但无法唯一映射到包内对象时阻断，不得删字段、截短或用伪路径掩盖。

### Run-type-specific quality-directory whitelist

production Run不调用独立质量验证副任务。为保持四分区交付结构，最终`04_独立质量验证/`顶层只能包含装配任务生成的`independent-qa-not-applicable.json`；它必须记录`schema、run_type=production、reason=production_run、independent_qa_status=not_applicable、p1=false`及21个Gate状态，不得包含QA结论、质量工作簿、独立预览或伪造的QA证据。

test-validation的`compact-validation`下最终`04_独立质量验证/`顶层只能包含：

1. `compact-qa-result.json`；
2. 只有存在问题时才出现`issues.md`或`issue-reference.json`之一。

compact-validation不得包含`独立质量验证.xlsx`、`quality-manifest.json`或独立预览目录。test-validation的`full-regression`继续使用四项完整白名单：`独立质量验证.xlsx`、`quality-manifest.json`、`independent-qa-previews/`、`issues.md`或`issue-reference.json`之一。

`QA_INPUT.md、assembly-manifest.json、handoff.json、verification.json、independent-qa-status.json、checks/、previews/`均为装配阶段对象，在test-validation的QA后不得留在质量目录。模式对应QA产物一经返回即不可变；最终封包不得修改compact result，或full的工作簿、quality manifest、独立预览及问题业务结论。production不产生这些独立QA对象。

兼容硬门表述：test-validation的独立QA产物一经返回即不可变；“产物”按`qa_mode`分别指compact-validation最小结果集合或full完整质量集合。历史`compact-production`只属于冻结旧Run，不再作为production路由。

### Privacy and path audit

最终封包前必须分别扫描：

- 所有相对文件路径；
- `JSON/JSONL/NDJSON/CSV/TSV/MD/TXT/XML/YAML/LOG`等文本正文及其他文件的可读元数据；
- XLSX/XLSM全部OOXML XML/rels部件，经数字实体解码后的业务单元格、共享字符串、批注和结构内容。

任意完整`8-4-4-4-12`十六进制UUID在文本、文件路径、XLSX业务字符串或非许可OOXML位置都按真实task/thread标识风险阻断；不依赖UUID版本位，也不使用泛`01a`正则。普通64位SHA-256必须单独分类并放行。Office内部GUID只允许合同脚本中绑定到精确OOXML部件的已知固定值，不能把任意UUID按“Office结构”放行。`/Users/`、`/home/`、`/Volumes/`、`/private/`、`/var/folders/`、`/tmp/`、`file:///Users/`和Windows用户/临时根等机器绝对路径全部阻断。

隐私报告必须保存在两对象交付之外，只输出分类、计数和路径/部件指纹，不回显敏感原文。装配自检必须核对该报告的零命中、内容指纹和文件人口，并以独立实现再扫文本/路径；两者不一致即阻断。test-validation再由独立QA交叉验证；production不因此伪称独立QA。

## Packaging lifecycle

production采用三阶段：

1. **候选装配**：生成八Sheet候选、四分区过程证据、唯一八Sheet渲染、21项机械结果和完整风险人口；Gate 21=`not_applicable`。
2. **装配检查与隐私**：装配任务完成Gate 1–20的机械全量检查和完整风险人口逐行语义复核，写唯一`independent-qa-not-applicable.json`，执行隐私审计并交叉核对内容指纹。
3. **直接封包**：冻结全部业务文件，重算最终工作簿和全部过程文件哈希，最后单次写入process manifest。Gate 1–20通过且Gate 21为`not_applicable`时交付可为`completed/completed_with_gaps`，但`independent_qa=not_applicable、p1=false`。

test-validation继续采用四阶段：候选装配且Gate 21=`pending_quality_validation`；compact-validation或full-regression一次性QA；装配最终封包；质量任务只读核对最终封包增量。QA不得写装配占位、装配manifest/handoff/verification或重复渲染。

process manifest不得列出或哈希自身；除自身外的过程文件必须全部列入且未列入、缺失、错哈希均为零。最终工作簿在交付身份区单独锁定相对路径、大小和SHA-256。禁止在QA产物与process manifest之间建立自哈希或互相回写循环。

## Recent-library reuse

`execution_mode=recent-library-reuse`是常规入口，独立于`run_type`及fresh-collection同Run精确stage-key续跑。执行前完整读取[主任务复用合同](../../amazon-keyword-library-operations/references/recent-library-reuse-contract.md)，只消费主任务冻结的`amazon-keyword-recent-library-reuse/v1`合同；不自行寻找历史源、重判资格或重跑来源、清洗、分类、词频、竞争、趋势。以下为本模块适配，资格与跨模块合同仍由主任务拥有。

### Dual-lock preflight

- 当前锁：新Run、execution_mode/run_type、当前revision/规则拥有文件哈希、三项输入各自SHA-256、新SKU事实卡相对指针/哈希、站点/类目/多细分回答、输出目录和装配执行器版本；test-validation另锁qa_mode及变更触发项。
- 来源锁：source Run/revision、源最终工作簿及必要manifest/判定锚点/人口/证据哈希、原始最终输出的有时区记录、数据周期/源规则版本、源缺口/质量状态；链式复用同时锁直接父本与最初来源。原始/入选/排除竞品及来源完成状态属于source，不把历史ASIN表述为本次已反查竞品；当前尚未查询的竞品仅作新输入保存，不替换历史已查询ASIN。
- 核对主任务已确认同站点、同Amazon类目。无多个稳定产品类型细分时细分核心词留空、不判断细分；有细分时必须有同一稳定类型的肯定结论与证据，未知/存在性冲突不能用空值相等放行。普通配置差异不是重跑或另建细分的理由。
- 用有时区的本次检查时间与可追溯原始最终输出时间计算`0 <= age <= 30天`，含第30天，封口前再核对。不用采集日、文件名、mtime、下载或复制时间；连续复用追溯最初输出，换卡/改名/再输出不刷新期限。资格不成立只拒绝复用入口并回主任务走正常流程，不要求逐Run再次授权。
- 核对源真实可读、八Sheet/人口/锚点/必要血缘完整及主任务兼容性结论；旧revision不同或本次规则新增入口导致哈希不同，本身不等于业务不兼容。历史入口、导出次数和执行顺序按源版本核验，不追溯套用当前新采集SOP强制重采；身份、指标口径、语义及当前输出硬门仍须无冲突，源已知错误、废弃判断或不兼容结构不得放行。
- 复用合同按主任务规定规范化并核对外置SHA-256，写入前逐项核对当前输入/新事实、所有引用源文件与规则拥有文件。任何漂移停止换卡并回主任务重锁，不静默更新。只有本入口全部通过后，复用合同才替代fresh-collection上游依赖预检；适用依赖为`reuse-eligibility -> assembly`，测试再接`quality-validation`，不伪装成全量run contract或调用旧脚本制造上游ready。

### Copy, replace facts and prove equality

在新Run输出目录另存副本，不覆盖源工作簿或历史过程证据。只全量替换四列`SKU事实卡`及必要交付身份/装配版本/血缘元数据；新卡全部来自当前锁定输入，缺失值保持缺失，不残留旧卡内容或用旧事实补空。历史卡仅作来源判定血缘，不作当前事实来源。

对其余七个Sheet逐项比较人口、Keyword_ID、原文/业务值、三去向/资格/分类、否词/词频/竞争/趋势、来源周期、源规则版本、公式与图表。允许的必要交付身份/装配版本/血缘变化必须逐字段锁定白名单并记录前后值，不允许借白名单改变业务判断、源状态或数据周期；`采集批次`不得改为新Run，“最近月/季”不得改成当前日历期间。比较覆盖全部七Sheet，非白名单差异为零，不以抽样或仅比较文件尺寸代替；重新加载/计算/换卡若改变业务结果同样阻断。

历史品牌关键词/ASIN是来源文本，不能全工作簿替换；品牌变化本身不否决复用。原自有品牌/授权裁决会被错误沿用为当前授权，或旧SKU专属理由与新事实冲突时，回主任务按既有边界选择正常流程或另行获准的有界修订；本Skill不得改语义或静默通过。风险人口复核保留全量覆盖，用于一致性与当前事实冲突核对，不重做上游判断。

前三个过程分区内将必要源证据明确标为历史来源，与当前输入/换卡说明分离；只对交付副本做已有脱敏/相对路径处理并分别锁原件与副本哈希。源质量材料仅作历史证据，不进入新Run质量目录，不冒充当前QA。保留原质量状态、允许缺口及行级缺失主键/计数/原值；未执行上游记录`execution=not_executed、data_origin=historical_reuse`，另存source原状态，不生成当前completed/stage key或模块案例。

当前process manifest另列复用合同哈希、source双层血缘/原始输出时间及证据、入口与封口age/资格核对、source状态/版本/周期、当前三项输入/新事实卡哈希、字段白名单/前后值、七Sheet等值结果及新输出哈希；源锁与current锁不能互相覆盖。八Sheet、两对象、Gate 1–20与全部重载/公式/图表/渲染/隐私/哈希检查不减。历史QA、人工接受和30天资格都不替代当前QA；Gate 21仍按本次run_type路由，变更后的复用测试使用full-regression。取消/未执行不改写为通过，当前状态仅据本次适用检查，`p1=false`。

## Final workbook sheets

恰好八个可见Sheet，顺序固定：

1. `最终关键词决策总表`
2. `SKU事实卡`
3. `品类产品通用词库`
4. `二类词`
5. `关键词竞争性分析`
6. `关键词趋势性分析`
7. `词频统计`
8. `否词库`

第二板块原始三去向过程表继续留在过程目录；最终`二类词`只作为分类完成的Sheet4机械视图进入最终工作簿，其他过程表不进入。

## Final decision master population

人口等于第一板块机械去重唯一关键词数。每个Keyword_ID恰好一行，`最终去向`只用`品类相关、其他摘除、二类词`。三去向不交叉、不遗漏。

### Fixed 51 fields plus N semantic columns

1. 身份/来源/版本18列：`Keyword_ID、英文关键词、中文翻译、标准化关键词、站点、采集批次、来源数据周期、来源规则版本、清洗规则版本、分类规则版本、竞争规则版本、趋势规则版本、装配规则版本、关键词来源、流量数据来源、ABA月排名、月搜索量、来源数据状态`。
2. 三去向/清洗12列：`最终去向、流量门状态、中心购买对象、品类关系、通用词库资格、保留理由、摘除主类型、摘除理由、清洗复核状态、二类商品类型、共同核心购买任务、直接替代理由`。
3. 分类4列：`流量层、长尾主分组标签、LT分组、分类状态`，其后插入N个分类输出动态语义列。
4. 竞争2列：`竞争性强度、竞争数据状态`。
5. 趋势9列：`最近完整月、最近月搜索量、月环比、月同比、最近完整季度、季度搜索量、季度环比、季度同比、趋势数据状态`。
6. 否词/广告5列：`否词库状态、否词类别、否词收录理由、广告资格、投放动作`。
7. 最终质量1列：`最终复核状态`。

标准化关键词只执行NFKC、小写、trim和压缩空格。详细Top3、点击/转化层、差值和结构不进入总表；只在竞争Sheet。广告资格和投放动作当前统一`未评估/后置`。

品类相关行填写品类关系、通用词库资格、保留理由和适用分类；只有资格为`纳入`的品类相关行才进入竞争、趋势和词频适用人口。其他摘除行填写摘除与否词状态；二类词行填写替代关系和适用流量分类。不适用字段留空或写合同规定范围状态，不伪造数值。

## SKU fact sheet

四列：`事实分类、事实字段、确认值、状态/来源`。内容与锁定事实卡一致，不复制标题、五点或长描述全文。

## General category keyword library

唯一数据源为最终总表中同时满足`最终去向=品类相关`且`通用词库资格=纳入`的行。`品类相关`不自动等于通用词库入选；`不纳入/待复核`不得进入任何块。

每个分类建立三列块：`关键词、月搜索量、竞争性强度`。上半区依次放F1–F5五个流量层块，共15列，显示表头依次为`F1 核心大词、F2 二级词、F3 中流量词、F4 中长尾词、F5 长尾词`。这只是最终通用词库的显示表头，最终总表和分类过程的`流量层`仍只用F1–F5，ABA阈值、人口和下游范围不变。下半区按最终总表动态语义列顺序展开`语义维度:标签值`块，每行横向四块；空块不输出。

多标签关键词可进入多个块，同块内唯一。块内按月搜索量降序、ABA升序、英文关键词字符升序；缺搜索量最后。ABA只作隐藏排序依据。F5竞争性强度写`不适用（F5）`。不显示Keyword_ID、翻译、ABA、来源、周期、标签说明或理由。

## Secondary-term sheet

唯一数据源是分类完成的`Sheet4_二类词`，人口机械等于最终总表中`最终去向=二类词`的人口。每个`Keyword_ID`恰好一行；上游零行时保留表头，不将零人口误报为缺失。

固定十六列并按此顺序：`Keyword_ID、英文关键词、中文翻译、ABA月排名、月搜索量、关键词来源、流量数据来源、数据状态、中心购买对象、二类商品类型、共同核心购买任务、直接替代理由、流量层、长尾主分组标签、LT分组、分类状态`。

装配只复制上游原值并调整视觉，不新增、删除、重判或改写二类词。不得加入Top3、动态语义列、竞争、趋势、通用词库资格、否词方式、广告资格或投放动作。

## Independent sheets

- 竞争：固定十二列，人口等于品类相关且通用词库资格为`纳入`的F1–F4。
- 趋势：关键词索引、36行月度矩阵、12行季度矩阵和两张实际搜索量图，人口等于品类相关且通用词库资格为`纳入`的F1–F3。月度图与季度图各一词一条线，环同比百分比只留表格。
- 词频：两张并列三列表，只读品类相关且通用词库资格为`纳入`的英文词，介词过滤。
- 否词库：五列，只含`否词库状态=已收录`对应行，无否定方式。

## Process manifest

唯一总manifest记录：run_type、交付身份和最终工作簿锁；test-validation的qa_mode与检查器版本；各模块版本与上游/封装副本哈希；原始/入选/排除竞品ASIN；除自身外每个过程文件的相对路径、类型、大小、SHA-256和状态；第一板块三来源/机械词池闭环；第二板块三去向；分类/二类词/词频/竞争/趋势/否词人口；风险集合及并集人口；三种行级数据状态各自计数、主键和原始值；最终八Sheet顺序/尺寸/图表/公式与render manifest；问题引用；run_type对应质量目录白名单；隐私审计摘要；封包生命周期；21项门结果。production必须记录`independent_qa=not_applicable、p1=false`，不得写QA pass。不得写接口正文、凭据、任务ID、绝对路径或交付外报告路径。最终写入前其他文件必须冻结，manifest只写一次且排除自身。

## 21 assembly gates

1. 顶层只有过程文件夹和最终XLSX。
2. 上游工作簿和manifest版本/哈希锁定；原始/入选/排除竞品ASIN人口、一级品类核心大词、可选细分核心词、主执行锚点、Amazon联想锚点、卖家精灵种子集合、各种子唯一成功导出和通用词库资格人口闭合。原始ASIN超过5个时每个稳定竞品产品类型只保留输入顺序中的第一个有效ASIN。存在细分核心词时Amazon联想锚点为细分核心词，否则为一级品类核心大词；有细分核心词时卖家精灵种子集合恰含一级品类核心大词与细分核心词，否则恰含一级品类核心大词；同种子无交叉重复导出。recent-library-reuse按双锁预检核对source事实及当前输入/新事实、主任务资格与兼容性锁；历史入口/导出次数/执行顺序按源版本核验，不追溯套当前采集SOP，身份/指标口径/语义及当前输出硬门仍须无冲突。不要求本Run重新采集或上游completed，不把正确分离的source/current Run或revision差异机械报为污染。
3. 总表行数等于第一板块机械去重词数。
4. 三去向合计等于总表行数。
5. 每个Keyword_ID恰好一行且可回查。
6. N个动态语义列与分类列名、顺序和值一致；最终`二类词`Sheet人口、固定十六列、主键和值与分类Sheet4机械一致，零行时只保留表头；三种行级数据状态的计数/主键/原始值与分类manifest一致并自动进入允许缺口状态。
7. 竞争强度只回写品类相关、资格为`纳入`的F1–F4，详细Top3/结构不进总表。
8. 趋势摘要只回写品类相关、资格为`纳入`的F1–F3，24月矩阵只留趋势Sheet。
9. 通用词库每块可由总表中品类相关且资格为`纳入`的行机械复算且块内无重复；`不纳入/待复核`零混入；五个流量块显示表头依次为`F1 核心大词、F2 二级词、F3 中流量词、F4 中长尾词、F5 长尾词`。
10. SKU事实卡与锁定卡一致且不复制长文案；锚点卡的一级品类、可选细分核心和主执行锚点关系符合输入锁。recent-library-reuse的新卡只对当前输入锁，source锚点对历史锁及主任务同类目/条件式同细分结论；缺失不由旧卡补齐，历史品牌文本不得全局替换，品牌授权或旧SKU专属理由冲突回主任务。
11. 竞争Sheet人口等于品类相关、资格为`纳入`的F1–F4。
12. 趋势人口等于品类相关、资格为`纳入`的F1–F3，两矩阵和两张实际搜索量图闭合；每图序列数等于趋势关键词数，百分比序列为零，月份/季度范围来自全部可用完整期间。
13. 词频只读品类相关、资格为`纳入`的英文词并通过介词过滤闭环。
14. 否词库只含已收录词且无否定方式。
15. 广告资格和投放动作均为`未评估/后置`。
16. 最终工作簿恰好八个可见Sheet、顺序一致、无隐藏过程Sheet。
17. 无外链、宏、重复表名、空主键或公式错误。
18. 日期/百分比/数字/文本格式正确，八Sheet全部渲染目视复核。
19. 最终过程文件必需项齐全、相对路径稳定且哈希一致；process manifest排除自身，其他过程文件未列入/缺失/错哈希均为零，最终工作簿另行锁定。recent-library-reuse分开核对source原件/历史证据与current输入/换卡副本/输出哈希，七Sheet等值与逐字段变更白名单闭合，封口age仍为0至30天；源保持未覆盖、历史QA不升级为当前QA。
20. 质量目录严格匹配run_type白名单；production只有`independent-qa-not-applicable.json`且没有QA结论，test-validation的问题文档或引用与质量结果锁定。任务/thread UUID、机器绝对路径和非许可OOXML UUID零命中，SHA-256与精确Office结构GUID无误报。
21. production固定`not_applicable`；test-validation要求模式对应质量验证完成最终封包只读差异复核，复核前不得标记`completed/pass`，复核过程不得再写交付文件。

交付状态只用`completed、completed_with_gaps、incomplete、blocked`。已准确记录的三种行级数据状态自动对应允许缺口；production在Gate 1–20通过且Gate 21=`not_applicable`后可标记`completed_with_gaps`，test-validation在模式对应QA通过后可标记，不向用户发起运行中确认。

## Runtime preflight

先按execution_mode路由。fresh-collection及其同Run续跑在写入前验证run contract及全部适用上游stage status：规则拥有文件哈希、stage key、执行器版本、输出/证据SHA-256、人口和完成状态均闭合，继续使用`scripts/runtime_contract.py verify/ready`的精确匹配门。recent-library-reuse只按本合同双锁章节和主任务独立复用合同逐项预检，不调用或放宽全采集图的build/verify/ready/resume，不补造当前未执行阶段的completed/ready。

对应入口预检通过后只建立一个作者候选，再执行完整重载、公式、图表、八Sheet渲染、隐私、人口和21项Gate；“一次作者写入”不得减少任何检查。process manifest记录适用run/reuse contract SHA-256及对应source/current身份/哈希，真实本机合同不进入最终工作簿。预检或后验验证失败时新候选保持失败，不得就地改写为通过。
