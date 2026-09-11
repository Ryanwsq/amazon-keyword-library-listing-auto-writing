# Amazon autocomplete source contract

## Fixed environment

- 首选Codex内置浏览器；当前设备无法稳定识别或操作时，允许使用普通Chrome作为备用入口。
- 使用Run锁定站点且由用户在本任务会话手动登录：`Amazon-US=amazon.com/All/10001`；`Amazon-DE=amazon.de/Alle或页面实际等义项/80539`。本会话取得`authenticated`回执前不得采集；域名、Department、邮编必须作为一个路由对象核对。
- 联想锚点按本Run已确认核心层级唯一选择：细分核心词非空时使用细分核心词；细分核心词为空时才使用唯一一级品类核心大词。不得追加强等价表达、宽泛/相邻流量词、卖点、配置或场景种子；不描述为无痕。
- 两种浏览器入口执行同一矩阵和证据门；搜索结果页、网页搜索和API不是备用入口。
- 页面进入非锁定Amazon站点时停止受影响来源，保存可见证据并回传`marketplace_mismatch/needs_user_intervention`；不得自行切回US后继续，也不得把错站建议写入来源事件。

## Required matrix

- `[anchor]`、`[anchor] `。
- `[anchor] a`至`[anchor] z`。
- `a [anchor]`至`z [anchor]`。
- `[anchor] for`、`[anchor] with`、`[anchor] without`。
- 真实品类功能/配置与锚点的前后组合。
- 规格敏感时执行`[anchor] 0`至`[anchor] 9`，否则记录不适用。

## Source record

每条来源事件至少保留：来源记录 ID、Run、一级品类核心大词、细分核心词值/空值、联想锚点、锚点选择依据、触发输入、触发类型、原始建议、机械键、可见顺序、SKU探针状态、marketplace、域名、Department、邮编、浏览器入口、浏览器环境、登录状态、采集时间、输入状态和证据指针。发生入口回退时另记首选入口失败状态与回退理由。

只有搜索框上方关键词联想区中的普通关键词建议行、关键词建议卡片和关键词建议组内选项，且文本完整可见时，才能形成来源事件。关键词建议被该区域内轮播或横向控件遮挡时，可在不改变输入的前提下用该区域控件揭示；保存操作前后证据并维持原组内顺序。仍未完整可见的内容只记异常；状态提示数量不等于可见建议证据。

底部商品卡、价格卡和商品轮播不属于关键词联想来源；即使完整可见也必须排除，不形成来源事件，不操作商品轮播来采集其内容。

## Gate

### 持久化完成门

每个输入完成后或一个可恢复小批次后立即保存原始建议、状态和可见证据，再推进持久化游标；不得把浏览器内存中的已执行格数当作落盘格数。浏览器/标签页丢失时报告最后持久化输入和未完成人口，不写完成事件。恢复时先通过当前dispatch的`checkpoint`，再验证本任务登录/站点/邮编；只恢复原锁未完成部分，不读取历史产品任务补齐。

新派发的`admission.query_lock.queries`锁定全部适用触发输入及顺序（保留尾部空格差异）；矩阵语义仍由本合同拥有。完成前保存一个`source_evidence` JSON：`run_id、records[{input,capture:{path,sha256}}]`，每个capture持久化`run_id、input、status=success|no_suggestions、suggestions、visible_evidence[{path,sha256}]`。失败/未执行格不能作为来源闭合，空建议也必须有可见证据；不能伪造空记录补人口。

运行`../../../../scripts/source_execution.py autocomplete --input <证据清单> --query-lock <锁定矩阵>`逐格核对身份、文件和哈希；`dispatch_guard observe`对联想完成事件强制执行同一检查。事件`source_evidence`必须也列于`artifacts`，`population.inputs/events`来自持久化结果；即使自报全部执行，缺一格证据也拒绝完成。检查器不能验证截图语义或替代原可见区域/完整矩阵审查，仍不产生P1。

联想锚点与锁定核心层级关系一致，全部适用输入有状态，环境字段完整，成功输入保存全部上方关键词联想区的完整可见建议，且底部商品卡、价格卡和商品轮播零混入；浏览器入口及任何回退可追溯；没有按 Enter、结果页、递归扩展、网页搜索或API替代。两个浏览器入口均不能识别/操作时整体回传`not_executed/incomplete`，不是零结果。
