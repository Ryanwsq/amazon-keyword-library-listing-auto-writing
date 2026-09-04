---
name: apply-amazon-listing-hard-rules
description: 按项目提供的硬性规则撰写、检查或修订 Amazon Listing 的标题与 Item Highlights、五点描述、Search Terms、图片方案和 A+ 内容，并加载项目标题/IH与五点软性知识库，支持文案交互确认及新版十四Sheet装配。用于“写 Listing”“检查是否违规”“按规则修改”“审核标题/五点/ST/图片/A+”等任务；不把未提供的产品事实补写进内容。
---

# Amazon Listing 硬性规则

## 执行原则

1. 先锁定`marketplace`（只允许Amazon-US或Amazon-DE）并识别用户要求处理的字段，再完整读取对应 reference；涉及整套 Listing 或跨字段一致性时，读取全部五份 reference。站点专属字符/字节/图片/A+规则不得跨站套用；缺少德国站当前规则证据时标记待确认，不能静默回退美国站默认值。
2. 把 reference 视为本项目的最低硬性门槛。若用户提供的当前 Seller Central、站点或类目规则更严格，以更严格且更具体的规则为准。
3. 只使用用户提供或可核验的商品事实。不得猜测材质、尺寸、数量、功能、认证、适用人群、兼容性、包装内容或效果。
4. 同时检查字段内部规则与跨字段事实一致性。不得通过拆分字段、同义改写或变形写法规避限制。
5. 写作任务先生成合规版本，再逐项自检；审核任务逐条列出违规位置、对应规则和最小修订建议。
6. 规则冲突、产品事实不足或当前类目要求不明确时，明确标注缺口，不自行放宽硬性规则。
7. 在 `Listing撰写信息决策` 项目中，先读取项目根目录的 [最终装配填充规则](../../../knowledge-base/listing-final-assembly-rules.md)。该文件决定位置和内容装填，五份 reference 决定合规边界；当前已确认的 `IMG-MAIN-01-SCENE-ALLOWED` 允许 `IMG-01` 选择合规白底首图或合规场景首图。
8. 撰写Title、Highlights和五点前，完整读取[新标题知识库](../../../knowledge-base/listing-title-highlight-writing-rules.md)与[软性写作规则](../../../knowledge-base/listing-soft-writing-rules.md)。搜索词源仅06的SKU可用关键词库；可以参考直接竞品写法，不移植事实、词源或原句。
9. 当前写法版本v2.2：Title先排06候选搜索量再对照卖点，IH按IH-TITLE-DEDUPE-01先排除Title已表达卖点（含T0），再按剩余卖点顺序补充；两者尽量用足75/125且无颜色，不强制自然句。Bullet按T0→T1/T2用途组合→配置背书→售后组织，至少5条、通常5–6条，按必要信息覆盖决定；五条讲完整就不补第六条，超过六条须先确认环境/条数。五点不设项目固定字符目标或上/下限，不使用长度例外；仍报告计数并核对真实后台限制。Title≤75、Highlights≤125及其他事实/禁限项不变。
10. 新Run须先07信息决策确认，再按[正文交互确认](../../../.agents/skills/orchestrate-amazon-listing-pipeline/references/stage-copy-review.md)讨论并确认Title、Highlights和全部Bullet（当前至少5条，通常5–6条），才能生成最终ST/10。装配读取[14Sheet展示合同](../../../knowledge-base/final-workbook-presentation.md)，正文逐字匹配确认快照；不因Skill升级静默改写旧Run。
11. 四张来源原表采用用户已授权的[原表保真装配](../../../.agents/skills/orchestrate-amazon-listing-pipeline/references/preserved-sheet-transfer.md)：核对来源/目标哈希、逐表值/公式/缓存、样式映射、图表及引用闭包。不用表格工具重新计算这些源表，不用截图或静态值冒充原表；不将搬表检查冒充被取消的上游独立QA。
12. Title按[标题知识库](../../../knowledge-base/listing-title-highlight-writing-rules.md)的TITLE-CORE-ROOT-01先确认核心大词词根，再从包含该词根的合格候选中按流量、卖点对照选词；最终合并不能将核心词根降为未确认的泛类目词。检查源词与最终品类表达两端，不能只核对字符数或“原词有流量”。此规则不改独立SKU词库准入。
13. Title、IH和全部Bullet按[软性写作规则](../../../knowledge-base/listing-soft-writing-rules.md)的FRONT-COPY-DISADVANTAGE-EXCLUDE-01保留已确认最强T0；其余通用卖点依重要程度顺序核对，跳过已确认劣势，后续合格项依原顺序补位。不得以真实、有流量、补字符或配置背书为由写回劣势；不改变Title关键词流量—卖点对照顺序或IH跨字段去重。保留事实和源对比，必要披露冲突另行处理；不自动改动主图/A+或独立SKU词库。
14. 按[软性写作规则](../../../knowledge-base/listing-soft-writing-rules.md)的CATEGORY-CONTENT-ROLE-01区分本体功能、配置证据与真实随附配件；不把电竞椅部件写成桨板式配件清单，不把配件/配置背书固定为末条。至少五条不构成罗列部件、重复卖点或虚构主题的理由。
15. Title、IH及Bullet均执行[标题知识库](../../../knowledge-base/listing-title-highlight-writing-rules.md)的FRONT-COPY-DIMENSION-EXPRESSION-01：依据类目和买家理解选择尺寸表达，Bullet先讲可感知的空间/用途，不以裸数字代替价值。IH另按IH-COMPONENT-GROUP-01合讲同一部件相关属性，按IH-BENEFIT-DEDUPE-01保留同一收益下更重要的配置；不改变事实、原排序或必要披露，不自动删除Bullet的有效结构解释。展示表达依据与取舍后重新确认正文。

## Reference 路由

- 标题与 Item Highlights：读取 [亚马逊标题硬性规则.md](references/亚马逊标题硬性规则.md)。
- 五点描述 / Bullet Points：读取 [亚马逊五点描述硬性规则.md](references/亚马逊五点描述硬性规则.md)。
- 标题、Item Highlights 与五点的内容组织、自然埋词和软性质量：读取[标题与五点软性写作规则](../../../knowledge-base/listing-soft-writing-rules.md)。
- Search Terms / ST：读取 [亚马逊ST硬性规则.md](references/亚马逊ST硬性规则.md)。
- 主图、副图、尺寸图、场景图等 Listing 图片：读取 [亚马逊图片硬性规则.md](references/亚马逊图片硬性规则.md)。
- A+ 页面、模块文案与图片：读取 [亚马逊A+硬性规则.md](references/亚马逊A+硬性规则.md)。

本项目安装版的五份 reference 来自 `knowledge-base/listing-hard-rules/` 的当前锁定副本；不得用安装包中的旧文件回滚。

## 输出要求

- 撰写时只交付用户要求的字段，并保持可直接复核的结构。
- 审核时将问题分为“硬性违规”“事实待确认”“通过”，不要把风格偏好伪装成硬性规则。
- 软性质量另行使用“通过”“可优化”“质量缺口”；五点字符计数是报告信息，不作为固定项目长度门，真实后台限制单独核验。
- 对长度、字符、字节、重复词、数量等可机械检查的项目给出实际计数。
- 不声称内容已通过 Amazon 审核；仅说明是否符合本 skill 中已读取的规则。

<!-- listing-structure-2: navigation only; original SOP above is preserved -->

本节仅补齐角色包结构导航；上方原SOP及其完整reference继续拥有业务规则和读取顺序。

## 目标

按两道确认门执行正文草案、ST、14Sheet装配及规则检查

## 输入

确认07、已验收06、锁定事实、写作知识库及正文确认记录

## 输出

待确认Title/IH/Bullet草案；确认后最终ST、14Sheet和规则检查

## 执行步骤

完整执行上方[执行原则](SKILL.md#执行原则)及其必读合同，不以结构导航替代正文。

## 质量标准

执行上方[输出要求](SKILL.md#输出要求)的全部条件。

## 异常处理

按上方[执行原则](SKILL.md#执行原则)及必读合同处理；各模块原有来源、停止及重试边界不变。

## 可调用能力

- `listing.listing-writing-qa.execute`：按两道确认门执行正文草案、ST、14Sheet装配及规则检查。

登记见[capabilities.yaml](capabilities.yaml)。planned仅为工具化需求，非已验证工具；真实执行前仍须按原SOP确认可用能力、输入和授权。[角色边界](Agent.md)、[知识索引](knowledge/index.md)、[证据状态](evidence/index.md)不授予额外权限。
