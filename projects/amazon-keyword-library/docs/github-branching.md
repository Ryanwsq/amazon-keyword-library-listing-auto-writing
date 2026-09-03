# GitHub branch and review strategy

- Status: active
- Last verified: 2026-08-06
- Applies to: the whole knowledge workspace

## Design decision

`main` 是唯一长期 Git 分支和跨电脑正式基线。工作台任务、项目主任务与副任务是逻辑职责，不与永久 Git 分支一一绑定。所有写入型工作使用短期分支，合并后删除。

这避免了把“长期聊天角色”错误地等同于“长期分叉版本”，也避免为每台电脑、每个项目或每个知识主题维护不断漂移的分支。

## Allowed branch families

| Pattern | Use | Example |
|---|---|---|
| `bootstrap/<topic>` | 仅用于首次盘点、迁移和仓库初始化 | `bootstrap/company-inventory` |
| `shared/<topic>` | 公共记忆、公共 Skill 或跨项目规则 | `shared/memory-import` |
| `work/<project>/<topic>` | 单项目的一项普通工作 | `work/project-a/import-knowledge` |
| `fix/<scope>/<topic>` | 修复错误知识、Skill 或配置 | `fix/shared/validator-paths` |
| `maintenance/<topic>` | CI、模板、仓库维护 | `maintenance/pr-template` |
| `hotfix/<scope>/<topic>` | 已确认且需要快速处理的严重问题 | `hotfix/project-a/remove-secret` |

名称只使用小写字母、数字、点、下划线和连字符。一个分支只处理一个可审查目标。

## Branches not to create

- 不创建每台电脑一个永久分支。
- 不创建每个 Codex 任务一个永久分支。
- 不创建每个项目一个永久分支；项目由 `projects/<slug>/` 隔离。
- 不创建永久 `develop`、`knowledge` 或 `github-sync` 中转分支。
- 不让所有修改绕道同步分支；同步是角色和检查流程，不是版本中转站。

## Standard lifecycle

Start from a clean base:

```bash
git switch main
git pull --ff-only
git switch -c work/<project>/<topic>
```

Before proposing a commit:

```bash
python3 scripts/validate_repository.py
git diff --check
git status --short --branch
git diff
```

After explicit approval, commit, push and open a PR:

```bash
git push -u origin HEAD
gh pr create --fill
```

Use squash merge so `main` remains readable. Delete the remote and local work branch after the PR is merged and the result has been pulled back and verified.

## Parallel side tasks and Worktrees

当多个副任务会同时写文件时，每个任务使用自己的短期分支与 Worktree。只读副任务不必创建分支。Worktree 是本地隔离工具，不应把绝对路径提交到 Git。

主任务负责确保两个副任务不同时修改同一长期记忆条目、同一 Skill 或同一知识文章；无法避免时按顺序合并。

## Pull requests

- PR 标题说明范围和单一目标。
- 使用仓库 PR 模板完成政策、敏感信息、记忆和验证检查。
- 跨多个项目的改动必须解释为什么不能拆分。
- 普通知识修订、Skill 修改和记忆更新都通过 PR 形成可审查历史。
- 紧急敏感信息泄漏不应只依赖普通 PR；立即停止同步并按公司事件流程处理。

## Main protection

如果仓库套餐支持私有仓库 ruleset 或 branch protection，建议针对 `main` 启用：

1. 禁止删除和 force push。
2. 要求通过 PR 合并。
3. 要求 `validate` 状态检查成功。
4. 要求所有讨论已解决。
5. 要求线性历史并只启用 squash merge。
6. 合并后自动删除 head branch。
7. 团队仓库要求至少一位审查者；单人仓库不要设置会使自己永久无法合并的审批数量。

GitHub 官方当前说明：私有仓库的 rulesets 和 protected branches 需要 GitHub Pro、Team 或 Enterprise；个人 Free 私有仓库只能依靠 Actions、PR 模板和操作纪律，不能把文档规则误认为平台已强制执行。

## Conflict handling

不要 force push、不要重写已共享历史。发生冲突时先保存当前状态并报告具体文件；将最新 `origin/main` 合并到短期工作分支，解决并重新验证。对长期记忆冲突，优先由工作台主任务根据来源和复核日期裁决。

## Snapshots and recovery

- `main` 的 Git 历史是主要回滚机制。
- 完成首次公司迁移或重要知识库重构后，可以创建带说明的标签，例如 `snapshot-2026-08-company-import`。
- 标签用于里程碑，不替代日常提交或备份策略。
- 不在 Git 中保存凭据，即使计划随后删除；Git 历史可能长期保留它们。

## Official references

- [GitHub: Managing rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets)
- [GitHub: About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub: GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)
