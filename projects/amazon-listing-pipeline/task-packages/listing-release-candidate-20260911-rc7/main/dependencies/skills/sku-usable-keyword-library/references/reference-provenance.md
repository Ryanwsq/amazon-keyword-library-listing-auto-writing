# 上游参考来源与继承边界

## 参考快照

- Package：`amazon-keyword-library-portable-20260831`
- Snapshot date：`2026-08-31`
- Source HEAD：`4a903057765e136c85c5dc4704178c076f3ce467`
- Source state：`working_tree_snapshot`
- 上游Skill状态：12个`draft`，能力均为`planned`，P1未完成。

本Skill仅参考该包中的稳定知识、判断边界和字段合同，不复制其成熟度声明，也不把上游Skill视为已验证能力。

## 已参考内容

- `docs/keyword-judgment-boundaries.md`：完整词、中心购买对象、配置连接、两级歧义及缺失值边界。
- `knowledge/product-keyword-library.md`：三去向、通用词库资格、分类动态列、竞争字段和最终总表结构。
- `knowledge/keyword-cleaning-case-evidence.md`：Gaming Chair等历史边界案例；具体词只作案例，不形成跨SKU固定词典。
- `.agents/skills/amazon-keyword-classification/`：动态语义列由词面支持、`长尾主分组标签`仅用于F5、分类不读取SKU事实。
- `.agents/skills/amazon-keyword-competition-analysis/`：`竞争性强度`含义及不得在下游改算。
- `.agents/skills/amazon-keyword-final-workbook-assembly/`：最终总表固定字段、动态列位置和上游字段血缘。
- `.agents/skills/amazon-keyword-quality-validation/`：只读验收、人口闭环、缺失不填0和行级证据原则。

## 继承的规则

- 英文原词是主判断文本；中文翻译只辅助阅读。
- 完整短语和中心购买对象优先于单个词根、标签、流量或来源。
- 缺失不等于0，未执行不等于无结果，范围外不等于缺失。
- 上游字段不在下游静默改写；判断必须保留稳定主键和逐行依据。
- 动态语义标签只能由上游原值机械汇总，不在SKU模块重分类。

## 明确不继承

- 三来源采集、流量OR门、品类清洗、通用词库资格重算、分类、词频、竞争、趋势、否词、广告和八Sheet交付流程。
- 上游“目标SKU缺少某配置不得影响品类相关/通用词库资格”的执行结果。本Skill是下游SKU精准可用阶段：关键词明确要求而SKU事实不支持的配置，只影响本模块的SKU事实匹配；品类关系与搜索意图不在本模块复判。
- 上游具体品类案例中的固定词去向。每个SKU仍按当前事实卡重新判断。
- 上游12个Skill的P1或verified声明；参考快照明确不存在这些状态。

## 冲突优先级

发生冲突时按以下顺序处理：

1. 当前用户对本项目和当前Run的明确要求；
2. 本Skill的SKU精准匹配合同；
3. 当前锁定SKU事实卡；
4. 上游工作簿字段原值和状态；
5. 便携包中的通用参考知识。

任何冲突不得通过改写上游数据消除；应停止受影响结论并回报主任务。
