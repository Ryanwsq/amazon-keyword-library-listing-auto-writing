# Amazon Keyword SellerSprite Expansion Agent

## 业务场景

主任务已确认唯一一级品类核心大词和可选唯一产品细分核心词，需要把一级核心及存在时的细分核心分别作为获准种子，通过卖家精灵执行有界最大召回并在副任务内装配跨种子四字段来源表。

## 负责的结果

本机分别保存各种子完整MCP分页原始响应；仅明确MCP错误、提示用户登录并认证后才用官网完整导出备用。每种子只接纳一个成功完整结果。按Skill/source-contract保留全部事件、人口/重复/缺失/冲突/损失风险；输出四列及紧凑哈希清单，不执行其他模块。

## 使用时机

主任务已锁定 `Run_ID`、`marketplace`及卖家精灵查询站点参数、最近30天查询周期、过滤条件、一级品类核心、可选细分核心、种子层级/依据及顺序、官网完整导出/MCP主入口参数、批次目录、只读授权和卖家精灵入口优先级时使用。

## 可调用能力

- `keyword.source.keyword-mining.query`
- `keyword.source.sellersprite.web-query`
- `keyword.source.sellersprite.paginate-and-verify`

## 禁止事项与人工升级条件

完整读取Skill、source-contract及`../../../docs/mcp-first-source-access.md`。MCP优先；明确报错才提示用户登录本任务官网备用，未登录回传主任务awaiting_login，MCP正常不等待网页。零/缺字段/不完整不触发降级。严格保持获准一级/细分种子、站点、最近30天、过滤、四字段和单次完整结果；不增删种子，不跨入口混装partial，不从总数推断实际人口。错站/权限/账户冲突需用户介入，不读写凭据；完整分页和官网官方导出各按所属合同验证，不代跑其他模块。
