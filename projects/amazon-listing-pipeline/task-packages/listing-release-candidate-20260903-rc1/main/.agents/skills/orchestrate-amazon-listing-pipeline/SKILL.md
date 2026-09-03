---
name: orchestrate-amazon-listing-pipeline
description: 编排 Amazon Listing 信息决策与最终装配。既可在明确授权时从一张产品输入工作簿启动完整 Alexa 上游流程，也可按本项目默认模式接收已封存的 01–05 上游工作簿，并接入独立的 06_SKU可用关键词库，再完成人工信息校准、埋词计划、标题/IH/五点正文交互确认、扩展 Listing 装配和硬规则检查。SKU关键词 Skill 独立运行，不由本总控调用或改写。
---

# Amazon Listing 自动化总控

## 目标

根据项目适配层选择 `downstream_intake` 或 `full_pipeline` 模式，创建可恢复的 Run，并在写作前形成可追溯的信息校准与初步排布决策包；先确认全部信息校准对象，再产可讨论正文草案；还须用户确认Title、Highlights和全部Bullet完整文字（v2.2当前至少5条、通常5–6条，不凑数）后，才生成最终ST与扩展工作簿。

总控 Skill 只负责阶段编排、接口适配、质量闸门、断点续跑和跨模块一致性。不得复制或放宽依赖 Skill 的业务规则。

## 开始前读取

每次运行先完整读取：

1. [references/project-adapter.md](references/project-adapter.md)
2. [references/pipeline-map.md](references/pipeline-map.md)
3. [references/input-contract.md](references/input-contract.md)
4. [references/quality-gates.md](references/quality-gates.md)
5. [references/output-contract.md](references/output-contract.md)

进入具体阶段前，再完整读取对应文件：

- 商品审计：[references/stage-product-audit.md](references/stage-product-audit.md)
- 五维洞察与标签：[references/stage-market-insights.md](references/stage-market-insights.md)
- 痛点：[references/stage-pain-points.md](references/stage-pain-points.md)
- 关键词：[references/stage-keywords.md](references/stage-keywords.md)
- 核心卖点决策：[references/stage-selling-point-decision.md](references/stage-selling-point-decision.md)
- 埋词规则：[references/keyword-allocation.md](references/keyword-allocation.md)
- 正文交互确认：[references/stage-copy-review.md](references/stage-copy-review.md)
- 新版14Sheet展示：[最终展示合同](../../../knowledge-base/final-workbook-presentation.md)
- Listing 生成：[references/stage-listing-generation.md](references/stage-listing-generation.md)

被调用的依赖 Skill 仍须按照其自身 `SKILL.md` 读取必需 reference，并保持其固定输入、提问、公式、Sheet 和输出边界。

## 必需依赖

运行前确认以下 Skill 可用：

- `$audit-alexa-shopping-product-info`
- `$extract-amazon-product-insights`
- `$prioritize-amazon-insight-tags`
- `$alexa-painpoint-frequency`
- `$alexa-painpoint-phrasing`
- `$apply-amazon-listing-hard-rules`
- `$spreadsheets`

关键词链路采用两段式外部生产：本项目主线程先把锁定的产品基础信息、产品配置和本次关键词项目所需事实输入下发给 `Amazon关键词词库｜主任务｜main`；该项目完成后把完整关键词总工作簿回传至本项目 `副线程｜SKU可用关键词库`，由其完成 SKU 事实终筛和文本质量清理并输出 `06_SKU可用关键词库.xlsx`。总控负责跨项目调度、等待、交接登记及身份/哈希校验，不替代两个关键词负责模块的业务处理。

## 执行流程

1. 先按 `project-adapter.md` 明确运行模式；没有明确要求重跑 Alexa 时默认使用 `downstream_intake`。
2. 使用 `scripts/validate_dependencies.py` 检查依赖。
3. `full_pipeline` 模式才使用 `scripts/validate_input.py` 预检单一主输入；`downstream_intake` 改为核对 Run_ID、01–05 文件数量、文件名、SHA-256、XLSX 完整性和产品身份。
4. 使用 `scripts/pipeline_state.py init --product-asin <已预检核对的本品ASIN>` 创建新 Run、锁定输入副本或封存包登记、保存全部输入 SHA-256 与产品身份；旧Run只读恢复，不重新初始化。
5. 锁定输入后，按 `stage-keywords.md` 将关键词所需输入下发给 `Amazon关键词词库｜主任务｜main`；等待其将完整总工作簿回传至本项目 `副线程｜SKU可用关键词库`，主线程登记并核验这次跨项目交接。
6. 按 `pipeline-map.md` 执行或接收其他数据阶段；每阶段开始和结束都更新 `run-manifest.json`。
7. 保留每个依赖项目和 Skill 的原始输出，再复制为 `output-contract.md` 中的固定编号文件；不得手工改写上游状态以迎合下游。
8. 汇总商品事实、参数优势、标签优先级、痛点、关键词和待决规则，生成 `07_核心卖点决策包.xlsx`。该文件同时承担“信息校准与初步排布决策包”的职责，必须覆盖七类确认对象：标签排序、全部卖点及优劣势、痛点与样本限制、P0 选择、主图 1–9 初步排布、A+ 1–7 初步排布及动态挤压、ST 去重范围等未决规则。
9. 在聊天中按七类对象展示摘要和初步排布，将 Run 置为 `WAITING_HUMAN_CONFIRMATION` 并停止。此时允许展示方案预览，但不得生成任何最终 Listing 文案或把主图/A+方案标为已锁定。
10. 用户可以逐项确认、修改、否决或要求重排。P0、标签排序或卖点优先级发生变化时，必须重新计算受影响的主图/A+初步排布并再次展示。只有七类对象全部锁定后，才使用 `pipeline_state.py confirm` 固化完整校准文件及其 SHA-256。
11. 完整07确认后，运行必要08、09计划映射及Title/Highlights/五点草案；使用新标题知识库，可参考直接竞品写法，关键词只从06取。调用写作Skill时须落实三个字段的尺寸表达判断及IH的相关部件合讲/同收益取舍；具体规则留在知识库，不能由总控另造事实或排序。
12. 主线程与用户逐项讨论整套正文；未确认置WAITING_COPY_CONFIRMATION并停止最终装配。确认后用pipeline_state.py confirm-copy封存草案JSON及来源哈希。
13. 根据已确认正文生成最终ST，回填09实际覆盖，再按确认排布和14Sheet展示合同装配10，完成规则和来源保真校验；不能静默改正文。四张原表按[原表保真装配](references/preserved-sheet-transfer.md)执行用户授权的OOXML底层复制：正文/展示表仍由表格工具生成，原表不重算，使用scripts/copy_preserved_sheets.py并验证公式缓存、图表、样式与关系闭包；失败不降级成值复制。
14. 新建schema2.0仍用双门/14Sheet，另锁定writing_rules_version=v2.2及bullet_count_policy=coverage_based_5_to_6；历史1.0及无该写法版本的2.0保持原合同，不静默升级。已授权局部改稿另存草案，不原地改变旧Run。交付最终工作簿和简明运行摘要。

## 运行状态

固定阶段键：

`preflight`、`product_audit`、`market_insights`、`tag_priority`、`pain_points`、`keywords`、`selling_point_decision`、`human_checkpoint`、`painpoint_phrasing`、`keyword_allocation`、`listing_draft`、`copy_checkpoint`、`listing_generation`、`final_qa`。

阶段状态只允许：

`pending`、`running`、`completed`、`needs_input`、`failed`、`skipped`。

技术失败、登录失效、验证码、限流或页面不可访问必须记为 `needs_input` 或 `failed`，不得冒充 `未抓取到`、0 分或空数据。恢复时继续原 Run，不重跑已成功问题来挑选更有利答案。

## 人工确认闸门

人工确认不是只确认一个 Top 1 卖点，而是锁定写作和最终装配所依赖的完整决策面。必须逐项确认：

1. 人群、场景、用途、频率标签排序；
2. 全部卖点及优势/劣势；
3. 痛点与样本限制；
4. P0 卖点选择；
5. 主图 1–9 初步排布；
6. A+ 1–7 初步排布及动态挤压；
7. ST 去重范围等未决规则。

其中每个候选核心价值主张仍必须能够回答：

`谁 → 在什么场景 → 想完成什么 → 本品如何支持 → 为什么值得表达 → 用什么事实证明`。

没有确认记录时：

- 不生成最终标题、Item Highlights、五点或 Search Terms；
- 不把主图 1–9、A+ 1–7 初步排布标为最终方案，也不进入最终文案装填；
- 不把试算候选描述为最终卖点；
- 不默认选择排名第一项。

### 正文确认闸门

七类信息决策与正文确认独立。只确认排序、要求继续写或未回复均不是正文确认。完整Title、Highlights和五点明确确认后才能生成最终ST/10；变更正文、07、06或事实源后以reopen-copy保留旧版并重新确认。详见stage-copy-review.md。

## 修改边界

- 修改某一阶段时，优先只改对应 `references/stage-*.md`。
- 修改字段、文件名或跨阶段接口时，同时更新 `input-contract.md` 或 `output-contract.md`。
- 修改停止条件和样本门槛时，只改 `quality-gates.md`，不得在多个阶段重复定义。
- 修改埋词位置和去重逻辑时，只改 `keyword-allocation.md`。
- 修改运行状态或恢复行为时，更新 `scripts/pipeline_state.py` 并重新测试。
- 不直接修改现有依赖 Skill，除非用户明确要求改变该 Skill 自身规则。

## 完成条件

- Run 清单能够解释每个阶段的输入、状态、输出和异常。
- 人工确认前后边界清楚且可恢复。
- 最终每个公开商品事实都能回溯至确认输入或合格证据。
- 关键词映射能够解释每个词被放入或排除的原因。
- 场景、人群、用途和频率标签有明确落位。
- 最终 Listing 已按 `$apply-amazon-listing-hard-rules` 完成字符、字节、格式、重复词、事实和跨字段一致性检查。

五点取消项目固定字符限制，但实际计数和后台限制核验仍保留。最终10新增四个来源表和三个T0/T1展示表，原07/P0与上游原始优先级不删除。

<!-- listing-structure-2: navigation only; original SOP above is preserved -->

本节仅补齐角色包结构导航；上方原SOP及其完整reference继续拥有业务规则和读取顺序。

## 输入

锁定的产品输入或01–05封存包、独立06及用户确认记录

## 输出

07信息校准、09映射、双确认门和10交付验收

## 执行步骤

完整执行上方[执行流程](SKILL.md#执行流程)及其必读合同，不以结构导航替代正文。

## 质量标准

执行上方[完成条件](SKILL.md#完成条件)的全部条件。

## 异常处理

按上方[运行状态](SKILL.md#运行状态)及必读合同处理；各模块原有来源、停止及重试边界不变。

## 可调用能力

- `listing.main.execute`：总控、跨项目交接、两道人机确认、07/09与最终交付验收。

登记见[capabilities.yaml](capabilities.yaml)。planned仅为工具化需求，非已验证工具；真实执行前仍须按原SOP确认可用能力、输入和授权。[角色边界](Agent.md)、[知识索引](knowledge/index.md)、[证据状态](evidence/index.md)不授予额外权限。
