---
name: amazon-keyword-sellersprite-expansion
description: Expand approved core seeds through SellerSprite MCP; official website export is allowed only after an explicit MCP error and user login. Use for卖家精灵双层核心扩词、单次完整结果、四字段工作簿及损失风险检查；not seed selection, SIF, autocomplete, source merging or trend.
---

# Amazon Keyword SellerSprite Expansion

## 目标

由卖家精灵MCP优先完成获准种子的扩词；仅明确报错后登录官网备用，不改变四字段及单次完整结果要求。

## 输入

主任务锁定Run_ID、marketplace及提供商站点、最近30天、唯一一级核心、可选唯一细分核心、层级依据、种子顺序、过滤、查询参数、stage key、本机忽略目录和当前Task/host。有细分核心按一级核心、细分核心分别执行，否则只查一级核心。强等价、宽泛、卖点、配置和场景不得新增为种子，本Skill不选择、替换、遗漏或语义合并种子。

每种子MCP优先取得一个成功完整结果；仅明确MCP报错后提示用户登录本任务卖家精灵官网，认证后完整官方导出备用。网页登录偏好不覆盖该顺序；MCP正常不等网页登录。Sorftime网页和MCP均不得参与扩词。

## 可调用能力

完整读取 `knowledge/index.md`、`../../../docs/keyword-judgment-boundaries.md`、`references/source-contract.md`和`../../../docs/mcp-first-source-access.md`；共享合同定义v2鉴权、报错、登录通知证明及新policy，历史合同不作为新Run入口。

- `keyword.source.keyword-mining.query`：MCP首选。
- `keyword.source.sellersprite.paginate-and-verify`：完整落盘、分页闭合、机械融合。
- `keyword.source.sellersprite.web-query`：仅明确MCP报错、提示用户登录并验证后的网站备用。

## 执行步骤

1. 核验当前Run、输入/规则/种子/查询锁、实际Task/host和stage key。只有同stage key、completed/completed_with_gaps、输出/证据哈希和人口闭合才允许复用，失败、partial或旧revision不能冒充完成复用。
2. 首选MCP核验真实鉴权取得authenticated_mcp，冻结admission.query_lock/source_access。站点只允许Amazon-US/Amazon-DE并与Run一致；错站记录marketplace_mismatch停止并通知用户，不自行切US，不前置打开官网。
3. 各种子MCP从第1页连续到短页或空页，每页20条，returnFields固定keyword,keywordCn,searchRank,searches。逐页完整落盘后解析，保留请求、页码/页内序号、声明总数、原始重复、事件账本；核对实际行数、缺页、整页重复、循环及损失风险。零结果、缺字段、不完整或保存失败本身不是MCP报错，不自动切官网。
4. 只有真实MCP明确报错才保留原始错误、错误码及已完成/未完成人口，向主任务回传官网登录需求，由主任务提示用户在对应拥有任务登录。核验authenticated_web及锁定站点才开始官网查询；未登录为awaiting_login。凭据/验证码/Cookie/令牌不进入聊天、证据、Run、Git；错站、账户冲突、权限/挑战不通过换入口绕过，需用户介入。
5. 官网备用按当前可见语义确认关键词挖掘页顶部/左上导出入口，不绑定固定selector/坐标，不以页面抄取代替完整导出。按种子、参数、时间及导出任务身份确认记录中的本轮新完成文件，原样保存唯一成功官方XLSX。保留入口/任务/记录/完成文件、页面声明总数、实际行数与唯一机械键。失败触发/任务/下载有界恢复，只作诊断。跨入口不能证明无遗漏/重复时另批完整查询受影响种子，旧partial保留但不混装；已完成种子不重采。
6. 每个种子只接纳一个成功完整结果，成功后不为交叉验证重复查询/导出。按种子/页/行顺序机械融合，一词一行，保留所有seed来源；字段冲突展示首次非空原值，原始冲突不删除，不平均、不估算、不精确词补拉。
7. 在副任务内装配唯一业务Sheet，仅英文关键词、中文翻译、ABA月排名、月搜索量四列。主任务只收工作簿、Run相对路径、哈希、原始事件数/唯一词数、逐种子完成状态、完整分页或官方导出证据、失败尝试、缺失/冲突/损失风险和匹配stage status的紧凑清单。长响应只留本机忽略目录。

## 输出

四字段来源工作簿、逐种子完整原始证据、事件账本和带Run相对路径/哈希/人口/状态/缺口的紧凑清单。正式回传要求见步骤7和source-contract。

## 质量标准

实际返回行数是闭环真值；声明总数漂移及未解释差额如实保留，不从整数推断上限、不补造缺行。页边界重复不从原始证据删除。单行缺失保留空白并记录，零、partial、技术失败分别呈现，不能包装成MCP报错。

## 异常处理

核心/种子身份不符、权限不清、保存失败、结构异常、缺页、整页重复、循环或无进展时停止受影响种子并保留数据；只有明确MCP报错才按共享合同降级。全部种子满足单次完整门才标记complete_with_residual_risk，部分为partial/blocked。不执行种子选择、三源合并、语义过滤、竞争或趋势；机械检查不证明真实业务完成或P1。
