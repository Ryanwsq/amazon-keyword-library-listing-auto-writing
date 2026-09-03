---
name: amazon-keyword-sif-competitor-collection
description: Collect SIF traffic-keyword responses for approved direct competitor ASINs, persist the unavoidable full response, and assemble a minimal keyword workbook for category-anchor and Top3 evidence. Use for第一板块SIF竞品反查、核心语义候选、Top3字段和紧凑回传；do not use for autocomplete, SellerSprite expansion, source merging, cleaning or competition scoring.
---

# Amazon Keyword SIF Competitor Collection

## 目标

逐个反查获准直接竞品的最近30天流量词，在任何汇总前保存官网完整导出或获准备用接口的完整响应，再在副任务内装配最小字段表和核心词候选摘要。

## 输入

锁定的 `Run_ID`、站点、产品事实、主任务筛选后的1–5个直接竞品 ASIN、原始/入选/排除ASIN清单及产品类型映射、每 ASIN 300条查询上限、本机忽略批次目录，以及长期副任务内置浏览器中的SIF网页登录状态。原始直接竞品超过5个时，主任务必须先按稳定竞品产品类型分组并在每类只保留输入顺序中的第一个有效ASIN；类型无法确认或每类取一后仍超过5个时，本Skill不开始外部查询。每类取一后少于3个时不得为凑数补入同类型ASIN。只有用户明确表示当前设备或会话无法完成SIF网页登录时，才允许使用SIF MCP备用入口。

## 输出

逐竞品原始响应文件、请求与周期元数据、七列SIF关键词明细、核心词候选摘要、异常日志、返回行数及紧凑主任务回传；正式主锚点由主任务确认。

## 可调用能力

- `keyword.source.competitor-traffic.web-query`
- `keyword.source.competitor-traffic.query`
- `keyword.source.sif.persist-and-verify`

## 执行步骤

1. 完整读取 `knowledge/index.md`、`../../../docs/keyword-judgment-boundaries.md` 和 `references/source-contract.md`，核对站点、竞品范围、输出目录和停止门。
2. 在第一次查询前确认 `.local/runs/<Run_ID>/keyword-sif-collector/` 已建立且允许写入，并核对主任务运行合同中的SIF stage key；目录、Run、规则哈希或阶段身份不清时停止。只有同一stage key下`completed/completed_with_gaps`状态、输出/证据哈希和人口均闭合才允许复用，失败尝试或旧revision不得续跑。
3. 在第一次查询前，先读取本Run无凭据preflight并在长期副任务的内置浏览器再次验证SIF官网已登录。未登录时状态进入`awaiting_login`，暂停并只向主任务回传登录状态、入口和受影响ASIN；由主任务提示用户登录，不得由本副任务直接向用户发问，也不得仅因当前未登录而切换MCP。登录验证通过后，对每个获准竞品 ASIN 分别通过官网查询同一最近30天口径并使用完整官方导出，最多300条，不叠加7天窗口。
4. 只有用户明确表示当前设备或会话无法完成SIF网页登录时，才允许切换同一SIF提供商的MCP备用入口。入口切换不得改变站点、ASIN、最近30天周期、300条上限、七列业务字段、结果顺序或数量闭环，并必须记录逐ASIN入口身份，不得把网页与MCP混成无身份续采。
5. 网页入口取得结果后立即使用 `keyword.source.sif.persist-and-verify` 保存查询条件、完整页面/官方导出原始证据、结果顺序和数量闭环；获准MCP备用入口则立即保存完整原始响应和全部入参。两种入口都记录来源记录ID、ASIN、站点、抓取时间、数据截止日、返回行数、批次ID和入口类型，再做字段裁剪。来源未返回起始日时写`来源未返回`，不得倒推。
6. 从每个来源记录只映射`竞品ASIN、SIF返回序号、英文关键词、ABA排名、搜索量、Top3点击份额、Top3转化份额`七列。字段缺失留空，不填0、不估算；完整原始证据继续保留，不把长响应正文回传主任务。
7. 在副任务目录装配工作簿：七列明细Sheet保留每个竞品记录；核心词候选摘要按机械键计算竞品覆盖数、最佳/中位返回序号并带出ABA、搜索量和Top3冲突状态。候选排序只帮助主任务审阅，不能替代产品事实和语义确认；高覆盖、高返回位置、高ABA或高搜索量只能证明竞品流量价值，不能证明候选是一级品类核心大词、产品细分核心词或强等价表达。
8. 核对每个竞品的入口类型、查询状态、原始证据指针、返回行数、查询上限、周期和异常，生成工作簿哈希、证据清单哈希、人口、冲突/缺失和Run相对路径清单，并写匹配运行合同的SIF stage status。主任务只接收工作簿和该紧凑清单。

## 质量标准

- 每次 SIF 结果先持久化后解析，完整官网导出或获准备用响应可回查。
- 已登录SIF官网网页端是首选入口；SIF MCP只在用户明确确认当前设备或会话无法完成网页登录后作为同提供商备用，入口必须逐记录可追溯。
- 实际查询ASIN为主任务完成代表筛选后的1–5个：原始输入不超过5个时全部保留；超过5个时每个稳定竞品产品类型只保留输入顺序中的第一个有效ASIN，原始/入选/排除人口及理由可追溯；不得为凑足三个而加入同类型第二个ASIN。
- 每个竞品和来源行有稳定 ID、站点、周期、数据截止日、抓取时间和批次。
- 300条只描述适配器上限；没有宣称 Amazon 全量。
- 工作簿明细严格七列；原始长响应没有因裁剪而丢失。
- 核心候选摘要不执行语义删除或层级晋级，主任务回传不展开逐行长响应。
- 输出只提供锚点候选证据，不越权确认类目或执行其他来源任务。

## 异常处理

无数据时检查站点、父子体和 ASIN 状态并记录失败；不得换用未授权 ASIN。原始ASIN超过5个但类型无法可靠分组，或每类取一个后仍超过5个时，在任何登录检查之外的外部查询前回传主任务`blocked_input_lock`，不得静默删掉某一类型。未登录时进入`awaiting_login`并只回传主任务，不能直接切换MCP；用户未明确确认当前设备或会话无法完成网页登录时，MCP不得执行。单个竞品失败不抹去其他竞品已取得结果。首选网页不可执行且没有满足MCP启用条件、两个入口的查询身份无法对齐、响应结构冲突、原始证据无法保存或来源授权不清时停止受影响查询，装配已取得证据并准确回传`partial/blocked/incomplete`。入口间续跑只有在稳定记录ID、查询条件、顺序和数量可证明无遗漏/重复时成立，否则从新批次完整重采受影响ASIN。
