# Runtime optimization contract

本文件只拥有执行性能、阶段身份、断点续跑和失败隔离合同；不拥有任何关键词业务判断。业务语义仍以`knowledge/`、`docs/keyword-judgment-boundaries.md`和各单一职责Skill合同为准。发生冲突时，本性能层必须停止，不能以“更快”为理由覆盖业务规则。

本文件的stage graph和`scripts/runtime_contract.py`适用于`execution_mode=fresh-collection`及该流程的同Run续跑。2026-09-03用户确认的跨产品`recent-library-reuse`不是性能层跳过业务门，而是独立业务入口；按operations的`references/recent-library-reuse-contract.md`冻结当前三项输入/新事实/规则与历史来源/原始最终输出时间/人口/哈希，逐项预检后直接到装配。复用分支不调用本脚本制造全量上游ready，也不将历史stage改成本Runcompleted；本文件原精确续跑规则和确定性算法保持不变。

## 不可削减边界

- 三来源、固定来源人口、完整短语逐行语义判断、目标细分强等价闭环、上位限定词省略族反查、Sheet2不纳入/待复核与Sheet3/Sheet4反向审计均保持全量。
- `通用词库资格`、三种行级数据缺口、F1–F5阈值、竞争Top3-only、趋势单Run单提供商、八Sheet/51+N/二类词机械复制、21个Gate ID和full-regression触发条件不变。
- 确定性脚本不得判断一级品类、细分核心、强等价、中心购买对象、二类词、动态语义标签、否词语义或广告资格。
- 任何人口、字段、原值、资格、哈希、规则族、风险审计或Gate差异都使优化结果失败；不得退回抽样、摘要判断、共享模板外推或静默容错。

## 运行合同

2026-09-03调度控制由`dispatch-control-contract.md`拥有，入口为`scripts/dispatch_guard.py`。它在原ready/哈希门外增加事务派发去重、拥有任务首次业务动作前双向身份校验、最小事件与不确定送达恢复；不更改下方阶段图或计算核心。控制层元数据不属于业务stage status，不能由发送/接收回执制造completed。

每个Run在本机忽略目录建立`run-contract.json`，由`scripts/runtime_contract.py`根据本机输入规格和`contracts/runtime-rule-map.json`生成。运行合同至少锁定：

- Run_ID、`run_type`、Git revision、站点和三组输入各自SHA-256；
- 目标Amazon类目、多稳定产品类型回答、原始/入选/排除ASIN人口；
- 权威规则族、拥有文件、锚点、当前文件SHA-256和适用阶段；
- 阶段依赖、执行器版本和内容寻址`stage_key`；
- production的`quality_routing=not_applicable`，或test-validation的`qa_mode`与变更触发项。

规则映射只保存稳定Rule ID、拥有文件和存在性锚点，不复制规则全文。每个阶段继续读取自己拥有Skill及直接引用合同；运行合同的哈希用于证明读取的是同一版本，不是用摘要替代完整规则。权威文件、输入、依赖、执行器版本或适用质量模式任一漂移都会改变阶段键。

真实路径、任务ID、凭据、cookie和会话内容禁止写入运行合同。运行合同、preflight和stage status只保存在`.local/runs/<Run_ID>/`，不进入Git或最终业务工作簿；最终process manifest只记录运行合同SHA-256和各适用stage身份/哈希，维持可追溯而不复制本机状态。

## 登录预检与来源冻结

SIF与卖家精灵在Run开始时可以并行检查会话，但业务动作仍按既有依赖执行。预检文件只记录`sif/sellersprite`的`authenticated/awaiting_login/unavailable`和检查时间，不记录凭据。

- SIF stage启动前必须为`authenticated`；未登录只回传主任务`awaiting_login`，保持既有网页优先与用户明确无法登录才允许MCP的门。
- SellerSprite stage启动前必须为`authenticated`；未登录只回传主任务，保持已登录官网完整官方导出优先、官网链路不可用才允许同提供商MCP的门。
- 登录恢复只解冻对应来源分支，不要求重做已通过内容哈希验证的无关阶段。

## 阶段图与失败隔离

固定阶段图为：

1. `sif -> core-lock`；
2. `core-lock -> amazon-autocomplete + sellersprite`；
3. 三来源汇合为`first-board -> cleaning`；
4. `cleaning -> word-frequency + classification`；
5. `classification -> competition + trend`；
6. 四个分析分支汇合为`assembly`；
7. 仅test-validation再进入`quality-validation`。

阶段失败只阻断自己的后代，不冻结无依赖关系的已就绪分支。例如词频失败只阻断词频和最终装配，不得暂停分类、竞争或趋势；分类失败会阻断竞争、趋势和装配，但不推翻已完成词频。最终装配仍必须等待全部适用分支闭合，因此失败隔离不构成缺模块交付授权。

## 内容寻址续跑

阶段只在以下条件全部成立时允许复用：

1. 当前运行合同自身哈希有效，权威规则文件哈希与合同一致；
2. stage status中的`stage_key`等于当前计算值；
3. 状态为`completed`或`completed_with_gaps`；
4. 输出SHA-256、证据SHA-256和人口锁均存在；
5. 依赖阶段身份与哈希没有变化。

任一条件不成立只重跑受影响阶段及后代，不重跑无关分支。外部来源续跑仍须满足各来源Skill的稳定事件、无遗漏/无重复和完整性门；内容寻址不能把失败尝试、partial、not_executed或旧revision提升为成功证据。

## 确定性核心

`scripts/keyword_deterministic_core.py`只承担以下可机械复算工作：

- `validate-source-merge`：验证三来源机械键并集、去重人口和来源身份闭合，不选择核心词或删除关键词；
- `validate-cleaning-ledger`：验证三去向、Sheet2资格、完整风险人口与上位限定词省略族均逐行复核，不生成语义去向；
- `classify-traffic`：按锁定ABA阈值计算F1–F5并精确传递三种数据状态，不生成动态语义标签或F5主标签；
- `word-frequency`：按`EN_PREP_CORE_V1`执行NFKC分词、介词删除、硬断点双词、稳定排序和人口统计；
- `competition`：只对资格纳入F1–F4用同周期精确Top3两项执行固定阈值和4×4矩阵；
- `trend`：只对资格纳入F1–F3在单一提供商的至少24完整月上计算月/季实际量及环同比，缺失不补0，图表数据只含实际搜索量。

JSON结果必须由拥有Skill写入过程工作簿并继续执行字段、公式、渲染、目视和模块质量门。脚本输出不是独立QA，也不自动提升capability或maturity。

## 装配与验收

装配开始前一次性锁定全部上游stage status、人口、字段和哈希；预检通过后才进行一次业务工作簿作者写入。写入后仍执行完整重载、公式、图表、渲染、隐私、人口、Sheet和Gate验证。验证失败必须修复新候选并重新验证，不得把失败候选改写为通过。

本性能层或其检查器发生变化时，下一次test-validation必须使用`full-regression`。只有新旧结果在相同输入下满足关键词主键人口、三去向、资格、所有业务列值、动态列、分析人口、Sheet/schema、公式/图表和21个Gate完全一致，才可接受为无损优化；当前P0和夹具通过不等于P1或实测提速结论。

## 命令入口

```bash
python3 scripts/runtime_contract.py build --spec <local-spec.json> --out <run-contract.json>
python3 scripts/runtime_contract.py verify --contract <run-contract.json>
python3 scripts/runtime_contract.py ready --contract <run-contract.json> --stage <stage> --status-dir <status-dir> --preflight <preflight.json>
python3 scripts/runtime_contract.py resume --contract <run-contract.json> --stage <stage> --status <stage-status.json>
python3 scripts/runtime_contract.py impact --run-type production --stage word-frequency
python3 scripts/keyword_deterministic_core.py <command> --input <input.json> --output <output.json>
python3 scripts/run_runtime_fixtures.py
```

本机规格和无凭据登录状态的字段示例分别见`contracts/run-spec.example.json`和`contracts/source-preflight.example.json`。test-validation规格还必须增加`qa_mode=compact-validation|full-regression`；`change_flags`非空时运行器只接受`full-regression`。
