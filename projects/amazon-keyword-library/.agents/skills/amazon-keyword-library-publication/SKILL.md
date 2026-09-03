---
name: amazon-keyword-library-publication
description: Publish reviewed, sanitized Amazon keyword knowledge into the existing project topic with provenance and status boundaries. Use for稳定知识同步、索引更新、版本说明或脱敏导入；do not use for raw archive copying, unreviewed research, shared memory, public Skills, cross-project rules, commits or external publishing without explicit authorization.
---
# Amazon Keyword Library Publication

## 目标

把经审查的项目知识写入正确拥有文件，避免重复、敏感泄露和状态夸大。

## 输入

主任务授权、已复核候选结论、来源与适用范围、当前知识索引、变更目标和排除清单。

## 输出

更新后的项目知识、索引、状态说明、脱敏变更摘要和验证报告。

## 可调用能力

- `keyword.library.publish`

## 执行步骤

1. 完整读取 `knowledge/index.md`、`../../../docs/end-to-end-workflow.md` 和 `../../../docs/keyword-judgment-boundaries.md`，确认现有主题拥有文件、当前流程和当前版本。
2. 将候选项分为 imported、local-only evidence、excluded 和 needs decision。
3. 对 imported 项逐条确认来源、稳定性、适用范围、复核日期和用户确认状态。
4. 更新已有主题；只有没有主题拥有者时才创建新知识文件。
5. 分离知识事实、判定边界和执行流程，并同步索引与版本状态。
6. 真实验证产生规则修正时，把旧工作簿标记为旧规则证据；只有重跑并形成去向差异后，才能把新运行结果写成当前验收证据。正常案例因必选来源`not_executed`时保持“进行中”，不得改称通过或边界案例。
7. 创建或扩展 Skill 前检查是否有用户明确授权，以及稳定输入、来源、输出字段、异常和停止门；未确认阈值只能作为`待确认`写入 draft Skill，不能注册成已验证判断或假装完成运行。
8. 修改任何项目知识或 Skill 时，同批更新端到端说明的同步信息和受影响章节；没有流程影响时也明确记录已复核。
9. 扫描凭据、个人信息、内部地址、源电脑路径、任务 ID 和原始业务数据；用户对具体材料明确免除重复扫描时，记录该决定和本次未执行状态，不伪称已扫描。
10. 运行仓库验证与差异检查，回传变更和风险；commit、push 或外部发布需要另行明确授权。

## 质量标准

- 只迁入稳定、可复用和已脱敏内容。
- 所有候选项有四类归属，排除项不进入 Git 历史。
- 已确认、候选和未完成状态清晰，不以 P0 代替 P1。
- 未完成业务板块没有被注册为空壳 Skill；获准 draft Skill 的计划能力、待确认阈值和未验证状态均被如实标记。
- 知识索引、版本说明和实际文件一致。
- 知识或 Skill 变更与端到端说明保持同批同步。

## 异常处理

发现凭据、身份或联系信息、未经授权公司材料、归属不清、规则冲突或跨项目影响时停止相关导入；保留脱敏问题描述并请求总控或用户决策。
