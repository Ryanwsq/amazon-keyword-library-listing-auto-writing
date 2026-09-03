# Listing Skill包结构与依赖标准

结构版本：`listing-structure-2`；复核日期：2026-09-03。

采用关键词项目2026-09-03版包规范的角色、能力、知识与证据结构，不引入其关键词业务判断、Gate编号或案例结论。适用于本项目10个角色的所属Skill、完整参考副本及权威维护源。历史v1只读保留，不宣称其符合v2。

## 目录与唯一入口

每个Skill须有`Agent.md`、`SKILL.md`、`capabilities.yaml`、`knowledge/index.md`、`evidence/index.md`。固定知识索引引用已有正文，不再造可编辑的业务副本；自包含Skill可以索引自身SOP。目录名、frontmatter name和skill.name一致。

权威维护源为项目根`.agents/skills/<name>/`。每个部署角色包仅在`.agents/skills/<所属name>/`放一个执行入口；完整参考副本在`dependencies/skills/<name>/`，不得增加执行权。主任务保留全部Skill和知识，但非所属模块仍交给其负责角色。包外层AGENTS/Agent/LOAD_ORDER是角色加载协议，不代替每个Skill的标准文件。历史快照不纳入当前发现根。

## 必需内容

- Agent：业务场景、负责的结果、使用时机、可调用能力ID、禁止事项与人工升级条件。
- Skill：保留原SOP，补足目标、输入、输出、可调用能力、执行步骤、质量标准、异常处理导航；导航不改原规则、优先级或必读顺序。
- capabilities：稳定ID、type、purpose、status、input/output、permission/risk；skill记录name、maturity、last_verified。JSON语法是YAML1.2子集，本项目使用该严格子集以便无第三方依赖地解析，不冒称完整YAML解析。
- knowledge：知识ID、内容、获准来源、范围、索引复核日期、使用方式。原文更新日期不明写未声明，不以索引日期冒充原文更新时间。资料无法确认时输出“不确定”并交人工确认。
- evidence：Skill、maturity、P1总状态，以及两个正常和一个异常固定槽位；每槽位记录类型、planned/running/candidate/accepted/rejected、revision、脱敏引用和验收状态。未执行仅登记planned，不造案例文件。candidate/accepted必须有真实文件；verified要求同一已锁定revision的三个accepted案例和已验证能力。历史项目内验收保持原状态，本批新结构revision不追认历史为P1。

## 依赖与完整性

`contracts/skill-dependencies.json`列出唯一入口、必需文件、知识、依赖角色/外部能力、静态脚本依赖和当前SHA-256；仅拥有依赖，不拥有业务规则。`scripts/validate_skill_packages.py`只读校验必需结构、名称和能力ID、知识索引、案例状态、文件哈希、显式本地链接/源路径、静态同目录脚本依赖、语法、发现根重名与路径越界。

每个包在其锁定发现范围内检查；可显式提供额外发现根检测同名，不默认扫描全局目录或选取替代Skill。包中的dependencies完整资料仅参考。动态输入输出名、历史来源路径不是当前必需源依赖；外部工具安装/认证与真实运行另行检查，不能由静态校验推出。

来源保全对比v1锁：业务正文不删改；允许增加结构导航和移动部署引用目标、更新依赖发现适配器。逐项记录差异。原知识、判断边界、字段、问题/重试、样本、双人工门、06/07/09/10合同与业务脚本必须保全。真实业务回归未经启动授权不执行。

上述v1→v2结构保全记录不追溯修改。v3另经`AKW-LISTING-INTERFACE-20260903-01`授权，以v2为基线仅补关键词附加输入/READY回执、合法ABA缺失接收例外、通用词库/独立二类词/F2名称区分；白名单之外维护源不改，旧快照与历史产物按原哈希保全。每个差异记录旧/新哈希及diff，不伪称业务正文全部字节不变；06/10表数与SKU人口、事实/文本判断、Alexa来源和双确认门不变。

## 验证与发布范围

运行`python3 -B scripts/validate_skill_packages.py --json`与`python3 -B scripts/task_packages.py validate`；测试只在临时夹具中制造缺失、改值、重名和越界等异常，不改真实业务数据。

结构、依赖和机械流程验证不等于语义判断质量或业务P1。本包保留获准的历史来源与黄金示例，仍为LOCAL_ONLY_NOT_APPROVED_FOR_PUBLICATION；不宣称公共发布敏感信息审查、Alexa登录、Amazon后台或跨设备发现已通过。
