# Case 03 — SIF quota fallback

- Case type: `edge-or-error`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-sif-fallback-01`
- Execution environment: controlled local Amazon US run
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

三个获准直接竞品、最近30天口径和每个竞品300条业务明细上限。原始ASIN、账号会话、下载文件和本机路径不进入本证据。

## Capabilities actually exercised

- `keyword.source.competitor-traffic.query`
- `keyword.source.competitor-traffic.web-query`
- `keyword.source.sif.persist-and-verify`

## Execution and output

三次MCP请求均返回额度耗尽，模块没有把失败写成零结果。经用户授权后切换到同一SIF提供商的已登录官网完整导出，对三个锁定竞品重新完成查询。原始导出共4,486行，按合同保留900行业务明细并机械形成509个候选键；每个竞品均为300行，内部重复为零。

## Quality and deviations

- 入口切换未改变提供商、竞品集合、周期或字段。
- 原始证据先保存，再装配七列业务工作簿和候选摘要。
- 字段缺口按缺失保留，不补零；候选冲突为零。
- 模块状态为`complete`，但该次回退按治理规则属于边界案例。

## Conclusion

接纳为SIF Skill的边界案例：验证了额度耗尽时的同提供商官网备用和完整性闭环，不占用正常案例槽位。
