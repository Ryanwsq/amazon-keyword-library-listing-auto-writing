# Single-responsibility Skill split

- Status: local packages created; repository P0 passed
- Date: 2026-08-20
- Logical role: keyword-main
- Sharing: sanitized

## Goal

在第一次正式只读验证前，把两个迁入组合 Skill 拆为长期副任务可独立拥有的单一职责包，并建立独立质量验证包；不改变已确认业务规则。

## Changes

- 来源：旧组合包拆为 SIF竞品反查、Amazon联想采集和卖家精灵扩词三个 draft Skill。
- 主任务：operations 新增三来源机械合并与第一板块十表总装合同；来源副任务之间不直接合并。
- 分析：旧竞争/趋势组合包拆为竞争性分析和趋势性分析两个 draft Skill。
- 质量：新增独立质量验证 draft Skill，只读复核 Run/revision、来源、主键、人口、版本、公式、渲染、Sheet和图表门。
- 旧组合包文件已移除；原包到新包的映射保留在任务角色和版本决策记录。

## Status boundary

- 当前项目共12个 Skill，全部为`draft`，能力为`planned`。
- 本次拆分与P0通过不构成P1；旧gaming-chair运行不反向成为新包证据。
- 实际长期副任务尚未创建；任务ID和Worktree只能进入被忽略的本机映射。
- 当前浏览器技术项、首轮正常案例重跑、Sheet3否词、广告资格和后置词库规则均未因此完成。

## Validation

- Standalone repository validator: final P0 passed for 12 draft Skills and 86 repository files after project-document synchronization.
- No external system, remote, branch, commit or task was created in this change.

## Next actions

1. 审查未跟踪迁移基线并形成可锁定的首个本地revision。
2. 创建长期副任务并只在本机忽略映射中记录实际ID。
3. 使用用户提供的新真实案例执行独立仓库第一次正式只读验证；本次拆分不生成P1。
