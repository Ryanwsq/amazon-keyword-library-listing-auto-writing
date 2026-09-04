# 输出合同

## Run 目录

每次运行创建独立目录：

```text
runs/<Run_ID>/
├── run-manifest.json
├── locked-input/
│   └── 00_锁定输入.xlsx
├── outputs/
│   ├── 01_竞品Alexa五维洞察并集.xlsx
│   ├── 02_Alexa商品信息审计.xlsx
│   ├── 03_本品优势与卖点排序.xlsx
│   ├── 04_竞品Alexa痛点频率统计.xlsx
│   ├── 05_Amazon标签优先级决策.xlsx
│   ├── 06_SKU可用关键词库.xlsx
│   ├── 07_核心卖点决策包.xlsx
│   ├── 08_Alexa痛点口语表达.xlsx
│   ├── 09_埋词与标签映射.xlsx
│   └── 10_Amazon Listing交付.xlsx
└── evidence/
    └── <各依赖 Skill 的原始问答、状态和证据>
```

在 `downstream_intake` 模式下，`locked-input/` 改为保存或登记原始产品基础输入、上游交付清单、manifest、01–05 的来源路径与逐文件 SHA-256；不得为迎合单一输入结构而合并或改写封存工作簿。关键词链路还须登记“发往 Amazon 关键词主任务的输入 → 回传至 SKU 副线程的完整关键词总工作簿 → 06”的两段 Run_ID、路径与 SHA-256。

`08` 为可选输出；跳过时不得用空文件占位。

## 文件所有权

| 文件 | 唯一负责模块 |
|---|---|
| 01 | extract-amazon-product-insights |
| 02、03 | audit-alexa-shopping-product-info |
| 04 | alexa-painpoint-frequency |
| 05 | prioritize-amazon-insight-tags |
| 06 | Amazon关键词词库主任务提供总表；本项目独立SKU可用关键词库副线程负责最终处理；总控负责调度与校验 |
| 07 | 本总控 Skill 的卖点决策阶段 |
| 08 | alexa-painpoint-phrasing |
| 09 | 本总控 Skill 的埋词分配阶段 |
| 10 | 本总控 Skill + apply-amazon-listing-hard-rules |

总控只能复制、编号和登记依赖输出，不能回写改变其状态、公式或事实。

## 07_核心卖点决策包.xlsx

该固定文件名为跨阶段兼容接口；文件内容承担“信息校准与初步排布决策包”职责。

固定 Sheet：

1. `标签优先级确认`
2. `卖点优劣势确认`
3. `痛点与样本限制`
4. `P0卖点选择`
5. `主图初步排布`
6. `A+初步排布`
7. `未决规则`
8. `证据与冲突`
9. `人工确认`

`人工确认` Sheet 在七类对象全部确认前保持待确认；确认后写入校准文件 SHA-256 和完整记录，但不删除原始建议、候选、限制或修改轨迹。

## 09_埋词与标签映射.xlsx

固定 Sheet：

1. `关键词分配`
2. `标签落位`
3. `字段预算`
4. `排除词与原因`

## 10_Amazon Listing交付.xlsx

历史 schema 1.0 保留以下原七 Sheet；新建 schema 2.0 在保留七 Sheet 后追加七 Sheet，固定为 14 Sheet。详细字段、显示方式和无损来源复制见项目知识库 `final-workbook-presentation.md`。

原七 Sheet：

1. `确认主张`
2. `标题与亮点`
3. `五点与Search Terms`
4. `图片方案`
5. `A+方案`
6. `规则校验`
7. `埋词覆盖`

新版追加：

8. `SKU可用关键词库`
9. `品类产品通用词库`（保持本名，不等于上游独立“二类词”Sheet，也不等于F2二级词子集）
10. `关键词趋势性分析`
11. `关键词竞争性分析`
12. `标签优先级展示`
13. `卖点与配置优先级展示`
14. `痛点频率与重要级展示`

四张来源表只从当前验收的 06 搬入，不重算；三张展示表只投影已确认 07。07 的内部九 Sheet 和 09 的四 Sheet 均不因展示合并而删改。

上游独立“二类词”是否额外交付仍待用户明确，不因消除命名歧义而增加06/10 Sheet或扩大Listing词源。跨项目附加对象和正式回执使用[关键词交接合同](keyword-handoff-contract.md)，不另造字段版本。

原表复制按preserved-sheet-transfer.md执行：用户已授权底层OOXML保真搬入，必须验证公式/缓存、样式与图表关系闭包；正文和展示表继续使用表格Skill工具。缺依赖不降级为静态值。

06缺表时暂停该表装配，交回SKU关键词任务按当前锁定来源补齐并重新验收；不得由最终装配任务自行拼入历史包。已授权的历史关键词复用仍先经过当前Run的06接口。

## 文案交互证据（新版）

`evidence/copy-review/<revision>.json` 保存 Run_ID、ASIN、完整标题/IH/全部 Bullet及实际条数/写法版本、源文件路径与哈希，具体合同见 `stage-copy-review.md`。聊天预览须展示实际正文，确认后将精确正文哈希写入 manifest；不得用“已确认卖点”代替“已确认文案”。

09 在文案确认前为落位计划，实际次数、实际占用留空；确认后生成最终 ST 并回填真实计数，再装配 10。

## run-manifest.json

至少记录：

- schema_version、run_id、created_at、updated_at；
- 原始输入路径、锁定输入路径、SHA-256；新版另有已核对的 `input.product_asin`；
- 每个阶段的状态、开始/结束时间、消息和输出；
- 人工确认状态、七类确认范围、校准文件路径及 SHA-256、P0 候选 ID、最终主张和确认时间；
- 新版 `listing_draft`、`copy_checkpoint` 阶段及实际文案文件、登记SHA-256、ASIN、非空版本、确认人/时间、来源锁、已确认正文快照、重开历史；
- 新Run的`writing_rules_version=v2.2`及`bullet_count_policy=coverage_based_5_to_6`；至少5条、通常5–6条，超过6条的确认依据见草案合同；历史Run缺写法版本或条数policy仍沿用各自旧版，不静默迁移；
- `pipeline_contract_version`，用于区分历史七 Sheet/单确认门与新版十四 Sheet/双确认门；
- 全部状态变更事件。

状态脚本以原子替换方式保存 JSON，避免中断造成半写文件。

## 交付摘要

最终聊天摘要只报告：

- Run_ID 和是否完成；
- 有效/排除竞品数及样本状态；
- 已确认核心主张；
- 已生成文件；
- 仍存在的事实、访问或合规风险。

不得把试算结果包装成正式市场结论，不得声称内容已通过 Amazon 审核。
