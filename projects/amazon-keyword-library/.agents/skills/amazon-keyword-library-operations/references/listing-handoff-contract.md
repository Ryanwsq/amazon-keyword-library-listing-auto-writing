# Listing cross-project keyword handoff

- Interface version: `AKW-LISTING-INTERFACE-v1`
- Scope: Listing输入交接、关键词正式回执及接收兼容；不是新业务Run或新清洗版本。
- Runtime verification: pending；文件/机械检查不构成P1。

## Ownership and loading

本合同由关键词主任务维护，接收Listing输入或向其交付之前完整读取。Listing主任务维护其发送适配和SKU接收合同；双方锁定同一接口版本与各自拥有文件哈希。接口不得覆盖来源、核心层级、三去向、通用词库资格、SKU事实终筛、文本门或最终装配的业务拥有文件。

只在跨项目支线使用本附加交接对象。不修改Alexa原始三表固定列，不要求用户重新提交已在开头给出的字段；也不把直接在关键词项目开始的任务改成必须依赖Listing项目。

## Listing to keyword input

Listing主任务在任何关键词业务查询前，随锁定输入发送明确的关键词交接附加对象，不得仅写“其他所需字段”。它必须完整指向：

| 内容 | 接收要求 |
|---|---|
| 三组用户输入 | `产品基础信息配置、产品配置卖点、竞品对标ASIN`各自的来源文件、SHA-256与Sheet/字段或文本区块定位。可来自同一文件，但三组定位不能混淆；不拼造缺失事实。 |
| 目标Amazon类目 | 用户开头确认的类目及来源定位；不能从标题中的用途或词根猜测。 |
| 是否存在多个稳定产品类型细分 | 明确的用户是/否回答及来源定位；未知不能按“否”处理。只控制是否允许关键词主任务确认细分核心词，不让用户指定核心词。 |
| 站点与当前产品身份 | 锁定站点、品牌、当前产品事实卡标识及事实源哈希；本品ASIN、SKU、变体等已提供身份逐项传递，未知不由历史词库或竞品补齐。必须能唯一对应本次产品事实。 |
| 原始直接竞品 | 保留输入顺序、全部原始ASIN及已有的稳定产品类型标签/证据；价格、颜色等对标标签不自动等同稳定产品类型。不得把Alexa市场统计池静默当作SIF直接竞品清单。 |
| 运行与版本 | Listing Run_ID、输入revision、接口版本/合同哈希、请求的production或test-validation及授权范围。关键词Run_ID在本项目输入验收并创建后回执补录，不用Listing Run_ID冒充本项目Run。 |

原始直接竞品的代表筛选仍完全执行本项目现有边界：不超过5个全部保留；超过5个按可验证稳定产品类型保留各类型输入顺序中首个有效ASIN并记录排除项，类型不明或筛选后仍超过5个时在SIF查询前停止。跨项目适配不另设抽样或补选规则。

接收检查通过仅表示本项目已锁定完整输入，核心大词、条件式细分核心词和强等价仍由关键词主任务按产品事实与SIF证据判断。未明确为测试时仍按现行production默认值，不因“接口验证”把真实业务Run改成测试或反之。

### Agreed wire names

双方使用同一字段字典，不再分别发明别名或另一份JSON Schema。以下字段属于本机交接附加对象，不增加任何原工作簿列；实际路径、哈希、身份和值只写入本机锁定交接文件。Listing拥有发送适配，关键词拥有上述输入验收。

- 顶层：`protocol_id、listing_run_id、listing_revision、keyword_run_id、keyword_revision、run_type、authorization、contract_locks、input_groups、product_context、direct_competitors_raw、reuse_source`；`protocol_id`固定为本合同接口版本。
- `input_groups`固定包含`product_basics、configuration_selling_points、benchmark_asins`，依次映射三组用户输入。值均为来源指针数组；每个指针使用`path、sha256、locator`，不得只给文件名而省略字段/区块定位。
- `product_context`使用`marketplace、brand、asin、sku、variant、fact_card_id、current_fact_sources、target_amazon_category、has_multiple_stable_product_types、category_confirmation_source、subdivision_confirmation_source`。未知的可选产品身份保留null；类目和稳定细分用户回答不可未知，`has_multiple_stable_product_types`必须是真实布尔值，不把缺失映射false。当前事实源与确认源使用上述来源指针。
- `direct_competitors_raw`逐项使用`input_order、asin、benchmark_tags、stable_product_type、type_evidence`；保持原始顺序，类型未知保留null，类型证据使用来源指针。对标标签不能代替稳定类型证据。
- `contract_locks`分别记录`listing、keyword`两方拥有合同的`path、sha256`；请求中的`keyword_run_id、keyword_revision`可为null，输入验收回执及正式交付必须填真实本项目身份，不提前拼造。
- 无历史复用时`reuse_source`为null；适用时明确历史source Run/revision、原始最终输出时间/周期、哈希血缘，并与`product_context`当前事实源分离。其资格判断仍由原复用合同拥有。

## Keyword return and execution permission

关键词主任务验收拥有模块的正式交付后，向Listing主任务返回正式交接回执。完整工作簿可按已锁定目标同时供其SKU任务预接收，但预接收不授权运行：Listing主任务核验完身份、源文件、哈希、XLSX和交付状态并发出当前Run启动标志后，SKU任务才可执行。关键词任务不越权给Listing所属SKU任务业务启动指令。

每次回执至少包含：

- Listing Run_ID、当前关键词Run_ID及各自revision、接口版本和原请求身份；
- 当前产品/事实卡身份、当前事实源指针与SHA-256；
- 完整八Sheet最终工作簿指针/大小/SHA-256，过程文件夹及process manifest指针/SHA-256；两对象交付不缩成一个摘取Sheet；
- 三去向人口与稳定Keyword_ID、源数据周期/版本、分类缺失主键/原值/状态证据指针；
- execution_mode、run_type、真实交付状态、允许缺口、装配Gate及独立QA/P1状态；
- Listing主任务正式回执目标与SKU预接收目标的逻辑角色；真实任务ID、host、cwd只从双方当前本机映射核验，不进入同步文档或业务工作簿。

正式回执沿用上述请求身份和锁，追加`return_artifacts、population_evidence、missing_classification_evidence、data_provenance、upstream_status、receipt_targets`。`return_artifacts.workbook`含`path、sha256、size_bytes`，`process_manifest`含`path、sha256`，`process_directory`为精确目录路径，不伪造单文件目录哈希；人口、分类缺口与来源证据保留稳定Keyword_ID和源定位。`receipt_targets`使用`formal=listing_main`和可选`pre_receive=sku_keywords`；不在同步合同硬编码真实目标ID。`upstream_status`保留原实际状态，不统一改成passed。

同一原请求、双方Run、源/结果哈希构成同一交接身份。重复通知只核对已有回执，不重复开Run或重跑已接受业务；身份相同而哈希不同、过期回执、未解决旧派发或真实目标不符均停止受影响交接。现有项目内dispatch guard仍服务本项目阶段，不伪称它已经全局拦截跨项目消息。

复用时同时带当前新事实锁、当前换卡输出与历史source Run/版本/周期/原始最终输出时间/哈希血缘；Listing与关键词Run不同、历史source与current不同本身不是污染。只有锁定关系一致才合法；旧事实不得补空或覆盖新事实。历史采集、QA取消/未执行及允许缺口不升级为本次实时采集、QA通过或P1。

## Missing values at the receiving boundary

本项目继续按原分类合同和确定性执行器输出，不为满足下游补造流量层、搜索量、ABA或主标签。

- 规范缺失数值使用空单元格（JSON读入为null，空字符串仅是读取层空值）；不增加通用N/A、横线或其他占位符。
- `分类状态`是原值状态，不把动态语义列的`｜`分隔规则挪用于分类状态。当前执行器在ABA不可用时优先输出精确`关键词ABA排名缺失`且`流量层`空白；有有效ABA时才分别输出`搜索量缺失`、`没有搜索量`或正常空白。并存缺口须继续保留源字段及manifest缺失清单，不能因为只显示一个分类状态而消失。
- 下游只对“分类状态精确为关键词ABA排名缺失、ABA确实不可用且有原始来源证据、流量层空白”的合法行兼容空白分类，继续其原SKU事实和文本门。F1–F5有效映射不重算；缺失状态和来源定位留在过程账本，不增加用户表列或虚构F6。
- 原始来源确实返回数值0且证据确认ABA不可用时，保留原0及原缺失状态；绝不把空值填0。负数、非有限值、布尔、Excel错误、任意文本占位、没有依据的空白或状态/数值/层冲突不能自动按合法缺失放行，须回传上游核实；不在接收端纠正源文件。
- 合法缺失不是SKU事实匹配结论，不新增筛词条件或删除合法候选；未知复合状态或历史编码不得猜测解析。正常缺口与结构/证据错误分别处理，原缺失值边界不变。

## Unambiguous artifact names

| 对象 | 唯一含义 | 跨项目处理 |
|---|---|---|
| `品类产品通用词库` | 品类相关且通用词库资格=纳入的既有分析库 | 保持原名与全部原表内容，不称为“二类词库”。 |
| `二类词`Sheet | 上游分类Sheet4的直接替代类型全人口 | 保留于本项目完整八Sheet交付，不能用通用词库或F2块代替。 |
| `F2 二级词` | 既有ABA流量层中的F2 | 只是流量分层，不是独立二类词人口。 |
| `SKU可用关键词库` | Listing所属SKU任务按其拥有合同输出的当前SKU可用结果 | 不是关键词项目的通用词库，也不是可绕过SKU终筛的同名副本。 |

本次接口修正不改变关键词八Sheet、Listing所属06五Sheet/五字段或最终14Sheet。不因消除命名歧义而把独立二类词追加进Listing可用人口或其最终工作簿；如需新增展示，须另行确认明确对象及输出范围。

## Acceptance and exclusions

双方分别核对完整输入/身份与Run回执、合法缺失和冲突拒收、固定表名/字段/人口及同源保真；文件已存在、包已构建、消息已送达均不代表已接收、已装载或业务完成。测试只能证明所覆盖的机械接口，不能替代完整业务判断、XLSX检查或P1。

本合同不授权跨项目改文件、创建任务、外部采集、修改历史产物或公开发布。接口维护完成后仍需分别审查脱敏与项目合并；不把两个仓库的规则、原始证据和本机身份直接混装。
