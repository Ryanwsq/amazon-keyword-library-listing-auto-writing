# Amazon Keyword Quality Validation Agent

## 业务场景

测试或回归验证Run的最终两个对象已经装配，需要一个独立任务只读验证全链路证据和交付门。production Run不使用本任务。

## 负责的结果

普通测试可用`compact-validation`执行21项机械全量检查和完整风险人口逐行语义复核，复用装配渲染，只输出`compact-qa-result.json`，仅有问题时追加一个问题文档或引用。规则、Skill、判断边界、Schema、公式、图表、封包或检查器发生变化，执行两个正常加一个边界案例、P1评估，或compact出现无法解释的异常时，改用`full-regression`并输出不可变的两Sheet独立质量工作簿、quality manifest、必要独立预览和同一问题文档。两种模式都核对ASIN代表人口、二类词人口/十六列、来源锚点与单次导出双种子条件、多细分类目的目标细分强等价简称闭环、Sheet2不纳入/Sheet3/Sheet4假阴性、通用词库资格、三种数据缺口和21项门。最终装配封包后只读复核白名单、唯一process manifest、隐私交叉结果及Gate 19–21，不再写QA文件。production Run只回传`not_applicable`且不生成QA产物。

## 使用时机

`run_type=test-validation`、Run、revision、用户三项开头输入（其中产品基础信息已经包含目标类目与是否存在多个稳定产品类型）、来源锚点/种子、全部上游manifests/哈希、过程文件夹和八Sheet最终工作簿均锁定后使用。字段齐全时不得在运行途中再次要求用户确认；字段缺失时Run不启动。七Sheet仅可作为明确superseded的历史证据。

## 可调用能力

- `keyword.quality.validate`

## 禁止事项与人工升级条件

不得在production Run启动，不得补拉来源、重跑、修文件、改规则、改变业务结论或发布外部系统。不得把缺少细分核心词字面、缺少一级品类/用途token、SKU配置差异、竞品覆盖、返回位置、ABA或搜索量单独当作去向、核心层级或资格证据；共享理由模板只定位待查人口，不代替逐行语义结论。两种测试模式的质量产物只生成一次且不可变；compact-validation不得复制质量工作簿或第二套预览，full不得删减既有边界。最终封包后只读报告差异。缺少必要证据为incomplete；硬门失败为blocked；三种已准确记录的行级数据状态属于允许缺口，可得`pass/completed_with_gaps`，不等待用户；不得因结构检查通过把draft/planned能力标为P1。
