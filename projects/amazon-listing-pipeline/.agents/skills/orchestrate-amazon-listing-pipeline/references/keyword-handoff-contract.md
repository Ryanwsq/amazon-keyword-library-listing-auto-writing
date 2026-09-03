# Listing与关键词项目交接合同

- 协议：`AKW-LISTING-INTERFACE-v1`；维护事项：`AKW-LISTING-INTERFACE-20260903-01`。
- 仅补足跨项目发送/回执和SKU合法缺失接收，不改变Alexa原始三表、关键词业务算法、06五列五Sheet或10十四Sheet。
- 本文定义附加JSON对象的键名；双方共用，不再另建含义不同的同名schema。来源与业务状态仍由各自拥有模块维护。

## 1. 附加请求对象

主任务从已有用户输入取值并附来源，不要求用户重填已提供字段。没有明确值时保留未知并在关键词查询前补确认，不能从标题、竞品或历史SKU猜事实。

来源指针统一为`{path, sha256, locator}`：path为可读取的精确文件路径，sha256为完整64位哈希，locator为Sheet/字段/单元格或文本记录定位。整文件指针可省locator；事实、确认、类型证据必须有定位。指针需实际核验，不是填入字符串便算通过。真实设备/任务ID只从本机任务映射取得，不进入共享合同正文或业务表。

| 顶层键 | 内容与规则 |
|---|---|
| `protocol_id` | 固定为本协议ID。 |
| `listing_run_id` / `listing_revision` | 当前Listing运行及输入版本，非空。 |
| `keyword_run_id` / `keyword_revision` | 初次请求尚未创建时为null；关键词主任务验收并创建后回执补录，不冒用Listing Run_ID。 |
| `run_type` | 沿用本次已锁定的production或test-validation；维护测试不改变真实Run类型。 |
| `authorization` | 本次授权范围及source指针；接收不自动授权采集或SKU执行。 |
| `contract_locks` | `listing`、`keyword`两项，各含本次实际采用合同的path/sha256。 |
| `input_groups` | 下述三个固定键的来源指针数组。 |
| `product_context` | 当前产品身份、类目及用户细分回答，见下文。 |
| `direct_competitors_raw` | 保留原始顺序与全部记录的数组，不预筛、不以Alexa市场池替换。 |
| `reuse_source` | 非复用为null；复用时记录历史source Run/版本/周期/原始最终输出时间、原工作簿path/sha256及授权source。不能代替当前事实锁。 |

`input_groups`固定为：

- `product_basics`：用户“产品基础信息配置”来源；
- `configuration_selling_points`：用户“产品配置卖点”来源；
- `benchmark_asins`：用户“竞品对标ASIN”来源。

三个数组可以指向同一工作簿不同区域，但不得混淆组别。Alexa所用`新品基础信息/新品基础配置/竞品对标ASIN`的既有列名、顺序和含义不变；只在此对象中显式记录来源对应关系，不强改原表以匹配关键词命名。

`product_context`固定传递：

| 键 | 要求 |
|---|---|
| `marketplace` / `brand` | 当前锁定站点、品牌；未提供品牌保留null并说明，不借历史品牌补齐。 |
| `asin` / `sku` / `variant` / `fact_card_id` | 已提供身份逐项传递，未知为null；组合必须能唯一对应当前SKU事实，不强迫未分配ASIN的产品伪造ASIN。 |
| `current_fact_sources` | 当前事实来源指针数组，包含事实卡及已确认补充；复用旧词数据也必须另锁当前事实。 |
| `target_amazon_category` | 用户确认的目标Amazon类目，不从关键词推测。 |
| `has_multiple_stable_product_types` | 用户确认的boolean；未知为null且阻断关键词查询，不能默认false。 |
| `category_confirmation_source` / `subdivision_confirmation_source` | 类目及细分是/否回答的来源指针。 |

`direct_competitors_raw`每项含`input_order、asin、benchmark_tags、stable_product_type、type_evidence`。input_order对应原始顺序；ASIN原值、重复/异常与原始对标标签均保留。稳定产品类型未知为null，type_evidence为来源指针数组；价格/颜色/尺寸等对标标签不自动算稳定类型证据。

Listing不决定核心大词、不向用户索要核心词，也不在发送前另选代表ASIN。核心词、条件式细分、强等价和超过5个直接竞品的代表筛选归关键词主任务，按其现行规则执行；未知类型及筛选后仍超限由其在业务查询前处理，不在这里增加抽样或补选。

## 2. 正式回执与READY

关键词正式回执沿用上面原请求身份、输入及合同锁，补齐当前关键词Run/revision，并增加：

| 键 | 要求 |
|---|---|
| `return_artifacts` | `workbook`为完整总工作簿path/sha256/size_bytes；`process_manifest`为过程manifest的path/sha256；`process_directory`为过程文件夹精确路径（目录不伪造单文件哈希）。 |
| `population_evidence` | 三去向人口及稳定Keyword_ID的来源指针，不在Listing重新分类。 |
| `missing_classification_evidence` | 缺失主键、原ABA值、原分类状态、原流量层及原因的证据指针；并存搜索量缺口也保留。 |
| `data_provenance` | 源数据周期/版本及原始输出时间、当前换卡输出与历史source的血缘；未知保留未知。 |
| `upstream_status` | 原样传递execution_mode、run_type、delivery_status、allowed_gaps、assembly_gates、independent_qa、P1；缺少关键状态时回询，不推成通过。 |
| `receipt_targets` | `formal=listing_main`；允许`pre_receive=sku_keywords`。任务真实绑定由当前本机映射核对。 |

固定控制门：完整总工作簿可先到SKU任务预接收，但正式回执必须回Listing主任务。主任务核对请求身份、双方Run、当前事实锁、总工作簿和过程manifest哈希、XLSX完整性、人口/缺口及原交付状态后，才下发本Run的READY启动标志。关键词项目不得越权启动Listing的SKU任务，SKU预接收不能代替主任务验收。

READY记录至少绑定`protocol_id、listing_run_id、keyword_run_id、listing_revision、keyword_revision、input_locks、workbook_sha256、process_manifest_sha256、issued_by=listing_main`，并保留核验回执。消息送达、文件存在、机械预检或只读装载回执均不是READY业务授权。

同一请求身份和相同哈希的重复回执只复核，不重开Run、不重复启动；身份相同但哈希变化、旧派发未解决、产品/事实无法闭环时停止受影响交接。当前Run和历史source不同本身不算污染，但必须有复用授权及明确血缘；旧SKU事实不能覆盖或补空当前事实。技术失败、未执行、未抓取到、真实零值、QA取消和P1状态各自保留。

## 3. 合法缺失与三种词表

SKU流量层接收只按SKU所属工作簿合同第3节：正常F1–F5原样映射；只有精确ABA缺失状态、确实不可用的原值、有主键级证据及空流量层，才允许最终分类空白。无占位符、复合状态、填零或推算分层。本接口不取代SKU事实/字符/拼写门。

| 对象 | 明确含义与去向 |
|---|---|
| 品类产品通用词库 | 上游品类相关且通用词库资格纳入的原表；仍是06第二张及10既有来源表。 |
| 独立二类词Sheet | 上游分类Sheet4_二类词对应的直接替代类型人口；留在上游完整总工作簿，不默认加入06或10。 |
| F2二级词 | 既有ABA流量分层，仅机械映射为“二级词”，不是独立二类词人口。 |

用户是否希望另外交付独立二类词仍待明确；本轮不增加Sheet、不扩大SKU候选人口、不把三者互相替代。两道人机确认、写作词源、原表保真及历史Run版本不变。

## 4. 维护验收

双方按同一字段约定核对各自拥有文件、路径/哈希与接收回执。此对象是文件交接合同，不声称已建立全局消息拦截器或自动执行器；语义证据、XLSX和业务判断仍由原负责模块核验。机械边界测试不等于真实业务Run或P1。只读加载新版后仍等待具体Run输入与READY。
