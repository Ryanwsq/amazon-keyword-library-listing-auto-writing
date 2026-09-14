---
name: amazon-keyword-sif-competitor-collection
description: Collect SIF traffic-keyword responses for approved direct competitor ASINs, persist the unavoidable full response, and assemble a minimal keyword workbook for category-anchor and Top3 evidence. Use for第一板块SIF竞品反查、核心语义候选、Top3字段和紧凑回传；do not use for autocomplete, SellerSprite expansion, source merging, cleaning or competition scoring.
---

# Amazon Keyword SIF Competitor Collection

## 目标

逐个反查获准直接竞品的最近30天流量词，按SIF MCP > SIF官网执行，在任何汇总前保存完整MCP响应或受控官网备用的完整官方导出，再在副任务内装配最小字段表和核心词候选摘要。

## 输入

锁定的 `Run_ID`、`marketplace`及派生站点参数、产品事实、主任务筛选后的1–5个直接竞品 ASIN、原始/入选/排除ASIN清单及产品类型映射、每 ASIN 300条查询上限、本机忽略批次目录，以及本Run/Task/host对应`keyword:sif-collector:sif`的真实MCP鉴权回执和查询锁。MCP鉴权不要求填写密码或账户别名/凭据引用；输入中的网页登录方式仅作备用偏好。新Run固定`source_policies.sif_competitor=mcp-first-error-only-20260914`，不要求逐Run额外例外批准或先官网失败。`marketplace`只允许`Amazon-US`或`Amazon-DE`，每次查询的提供商站点参数必须与Run一致。原始直接竞品超过5个时，主任务必须先按稳定竞品产品类型分组并在每类只保留输入顺序中的第一个有效ASIN；类型无法确认或每类取一后仍超过5个时，本Skill不开始外部查询。每类取一后少于3个时不得为凑数补入同类型ASIN。

## 输出

逐竞品原始响应文件、请求与周期元数据、七列SIF关键词明细、核心词候选摘要、异常日志、返回行数及紧凑主任务回传；正式主锚点由主任务确认。

## 可调用能力

- `keyword.source.competitor-traffic.web-query`
- `keyword.source.competitor-traffic.query`
- `keyword.source.sif.persist-and-verify`

## 执行步骤

1. 完整读取 `knowledge/index.md`、`../../../docs/keyword-judgment-boundaries.md` 和 `references/source-contract.md`，核对站点、竞品范围、输出目录和停止门。
2. 在第一次查询前确认 `.local/runs/<Run_ID>/keyword-sif-collector/` 已建立且允许写入，并核对主任务运行合同中的SIF stage key；目录、Run、规则哈希或阶段身份不清时停止。只有同一stage key下`completed/completed_with_gaps`状态、输出/证据哈希和人口均闭合才允许复用，失败尝试或旧revision不得续跑。
3. 在统一前置鉴权阶段，验证当前Run/Task/host的SIF MCP可用且真实鉴权，形成`authenticated_mcp`非敏感证明并冻结`admission.query_lock/source_access`；完整读取source-contract的字段与验证命令。MCP主路径不以官网已登录为前提。逐字段核对Run的`marketplace`与提供商参数；站点不一致记录`marketplace_mismatch`并通知用户介入，不查询或自行改成US。每个获准ASIN分别按最近30天口径请求最多300条，不叠加7天窗口。
4. 完整读取`../../../docs/mcp-first-source-access.md`。仅真实MCP明确报错才保存原始错误/错误码、原查询锁和未完成ASIN，向主任务回传官网备用登录需求；主任务提示用户在本拥有任务登录SIF官网并核验authenticated_web后，才处理未完成ASIN。零结果、缺字段、不完整响应本身不是报错，不自动切换。站点、权限、账户冲突或验证码需用户介入，不借换入口绕过。备用不改最近30天/过滤/300条/七列/顺序/人口；不能证明跨入口无遗漏重复时另批完整查询受影响ASIN，不混装旧partial或重采完成ASIN。凭据不输出，已填充一次登录恢复仍按合同。
5. MCP结果立即用 `keyword.source.sif.persist-and-verify` 保存完整原始响应和全部入参；官网备用保存查询条件、完整页面/官方导出原始证据、结果顺序和数量闭环。两种入口都记录来源记录ID、ASIN、站点、抓取时间、数据截止日、返回行数、批次ID、入口类型和受控切换原因，再做字段裁剪。来源未返回起始日时写`来源未返回`，不得倒推。
6. 从每个来源记录只映射`竞品ASIN、SIF返回序号、英文关键词、ABA排名、搜索量、Top3点击份额、Top3转化份额`七列。字段缺失留空，不填0、不估算；完整原始证据继续保留，不把长响应正文回传主任务。
7. 在副任务目录装配工作簿：七列明细Sheet保留每个竞品记录；核心词候选摘要按机械键计算竞品覆盖数、最佳/中位返回序号并带出ABA、搜索量和Top3冲突状态。候选排序只帮助主任务审阅，不能替代产品事实和语义确认；高覆盖、高返回位置、高ABA或高搜索量只能证明竞品流量价值，不能证明候选是一级品类核心大词、产品细分核心词或强等价表达。
8. 核对每个竞品的入口类型、查询状态、原始证据指针、返回行数、查询上限、周期和异常，生成工作簿哈希、证据清单哈希、人口、冲突/缺失和Run相对路径清单，并写匹配运行合同的SIF stage status。主任务只接收工作簿和该紧凑清单。

## 质量标准

- 每次 SIF 结果先持久化后解析，完整MCP响应或官网备用完整导出可回查。
- 新Run首选SIF MCP；真实当前鉴权与查询锁闭合即可执行，不新增例外批准。官网只处理已有合格MCP失败证据的未完成ASIN，入口逐记录可追溯。旧已锁web-first协议保留原验收，不用于新Run或改写历史。
- 实际查询ASIN为主任务完成代表筛选后的1–5个：原始输入不超过5个时全部保留；超过5个时每个稳定竞品产品类型只保留输入顺序中的第一个有效ASIN，原始/入选/排除人口及理由可追溯；不得为凑足三个而加入同类型第二个ASIN。
- 每个竞品和来源行有稳定 ID、站点、周期、数据截止日、抓取时间和批次。
- 300条只描述适配器上限；没有宣称 Amazon 全量。
- 工作簿明细严格七列；原始长响应没有因裁剪而丢失。
- 核心候选摘要不执行语义删除或层级晋级，主任务回传不展开逐行长响应。
- 输出只提供锚点候选证据，不越权确认类目或执行其他来源任务。

## 异常处理

无数据时检查站点、父子体和ASIN状态并记录；真实零与技术失败、不完整分开，不换用未授权ASIN。类型无法可靠分组或每类取一后仍超过5个时，查询前回传`blocked_input_lock`。MCP仅明确报错可按合同提示用户登录官网备用；错误站点、权限或账户/鉴权问题继续阻断并通知用户介入。官网备用未登录只向主任务回传`awaiting_login`；没有当前失败证据和网站认证不能执行官网。单个竞品失败不抹去其他已完成结果。查询身份无法对齐、结构冲突、证据无法保存或授权不清时停止受影响查询，准确回传`partial/blocked/incomplete`。机械检查不证明真实登录、查询完成或P1。
