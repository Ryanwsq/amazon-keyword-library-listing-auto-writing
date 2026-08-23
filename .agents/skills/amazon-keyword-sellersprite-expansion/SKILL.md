---
name: amazon-keyword-sellersprite-expansion
description: Expand one approved Amazon core seed through SellerSprite with bounded maximum-recall passes, four requested business fields and a locally assembled handoff workbook. Use for第一板块卖家精灵分页扩词、漂移重复、四字段表格和损失风险检查；do not use for seed selection, SIF, autocomplete, source merging or trend queries.
---

# Amazon Keyword SellerSprite Expansion

## 目标

对主任务按核心词优先级确认的单一代表种子执行有界最大召回分页，保存接口实际返回的原始页和分页证据，并在副任务内装配四字段关键词表。

## 输入

锁定的 `Run_ID`、站点、查询月份、一个代表种子、种子层级及确认依据、每页20条参数、本机忽略批次目录，以及首选卖家精灵MCP或获准卖家精灵网页备用入口。存在已确认产品细分核心词时，种子必须为该词；不存在时，种子必须为一级品类核心大词。

## 输出

逐种子逐页原始响应、实际返回行数、机械键重复组、总数/页数漂移、四字段缺失、分页/Pass状态、损失风险、四列来源工作簿及主任务紧凑回传清单。

## 可调用能力

- `keyword.source.keyword-mining.query`
- `keyword.source.sellersprite.web-query`
- `keyword.source.sellersprite.paginate-and-verify`

## 执行步骤

1. 完整读取 `knowledge/index.md`、`../../../docs/keyword-judgment-boundaries.md` 和 `references/source-contract.md`，核对单一种子、种子层级/依据、站点、查询月份、分页参数、Pass上限和停止门。
2. 首选卖家精灵MCP；MCP不可用时允许切换已登录卖家精灵网页。两种入口都固定`keyword,keywordCn,searchRank,searches`四个业务字段；单一种子从第1页开始、每页20条，连续到短页或空页结束。种子由主任务给定，本 Skill 不新增、替换或追加；细分核心词已确认时拒绝一级品类词、强等价表达、宽泛流量词或相邻细分词作为默认种子。
3. 每页返回后立即保存实际返回的完整响应或网页页面/导出原始证据、查询条件、入口类型、页码、种子、Pass、站点、时间、声明总数/页数和四个业务字段；不在模型消息中展开逐页行。
4. 单一种子至少执行两个版本化完整Pass。第二个Pass增加新机械键或出现键交换时最多执行第三个Pass；第三个Pass结束后不自动增加第四个Pass。声明总数/页数漂移只作证据，只要页码持续前进、返回可用、无整页重复/循环并能达到短页或空页，就继续当前Pass。入口间续跑只有在种子、月份、Pass、页码、四字段和稳定事件账本能够证明无遗漏/重复时成立，否则新建版本并从该种子Pass第1页重采。
5. 使用`keyword.source.sellersprite.paginate-and-verify`检查页码、实际行数、Pass间新增/交换、重复、循环、缺失和损失风险。持续错误阻断受影响Pass；已取得数据仍进入工作簿并准确标记`partial`，不得因错误返回空来源。
6. 原始页边界重复和同一机械键冲突在本机事件清单中全部保留。副任务按锁定种子/Pass/页/行顺序机械融合，一词一行；四字段冲突时以首次非空原值作展示，不平均、不估算，并在清单记录全部冲突来源。
7. 在副任务目录装配业务工作簿，唯一业务Sheet只含`英文关键词、中文翻译、ABA月排名、月搜索量`四列。再生成Run相对路径、哈希、唯一词数、原始事件数、Pass/分页轨迹、缺失/冲突和损失状态清单；主任务只接收工作簿与该紧凑清单。

## 质量标准

- 单一种子至少两个完整Pass；需要时最多三个，页码连续且原始页可回查。
- 种子层级闭合：有细分核心词时只用细分核心词，否则只用一级品类核心大词；强等价表达和宽泛/相邻流量词没有默认成为种子。
- 实际返回行数是闭环真值；声明总数漂移被记录。
- 分页边界重复没有从原始证据中删除。
- MCP或网页查询只含四个业务字段，工作簿也严格为四列；入口、缺失与冲突状态可识别。
- 主任务回传不展开逐页/逐行长响应，工作簿与清单的哈希、行数和路径可核验。
- 不执行种子选择、三来源合并、语义过滤、竞争补拉或趋势查询。

## 异常处理

种子数量、层级或确认依据不符合输入门时不开始查询。MCP不可用时切换卖家精灵网页；网页也不可用、入口身份无法对齐、明确报错、限流、结构异常、缺页、整页重复、循环或无继续进展时停止受影响Pass并保留已取得数据。成功查询返回零结果时复核方法、站点和必填参数后形成新版本重试；单一种子达到有界Pass完成门时才标记`complete_with_residual_risk`，部分结果必须准确标记`partial/blocked`。
