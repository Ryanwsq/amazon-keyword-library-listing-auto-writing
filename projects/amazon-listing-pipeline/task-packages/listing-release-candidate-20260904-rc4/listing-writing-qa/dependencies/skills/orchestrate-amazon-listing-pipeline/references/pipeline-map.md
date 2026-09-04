# 流程总图

## 原则

- `full_pipeline` 使用一张主输入工作簿；本项目默认 `downstream_intake` 使用已封存的 01–05 上游包与独立 06 关键词输出。
- 数据阶段是多条独立证据支线，不是一个输出覆盖另一个输出的线性改写链。
- 所有支线在“信息校准与初步排布决策包”汇合；为保持固定文件接口，文件名仍为 `07_核心卖点决策包.xlsx`。
- 新版有两个强制人工闸门：先确认七类信息决策与初步排布，再确认标题/IH/五点的实际正文。信息确认前不撰写正式正文；文案确认前不生成最终 ST 或最终装配。
- 每个阶段保持自己的来源边界、样本状态和失败语义。

## 阶段表

| 顺序 | 阶段键 | 依赖 Skill / 适配器 | 主要输入 | 固定输出 | 失败处理 |
|---:|---|---|---|---|---|
| 0 | preflight | 本 Skill 脚本 | 单一主输入或封存交付包 | 锁定输入/逐文件哈希、marketplace路由、预检记录、Run 清单 | 站点/结构阻断错误停止；警告继续并降级 |
| 0.5 | login_gate | 各实际拥有任务 + 本Skill状态脚本 | 锁定站点、`登录准备`与固定八会话矩阵 | 六个Amazon逐任务手动登录回执 + SIF/卖家精灵各自拥有任务回执 | `confirm-login-session`逐条登记，`finalize-login-gate`收口；失效只阻断直接依赖阶段 |
| 1 | product_audit | audit-alexa-shopping-product-info | 锁定输入 | 02、03 | Alexa 技术阻断记 needs_input |
| 2 | market_insights | extract-amazon-product-insights | 市场竞品 ASIN 池 | 01 | 保留已完成槽位；不得换来源 |
| 3 | tag_priority | prioritize-amazon-insight-tags | 锁定输入 + 01 | 05 | 少于 10 个有效竞品只允许试算 |
| 4 | pain_points | alexa-painpoint-frequency | 市场竞品 ASIN 池 | 04 | 少于 10 个有效 ASIN 不作为频率证据 |
| 5 | keywords | Amazon关键词主任务 + 独立SKU关键词副线程 | 锁定产品输入 → 完整关键词总工作簿 → SKU终筛 | 06 | 任一交接未完成、契约不符或产品身份不一致时 needs_input |
| 6 | selling_point_decision | 本 Skill + Spreadsheets | 02–06 + 锁定输入 | 07（七类信息校准与初步排布） | 证据不足仍输出候选/空位，但明确阻断项 |
| 7 | human_checkpoint | 本 Skill | 07 | 完整校准文件哈希与七类锁定记录 | 必须等待用户逐项确认、修改或否决；受影响布局需重排后再确认 |
| 8 | painpoint_phrasing | alexa-painpoint-phrasing | 04 | 08，可选 | 仅选中痛点型主张时执行 |
| 9 | keyword_allocation | 本 Skill + Spreadsheets | 已确认主张 + 05 + 06 | 09 | 未完成关键词阶段不得生成最终 ST |
| 10 | listing_draft | apply-amazon-listing-hard-rules | 已确认 07 + 09 计划 + 06 + Ground Truth | 实际标题/IH/五点草稿 JSON 与聊天预览 | 来源缺失或事实冲突停止 |
| 11 | copy_checkpoint | 主线程与用户 | 草稿与来源哈希 | 明确文案确认记录 | 未确认或正文/来源改变不得最终装配 |
| 12 | listing_generation | apply-amazon-listing-hard-rules + Spreadsheets | 已确认正文 + 09 计划 + 锁定来源 | 最终 ST、09 实际覆盖、10 的 14 Sheet | 不得静默改动已确认正文 |
| 13 | final_qa | 本 Skill + 硬规则 | 09/10 + 全部证据 | 最终 QA 状态 | 未通过不得标记 Run 完成 |

## 数据流

```text
锁定的产品基础信息与配置
  ├─→ Amazon关键词词库｜主任务｜main
  │       └─→ 完整关键词总工作簿
  │               └─→ 副线程｜SKU可用关键词库 ─→ 06 ─┐
  │                                                    │
单一输入工作簿或封存的01–05上游包                      │
  ├─→ 商品审计 ─→ 参数优势 / 原始卖点排序 ─┐
  ├─→ 五维洞察 ─→ 标签优先级 ───────────┤
  ├─→ 痛点频率 ─────────────────────────┤
                                             │
  └──────────────────────────────────────────┤
                                             ↓
                         信息校准与初步排布决策包（七类对象）
                                             ↓
                              人工逐项确认 / 修改 / 重排
                                             ↓
                  09埋词计划 → 标题/IH/五点完整草稿 → 人工文案确认
                                             ↓
                  最终ST + 09实际覆盖 → 10十四Sheet装配 → 硬规则与覆盖QA
```

## 调度规则

- 输入预检完成后，关键词阶段可以立即向 Amazon 关键词主任务下发锁定输入，并与阶段 1、2、4 并行等待；关键词项目回传后再串行进入本项目 SKU 终筛。
- `full_pipeline`在输入与marketplace锁定后先完成适用的统一网页登录门；`downstream_intake`不为已封存01–05重复登录，但新的关键词网页采集仍须完成Amazon/SIF/卖家精灵拥有会话登录。
- 阶段 1、2、4 逻辑上可独立，但同一个 Alexa 浏览器会话不得并发污染上下文。执行者可以顺序运行并保留并行证据结构。
- 阶段 3 必须等待阶段 2 完成。
- 阶段 6 等待阶段 1、3、4、5 全部进入终态；`needs_input` 允许形成不完整决策包，但必须携带缺口。
- 阶段 8 只在确认的主张确实使用某个上游标准化痛点时运行；否则标记 skipped。
- 阶段 9–13 必须等待七类校准对象全部人工确认；不能以只确认 P0 或 Top 1 候选代替完整确认。
- 09 计划阶段的实际次数/占用留空并标待正文确认，不可填 0 冒充已检查；`listing_generation` 和 `final_qa` 必须额外通过文案确认门。
- 状态顺序：`WAITING_HUMAN_CONFIRMATION` → `listing_draft` → `WAITING_COPY_CONFIRMATION` → 最终装配 → QA。
- 历史 schema 1.0 Run 保留原阶段与原交付合同；只有新建 schema 2.0 Run 默认启用双确认与 14 Sheet。

## 运行恢复

读取 `run-manifest.json` 后：

1. 验证锁定输入 SHA-256 未变化。
2. 跳过 `completed` 和 `skipped` 阶段。
3. 对 `needs_input` 或 `failed` 阶段，先检查阻断条件是否已解除，再切回 `running`。
4. 不重复成功的 Alexa 问题或已完成工作簿，只续跑未完成记录。
5. 恢复后继续使用同一 Run_ID、问题模板、语言、市场和样本口径。
