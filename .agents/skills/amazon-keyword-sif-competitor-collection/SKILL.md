---
name: amazon-keyword-sif-competitor-collection
description: Collect SIF traffic-keyword responses for approved direct competitor ASINs, persist the unavoidable full response, and assemble a minimal keyword workbook for category-anchor and Top3 evidence. Use for第一板块SIF竞品反查、核心语义候选、Top3字段和紧凑回传；do not use for autocomplete, SellerSprite expansion, source merging, cleaning or competition scoring.
---

# Amazon Keyword SIF Competitor Collection

## 目标

逐个反查获准直接竞品的最近30天流量词，在任何汇总前保存接口完整响应，再在副任务内装配最小字段表和核心词候选摘要。

## 输入

锁定的 `Run_ID`、站点、产品事实、3–5个直接竞品 ASIN、每 ASIN 300条查询上限、本机忽略批次目录，以及首选SIF MCP或获准SIF网页备用入口。

## 输出

逐竞品原始响应文件、请求与周期元数据、七列SIF关键词明细、核心词候选摘要、异常日志、返回行数及紧凑主任务回传；正式主锚点由主任务确认。

## 可调用能力

- `keyword.source.competitor-traffic.query`
- `keyword.source.competitor-traffic.web-query`
- `keyword.source.sif.persist-and-verify`

## 执行步骤

1. 完整读取 `knowledge/index.md`、`../../../docs/keyword-judgment-boundaries.md` 和 `references/source-contract.md`，核对站点、竞品范围、输出目录和停止门。
2. 在第一次查询前确认 `.local/runs/<Run_ID>/keyword-sif-collector/` 已建立且允许写入；目录或 Run 版本不清时停止。
3. 首选SIF MCP；MCP不可用时允许切换SIF网页浏览器。对每个获准竞品 ASIN 单独使用同一最近30天口径查询最多300条，不叠加7天窗口；入口切换不得改变站点、ASIN、周期或业务字段。
4. MCP返回后立即使用 `keyword.source.sif.persist-and-verify` 保存完整原始响应和全部入参；网页入口则保存查询条件、页面/导出原始证据、结果顺序和数量闭环。两种入口都记录来源记录ID、ASIN、站点、抓取时间、数据截止日、返回行数、批次ID和入口类型，再做字段裁剪。来源未返回起始日时写`来源未返回`，不得倒推。
5. 从每个`top_keywords`记录只映射`竞品ASIN、SIF返回序号、英文关键词、ABA排名、搜索量、Top3点击份额、Top3转化份额`七列。字段缺失留空，不填0、不估算；完整原始响应继续保留，不把长响应正文回传主任务。
6. 在副任务目录装配工作簿：七列明细Sheet保留每个竞品记录；核心词候选摘要按机械键计算竞品覆盖数、最佳/中位返回序号并带出ABA、搜索量和Top3冲突状态。候选排序只帮助主任务审阅，不能替代产品事实和语义确认；高覆盖、高返回位置、高ABA或高搜索量只能证明竞品流量价值，不能证明候选是一级品类核心大词、产品细分核心词或强等价表达。
7. 核对每个竞品的入口类型、查询状态、原始证据指针、返回行数、查询上限、周期和异常，生成工作簿哈希、行数、冲突/缺失和Run相对路径清单。主任务只接收工作簿和该紧凑清单。

## 质量标准

- 每次 SIF 返回先持久化后解析，完整响应可回查。
- MCP与网页只是同一SIF提供商的不同入口；网页满足相同查询、字段、顺序和数量闭环时可作为正式输入，入口必须逐记录可追溯。
- 每个竞品和来源行有稳定 ID、站点、周期、数据截止日、抓取时间和批次。
- 300条只描述适配器上限；没有宣称 Amazon 全量。
- 工作簿明细严格七列；原始长响应没有因裁剪而丢失。
- 核心候选摘要不执行语义删除或层级晋级，主任务回传不展开逐行长响应。
- 输出只提供锚点候选证据，不越权确认类目或执行其他来源任务。

## 异常处理

无数据时检查站点、父子体和 ASIN 状态并记录失败；不得换用未授权 ASIN。单个竞品失败不抹去其他竞品已取得结果。MCP不可用时切换SIF网页；网页也不可用、两个入口的查询身份无法对齐、响应结构冲突、原始证据无法保存或来源授权不清时停止受影响查询，装配已取得证据并准确回传`partial/blocked/incomplete`。入口间续跑只有在稳定记录ID、查询条件、顺序和数量可证明无遗漏/重复时成立，否则从新批次完整重采受影响ASIN。
