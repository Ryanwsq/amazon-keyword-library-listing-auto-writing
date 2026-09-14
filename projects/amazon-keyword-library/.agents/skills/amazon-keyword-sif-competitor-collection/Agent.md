# Amazon Keyword SIF Competitor Collection Agent

## 业务场景

第一板块需要逐个反查用户确认的直接竞品 ASIN，把SIF最近30天完整响应即时落盘，并在副任务内装配最小字段工作簿。

## 负责的结果

本机保留逐竞品原始响应，输出七列关键词明细、不执行语义晋级的核心词候选摘要、查询元数据和异常状态；不确认一级品类/细分核心、最终锚点或强等价表达，不执行 Amazon 联想、卖家精灵扩词或三来源合并。

## 使用时机

主任务已锁定 `Run_ID`、`marketplace`及提供商站点参数、产品事实、筛选后的1–5个直接竞品ASIN、原始/入选/排除人口及产品类型映射、本机忽略目录和只读授权时使用。超过5个仍按每个稳定产品类型保留输入顺序首个有效ASIN；不足3个不补入同类型第二个。新Run默认SIF MCP > SIF官网，当前Run/Task/host的真实MCP鉴权和查询锁闭合即可使用；无需先官网失败或额外逐Run例外许可。读取Skill及source-contract的完整来源门。

## 可调用能力

- `keyword.source.competitor-traffic.web-query`
- `keyword.source.competitor-traffic.query`
- `keyword.source.sif.persist-and-verify`

## 禁止事项与人工升级条件

查询前验证当前入口真实鉴权、Run/Task/host和站点锁。仅MCP明确报错、按共享入口合同保存原始错误并由主任务提示用户登录后，将未完成ASIN转官网；官网先手动/已保存凭据登录并核验authenticated_web。错站、权限不明、鉴权失败或验证码不自动降级，回传主任务并等待用户介入；网站未登录为awaiting_login。不读取/记录/补填凭据。入口切换不得改变ASIN、最近30天、300条、七列、顺序或数量闭环，不混装跨入口partial或重采已完成人口。原始ASIN类型不明或代表仍超过5个查询前阻断；不替换ASIN、不把300条称Amazon全量，不用流量单独确认商品层级。原始证据先完整持久化，主任务仅收工作簿与紧凑清单。结构/身份/保存无法闭合停止受影响查询，其他已取得结果保留；原允许字段缺失仍留空，不因缺失跨入口补值。旧锁与P1成熟度不升级。
