# Evidence registry

- Skill: `amazon-keyword-library-publication`
- Maturity: `draft`
- P1 status: `in_progress`
- Last reviewed: `2026-08-27`

## Case slots

| Evidence file | Required case type | Registry status | Locked revision | Sanitized case reference | Acceptance |
|---|---|---|---|---|---|
| `case-01-normal.md` | normal | candidate | `4a903057765e136c85c5dc4704178c076f3ce467` | `gaming-chair-evidence-publication-01` | pending user review |
| `case-02-normal.md` | normal | planned | pending | pending | pending |
| `case-03-edge-or-error.md` | edge-or-error | planned | pending | pending | pending |

## Evidence admission rules

- 本索引只登记槽位和状态，不是案例证据，不能单独支持 P1、`maturity: verified` 或 capability `status: verified`。
- 只接纳在同一已锁定 Git revision 上真实执行且由本 Skill 实际承担的案例；历史运行、模板、AI 推演和事后倒填不得占用槽位。
- 正常案例必须完成本模块核心步骤并通过模块质量门；`blocked`、`partial` 或 `not_executed` 不能占用正常案例槽位。
- 边界/异常案例必须真实触发预期的安全停止、降级、缺口保留或人工升级，并通过该行为的验收。
- 一个端到端 Run 只能为实际执行到的 Skill 各贡献一个对应槽位；每个 Skill 必须形成独立、可审计且引用自身 capability ID 的案例记录。
- 正式只读验证期间不修改本索引或规则文件。Run 结束、用户确认后，才在获准迭代/发布批次写入脱敏案例文件并更新登记状态。
- 原始业务输入、凭据、账号会话、Codex 任务 ID、绝对路径、原始工作簿、截图和日志不得进入本目录。

## Current status

已登记一个正常发布候选，等待用户复核本批跟踪变更后接纳；其余两个槽位为`planned`。Skill保持`draft`，P1未完成。
