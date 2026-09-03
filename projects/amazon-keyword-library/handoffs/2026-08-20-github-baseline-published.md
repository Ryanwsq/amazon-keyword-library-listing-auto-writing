# GitHub baseline published

- Status: private GitHub baseline published
- Date: 2026-08-20
- Logical role: keyword-main
- Sharing: sanitized

## Goal

为独立 Amazon 关键词词库建立可回读、可跨电脑继续的首个 GitHub 固定基线，不创建与长期 Codex 任务一一对应的永久 Git 分支。

## Result

- GitHub 私有仓库：`Ryanwsq/amazon-keyword-library`。
- 唯一长期基线分支：`main`。
- 本机远端：`origin` 指向该私有仓库的 HTTPS 地址。
- 本项目提交身份使用 GitHub noreply 邮箱；GitHub 凭据使用 Windows DPAPI 加密存储，不进入仓库。
- 十二个 Skill 继续保持 `draft`，全部能力继续保持 `planned`；仓库创建、提交和推送不构成 P1 证据。

## Included

- 独立仓库治理、项目状态、端到端流程和判定边界。
- 已确认的脱敏知识、版本决策、历史证据摘要和交接。
- 十个业务 Skill、两个项目维护 Skill及其直接合同。
- 长期主副任务的可同步逻辑架构；实际任务映射继续留在被忽略的本机文件。

## Excluded

- 原始聊天、自动记忆、终端历史、任务 ID、绝对路径和 Worktree 映射。
- ASIN/SKU运行数据、接口响应、XLSX/CSV/ZIP/PNG、浏览器状态和本地检查日志。
- Token、Cookie、MCP配置、账号授权细节和其他敏感信息。

## Validation

- P0仓库结构验证通过后才允许提交。
- 提交前执行Git差异空白检查、忽略规则检查和原始业务产物扫描。
- 推送后回读远端仓库可见性、默认分支和`main`提交，确认远端与本地提交一致。

## Branch boundary

- `main`是唯一长期分支，也是跨电脑继续的正式基线。
- 后续写入型任务使用`bootstrap/<topic>`、`work/<project>/<topic>`或其他获准短期分支；合并后删除。
- 长期Codex主任务和十个副任务不建立永久对应分支；并行写入时使用短期分支和Worktree隔离。

## Next gate

主任务锁定`main`上的当前revision和新`Run_ID`后，使用用户提供的新真实案例启动第一次正式只读验证；迁移前gaming-chair运行仍只作为问题发现证据。
