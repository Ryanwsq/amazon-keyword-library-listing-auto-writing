# Listing撰写信息决策｜项目适配层

## 1. 适用范围与优先级

本文件只适用于 `Listing撰写信息决策` 本地项目。规则冲突时按以下顺序执行：

1. 用户在当前 Run 中明确锁定的指令、文件、Run_ID 和 SHA-256；
2. 本项目 `knowledge-base/listing-final-assembly-rules.md` 与 `knowledge-base/listing-hard-rules/`；
3. 本项目已登记的上游交付清单、manifest 和输入注册表；
4. 本 Skill 的通用 reference。

不得用通用包里的旧规则覆盖本项目已确认的例外。当前图片规则允许 `IMG-01` 在“合规白底首图”和“合规场景首图”之间二选一。

## 2. 两种运行模式

### downstream_intake（本项目默认）

接收另一个项目正式交接且已封存的上游文件，不重新执行 Alexa。必须锁定：

1. `01_竞品Alexa五维洞察并集.xlsx`
2. `02_Alexa商品信息审计.xlsx`
3. `03_本品优势与卖点排序.xlsx`
4. `04_竞品Alexa痛点频率统计.xlsx`
5. `05_Amazon标签优先级决策.xlsx`
6. 上游交付清单与机器可读 manifest

核验 Run_ID、5/5 业务工作簿、逐文件 SHA-256、XLSX ZIP 完整性和本品 ASIN/SKU。上游样本限制、技术失败、抓取率、未执行和未抓取到语义必须原样继承，不能转成零值或已验证事实。

`product_audit`、`market_insights`、`tag_priority`、`pain_points` 在此模式中登记为 `completed` 仅表示“已接收对应上游终态输出”，不得描述为本项目重新执行通过。

### full_pipeline（仅明确授权）

只有用户明确要求从单一原始工作簿启动或重跑上游 Alexa 阶段时使用。此时执行通用 `input-contract.md`、`validate_input.py` 和各上游 Skill 的完整约束。

## 3. 关键词跨项目生产与SKU终筛接口

关键词不是由 Listing 总控直接生产，也不是被动等待一个来历不明的 06 文件。固定链路为：

1. 本项目主线程按[关键词交接合同](keyword-handoff-contract.md)锁定三组来源、目标类目、用户细分是/否、站点、品牌/当前SKU身份、原始直接竞品及类型证据。使用独立附加对象，不改Alexa三表，不要求用户给核心词，不代关键词项目选代表ASIN。
2. 主线程向 `Amazon关键词词库｜主任务｜main` 下发锁定输入，并登记 Listing Run_ID、关键词项目 Run_ID（回执后补录）、精确文件路径、SHA-256 和产品身份。
3. 等待 Amazon 关键词项目完成；该项目把正式“最终关键词词库”总工作簿回传至本项目 `副线程｜SKU可用关键词库`，同时向 Listing 主线程提供交接回执。主线程不得自行替代该项目的品类筛选、指标计算、词频、竞争性或趋势分析。
4. 正式回执必须回主线程；SKU只可预接收。主线程按交接合同核验双方Run/revision、当前事实锁、总表与过程manifest哈希、XLSX及原状态后才下发当前Run的READY；SKU仅处理该锁定文件。获准复用保留当前事实与历史source的双身份血缘，不把历史QA或未知升级。
5. SKU 副线程只按自身锁定 Skill 对总工作簿做 SKU 事实终筛和文本质量清理，输出 `06_SKU可用关键词库.xlsx`。
6. 主线程再次核验 06 的产品身份、SHA-256、XLSX 完整性和 Sheet 契约，验收后才允许进入关键词落位。

`sku-usable-keyword-library` 仍是独立副线程，不属于新七 Skill 包的内部执行树：

- 总控负责下发和等待，但不得代替、改写或绕过该 Skill 的筛选结论；
- Amazon 关键词项目的总工作簿不能直接作为 Listing 搜索词库，必须先经过本项目 SKU 副线程；
- Listing 主线程只接收 SKU 副线程完成并锁定的 `06_SKU可用关键词库.xlsx`；
- 必须验证两次交接的 SHA-256、XLSX 完整性、Sheet 契约和产品身份；
- 当前最低 Sheet 契约为 `SKU可用关键词库`、`品类产品通用词库`、词频、竞争性分析和趋势性分析五类内容，其中后四类应保留上游原表；
- 公开 Listing 中承担搜索作用的词只能来自 `SKU可用关键词库` Sheet，不得临时补库外同义词；
- 总控可以决定库内词的落位和覆盖顺序，但不能修改该副线程的保留/筛除结论。

初始产品输入、Amazon 关键词项目总工作簿、SKU 副线程输入/输出、01–05 和 06 必须属于同一产品身份。ASIN、SKU、产品类型或已锁定事实不能闭环时，停止装配；不得跨产品或跨 Run 拼接。

## 4. 本项目副线程路由

主线程持有本总控，并把专门执行分发到以下项目本地副线程：

- Alexa商品信息审计 → `audit-alexa-shopping-product-info`
- Alexa五维洞察 → `extract-amazon-product-insights`
- Amazon标签优先级 → `prioritize-amazon-insight-tags`
- Alexa痛点频率 → `alexa-painpoint-frequency`
- Alexa痛点口语表达 → `alexa-painpoint-phrasing`
- Listing硬规则与最终QA → `apply-amazon-listing-hard-rules`
- SKU可用关键词库 → 现有独立副线程，不纳入本包

跨项目关键词上游固定为 `Amazon关键词词库｜主任务｜main`。该任务只负责产出完整关键词总工作簿；其回传文件必须继续路由到本项目 SKU 副线程，不能直接跳到 Listing 装配。

默认 `downstream_intake` 下，前四个 Alexa 副线程只接收和读取对应封存文件；只有主线程明确下发新的原始输入、Run_ID、文件哈希与启动标志，才允许重新执行业务采集或处理。

## 5. 信息校准、文案确认与最终装配边界

写作前必须先生成并完成一次完整的人机信息校准。校准包和聊天预览必须包含：

1. 人群、场景、用途、频率标签排序；
2. 全部卖点及优势/劣势；
3. 痛点与样本限制；
4. P0 卖点选择；
5. 主图 1–9 初步排布；
6. A+ 1–7 初步排布及动态挤压；
7. ST 去重范围等未决规则。

人工确认前可以生成第 5、6 项的初步排布预览，但不能生成最终标题、Item Highlights、五点、ST，也不能将主图/A+排布标为最终。P0、标签或卖点排序被修改后，必须重排受影响槽位并再次确认。七项全部确认并锁定后：

- 先按 `stage-copy-review.md` 生成标题、Item Highlights 和全部 Bullet（v2.2当前至少5条、通常5–6条，完整覆盖后不凑第六条） 的完整草稿，主线程与用户逐项讨论并确认实际英文；信息校准通过不等于文案已确认；
- 关键词唯一来源为当前 Run 已验收 06 的 `SKU可用关键词库` Sheet，参照竞品只学习写法，不引入竞品事实、关键词或未验证效果；
- 标题/IH 加载 `knowledge-base/listing-title-highlight-writing-rules.md`；五点加载软性知识库，项目不再设置固定字符最低值、目标区间或上限；实际后台限制须另行核验；
- `copy_checkpoint` 锁定正文及其来源 SHA-256 后，才生成最终 ST、回填 09 实际覆盖并装配 10；
- 新版 10 固定 14 Sheet，四张关键词来源表与三张优先级展示表按 `knowledge-base/final-workbook-presentation.md` 装填，优先级展示不得重新裁决；
- 主图最多 9 张、Premium A+ 最多 7 个模块，只输出位置、内容类型、卖点、场景、人群、用途/频率、配置参数、关键词、事实依据、重复关系、规则状态和动态挤压说明；
- 不生成真实图片、视觉设计稿或完整制作需求书；
- Q&A/评论保留接口但当前不执行；
- ST 去重范围、多个 P0 的挤压方案和 A+ 对比口径若仍为待确认状态，必须在信息校准中显式展示，不得自行锁定。

历史schema1.0及无writing_rules_version的2.0继续原合同；新建Run使用schema2.0双门/扩展交付并锁定writing_rules_version=v2.2及bullet_count_policy=coverage_based_5_to_6。已有v2.2但未锁定该policy的Run继续旧条数合同，不静默迁移。局部重写须明确授权、另存待确认草案，不原地迁移旧Run。

## 6. 安装与验证状态

项目内安装只证明文件结构、依赖发现、脚本语法和引用路径可用，属于 P0 结构验证。没有真实 Run 证据前，不得把新总控、硬规则集成或各本地副线程宣称为 P1/生产验证完成。
