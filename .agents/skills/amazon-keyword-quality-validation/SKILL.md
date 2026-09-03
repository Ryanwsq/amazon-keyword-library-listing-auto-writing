---
name: amazon-keyword-quality-validation
description: Independently validate a locked Amazon keyword-library test-validation run in compact validation mode or full regression mode. Use for测试跑的21项完成门、风险人口语义复核、八Sheet、公式图表、哈希隐私和封包差异；do not use for production runs, fixing files, rerunning sources, changing rules or publishing externally.
---

# Amazon Keyword Quality Validation

## 目标

在不丢失现有业务边界和21个Gate身份的前提下，只对锁定的`run_type=test-validation` Run执行独立只读验收。普通测试把全量机械检查交给确定性检查，只对完整风险人口做语义复核；完整回归保留全面重审。`run_type=production`禁止调度本Skill。

## 模式

- `compact-validation`：用于规则、Schema和检查器版本均未变化的普通测试或冒烟验证。
- `full-regression`：仅用于Skill/知识/判断边界、字段、Sheet、公式、图表、封包或检查器变化，两个正常加一个边界案例、P1/verified评估，或compact发现无法解释的异常。

模式由主任务锁定；不得为节省成本把应运行的`full-regression`降级。历史冻结产物里的`compact-production`只作为旧模式标识读取，不能据此把production Run路由到本Skill。

`qa_mode`与`execution_mode`分开锁定：`fresh-collection`及其同Run精确续跑验证当前上游阶段；`recent-library-reuse`验证主任务批准的近期历史词库复用，不是精确续跑，也不重跑上游。复用分支先完整读取主任务拥有的[近期词库复用合同](../amazon-keyword-library-operations/references/recent-library-reuse-contract.md)，再按质量合同的复用章节验收；production禁用及full触发条件不变。

## 输入

`run_type=test-validation`、Run_ID、execution_mode、当前revision、站点、qa_mode、用户三项原始输入摘要及哈希、用户在产品基础信息中提供的目标Amazon类目与是否存在多个稳定产品类型、原始/入选/排除竞品ASIN、一级/可选细分核心词、来源锚点与种子、卖家精灵各种子唯一成功导出、目标细分强等价闭环、全部模块版本/哈希/manifest、装配21项机械检查结果、风险人口清单、过程文件夹、八Sheet最终工作簿、渲染清单、process manifest和唯一问题文档或引用。近期复用另锁定主任务内容寻址复用合同、新事实卡哈希、历史源Run/revision、原始最终工作簿输出时间（带时区）/源SHA、来源周期、锚点证据、人口、历史QA和缺口；上游材料以历史血缘提供，不制造当前上游stage状态。

## 输出

- `compact-validation`：只生成`compact-qa-result.json`；仅有问题时再保留`issues.md`或`issue-reference.json`之一。复用装配渲染，不生成质量工作簿、重复预览或第二份过程副本。
- `full-regression`：生成`独立质量验证.xlsx`、`quality-manifest.json`、必要独立预览，以及问题文档或唯一引用。
- 两种模式都输出21个Gate逐项状态、QA结论`pass/blocked/incomplete`和交付状态。

## 可调用能力

- `keyword.quality.validate`
- `keyword.quality.runtime-contract.verify`

## 执行步骤

1. 读取知识、判断边界和`references/quality-contract.md`，先核对run_type、execution_mode和qa_mode。production Run立即回传`not_applicable`且不生成QA产物。`fresh-collection`及同Run精确续跑使用仓库级`scripts/runtime_contract.py verify`核对运行合同自身哈希、权威规则族人口/拥有文件哈希和阶段键；`recent-library-reuse`只读验证主任务内容寻址复用合同及其当前输入/新事实卡/规则哈希和历史血缘，不运行仅支持fresh-collection的旧运行器或ready脚本求通过。锁定Run、当前与历史revision各自角色、版本、哈希、类目/细分依据和产物清单；测试模式触发条件无法证明时使用`full-regression`，不是在运行途中要求用户判断。
2. 只读验证三来源状态、获准入口类型与回退证据、原始/入选/排除ASIN人口、第一板块两Sheet、机械词池和损失风险。原始ASIN超过5个时，每个稳定竞品产品类型只保留输入顺序中的第一个有效ASIN。有细分核心词时，Amazon联想必须以细分核心词为锚点，卖家精灵必须分别以一级品类核心大词和细分核心词执行两个种子，每个种子恰有一个官网完整官方导出优先的成功结果，并在卖家精灵模块内按机械键去重且保留双seed来源；无细分核心词时，Amazon联想和卖家精灵都只使用一级品类核心大词。同种子重复导出不得作为交叉验证或人口补充。
3. 验证第二板块四Sheet、三去向、主键、理由和人口闭环；核对一级品类核心大词、可选细分核心词、主执行锚点、强等价表达和宽泛/相邻流量词没有混层。多细分类目必须验证目标细分强等价闭环：省略一级品类词、用途限定词或其他上位限定词但仍保留决定性细分表达与完整商品头部的候选已按产品事实、直接竞品同对象身份和SIF证据逐项判定，同一机械键零层级冲突。语义反向检查必须覆盖完整风险人口，不能只找误纳：至少包含所有锚点/层级候选、Sheet2`不纳入/待复核`、Sheet3、Sheet4、决定性商品头部/稳定类型候选、配置假阴性候选、F1/F2高流量纳入词、特殊语言/连接结构和三种行级数据缺口。不得抽样、截断或用共享理由模板代表逐行结论。
4. 验证分类两Sheet、N动态列、F1–F5、F5主分组/LT和五列否词库；核对`关键词ABA排名缺失、搜索量缺失、没有搜索量`的状态、原始值和派生留空是否符合合同。
5. 验证词频、竞争和趋势均只使用`通用词库资格=纳入`的适用人口，再验证词频固定介词删除/断点、竞争十二列与Top3矩阵、趋势来源优先级/单一提供商、24月/两矩阵/两张实际搜索量图。
6. 验证最终总表三去向51+N、SKU事实、通用词库按品类相关且资格纳入机械筛选、五个流量块显示表头、最终`二类词`与分类Sheet4人口/十六列/主键/值一致、独立四个分析Sheet及八Sheet顺序。
7. 两种测试模式都执行21项装配门并保留原Gate ID。compact-validation对全部机械人口运行确定性检查，再对完整风险人口逐行语义复核；full全面重审全部阶段。每个失败Gate引用同一根因Issue_ID。
8. compact-validation复用装配阶段唯一一套八Sheet渲染和`render-manifest.json`，只读取异常页及最终总表、通用词库、二类词和趋势图的必要风险预览；full可以生成独立预览。
9. compact-validation一次性写`compact-qa-result.json`，三种行级数据状态自动对应允许缺口并可`pass/completed_with_gaps`，不等待用户确认。full按合同写一次性不可变完整质量产物。
10. 装配纳入质量结果并写最终process manifest后，只执行Gate 19–21只读差异核对；该步骤只回传状态，不再写交付文件。硬门失败不得输出pass。

步骤2–6在近期复用分支只读核验锁定历史阶段证据与新候选，完整风险人口仍逐行审计；七个非事实Sheet按合同排除明确的当前交付身份/装配版本/血缘说明白名单后业务等值，白名单变更逐字段记录前后值，源采集批次/源规则版本/数据周期不得刷新；`SKU事实卡`只对应当前锁定新事实。历史QA不代替此次独立检查，源Run/revision与当前不同本身不算污染；30天在装配封口前再核对，QA核对该最终时间，具体Gate证据归属与停止门见质量合同。

## 质量标准

- 对上游和最终封包全程只读，不调用业务外部系统、不重跑、不修改上游、不改规则；只允许在首次生成阶段写入合同白名单内的QA产物。
- Gate状态只用`pass/fail/not_executed/not_applicable`，21个Gate不得改号、合并或省略。
- 运行合同只作为版本与人口身份证据；QA仍完整读取适用Skill/合同并执行全部机械门与完整风险人口逐行语义复核，不接受规则摘要代替。
- 来源锚点审计以用户类目多稳定类型输入门为前提：有细分时联想使用细分核心词、卖家精灵保留一级核心词与细分核心词两个种子各自唯一成功官方导出血缘；无细分时两者使用一级核心词。
- 锚点与清洗语义审计覆盖全部一级品类核心大词、细分核心词、强等价表达、当前输入门要求的一个或两个卖家精灵种子、SIF候选摘要全部词及最终通用词库全部F1/F2词；多细分类目追加目标细分简称/紧凑表达及其全部上位限定词省略族，同时逐行覆盖Sheet2不纳入/待复核、Sheet3和Sheet4以反查假阴性。流量、竞品排名、缺少细分核心词字面、缺少一级品类/用途token、营销用途或目标SKU配置均不能单独通过或否决核心层级、品类去向或通用词库资格。QA按行报告，不抽样、不设上限、不用共享理由模板推断整组结论。
- 合同允许缺口可为QA pass且交付completed_with_gaps；硬门失败只能blocked/incomplete。
- 三种行级数据状态不是分类整批停止门；原值和受影响派生留空准确时自动作为合同允许缺口，不向用户发起确认。
- 同一根因只在唯一问题文档记录一次，多个Gate复用问题ID。
- compact-validation严格使用两项按需白名单且不生成完整质量工作簿/重复预览；full使用完整白名单。两种模式都不复制接口正文、整张关键词表或上游工作簿。
- 当前正式交付只接受八Sheet；七Sheet仅可作为明确`superseded`的历史证据。
- Skill保持draft/planned，P0不冒充P1。

## 异常处理

production Run不得启动本Skill或生成QA结论。test-validation Run中，风险人口不完整、任一Gate未映射、模式依据不明、revision/manifest/必需产物/哈希、开头类目输入门、ASIN代表人口、强等价闭环、单次导出血缘、资格人口、二类词闭环或渲染缺失时不得运行compact-validation并假装通过：材料充分时升级full，否则`incomplete/blocked`。三种行级数据状态准确传递时不阻断；路径/大小/哈希、白名单、隐私或Gate 19–21失败为`blocked`。只有网页入口需要新登录时由主任务进入`awaiting_login`，质量任务不为运行中的业务判断请求人工确认。
