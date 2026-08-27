# Agent and Skill package standard

- Status: active
- Last reviewed: 2026-08-27
- Purpose: 统一仓库中公共与项目专用 Skill 的角色边界、能力登记、知识依赖和真实运行证据

## Directory naming

实际 Skill 直接以作用命名，不使用 `submission/` 外壳：

```text
.agents/skills/<skill-purpose>/
├── Agent.md
├── SKILL.md
├── capabilities.yaml
├── knowledge/                    # only when fixed knowledge is required
│   └── index.md
└── evidence/
    ├── index.md                  # draft / verified 均必需；只登记槽位，不等于P1证据
    ├── case-01-normal.md         # 对应案例被接纳后存在
    ├── case-02-normal.md         # 对应案例被接纳后存在
    └── case-03-edge-or-error.md  # 对应案例被接纳后存在
```

项目专用 Skill 使用同样结构，放在 `projects/<project>/.agents/skills/<skill-purpose>/`。目录名、`SKILL.md` frontmatter `name` 和 `capabilities.yaml` 中的 `skill.name` 必须一致。

## Maturity

`capabilities.yaml` 必须声明：

```yaml
skill:
  name: example-skill
  maturity: draft            # draft / verified
  last_verified: null
```

- `draft`：P0 结构可以合格，但尚未完成真实三案例运行，不得声称 Skill 已训练完成。
- `verified`：必须存在两个正常案例和一个边界/异常案例的真实执行记录，并且所有被引用能力均已验证可用。

模板、AI 推演或事后补写的“看起来正确”结果不能作为 evidence。

## Agent.md

描述角色在什么场景工作、负责什么结果、何时使用、可调用哪些 capability ID，以及何时必须停止并升级人工。至少包含：

```markdown
# Agent 名称

## 业务场景
## 负责的结果
## 使用时机
## 可调用能力
- `capability.id`
## 禁止事项与人工升级条件
```

Agent 是职责和边界，不是永久 Git 分支，也不绑定设备本地任务 ID。

## SKILL.md

`SKILL.md` 保留 Codex 项目 Skill 所需的 YAML frontmatter，并至少包含：

```markdown
---
name: example-skill
description: 清楚说明何时应该和不应该触发
---

# Skill 名称

## 目标
## 输入
## 输出
## 可调用能力
- `capability.id`
## 执行步骤
## 质量标准
## 异常处理
```

它描述可重复 SOP，不保存某次聊天记录或虚构执行结果。

## capabilities.yaml

每项能力使用稳定 ID，`Agent.md` 与 `SKILL.md` 只能引用已登记 ID：

```yaml
capabilities:
  - id: report.draft.generate
    type: mcp                 # api / cli / mcp / manual
    purpose: 根据获准输入生成报告草稿
    status: planned           # planned / verified / unavailable
    input: 已脱敏业务数据
    output: 结构化报告草稿
    permission: read-only
    risk: 不得写入生产系统；信息不足时升级人工
```

`planned` 只表示工具化需求，不能在 Skill、证据或说明中描述为已可用。真实密钥、Token、Cookie、生产地址和生产数据不能进入本文件。

## knowledge/index.md

只有 Skill 依赖固定业务资料时才创建。索引至少记录：知识 ID、内容、来源或获准链接、适用范围、更新日期和使用方式。末尾必须声明：资料无法确认时，输出“不确定”并交人工确认。

## evidence

每个 Skill 从 `draft` 阶段起就必须有 `evidence/index.md`。索引至少记录 Skill 名称、当前 maturity、P1 总状态，以及下列三个固定槽位：

- `case-01-normal.md`
- `case-02-normal.md`
- `case-03-edge-or-error.md`

每个槽位记录案例类型、登记状态、锁定 revision、脱敏案例引用和验收状态。允许的登记状态为 `planned / running / candidate / accepted / rejected`。空索引、`planned` 槽位或只有登记行都不构成案例证据，不得据此把 P1、maturity 或 capability 标成已验证。

正式验证期间规则和 Skill 包只读，运行产物只进入获准的本地 Run 目录。Run 结束并经用户确认后，才在获准迭代/发布批次把脱敏证据写入对应案例文件并更新索引；不得将历史运行、模板、AI 推演或事后补写结果追认为真实案例。

`verified` Skill 至少提交：

- `case-01-normal.md`：常见任务。
- `case-02-normal.md`：更换同类输入验证可重复性。
- `case-03-edge-or-error.md`：缺少信息、异常输入或权限不足时安全停止、提示或升级人工。

每个案例必须包含执行环境、输入、锁定 Git revision、实际执行步骤与能力 ID、实际输出、质量检查、人工修改或失败原因和结论。证据只描述实际发生的运行，不反向补写。一个端到端 Run 可以为实际执行到的每个 Skill 各贡献一个对应案例，但各 Skill 必须形成独立的模块证据，未执行或未通过自身质量门的模块不能借用整体验收结论。

## P0 and P1

### P0: package review

- 目录和必需文件存在。
- 每个 Skill 都有 `evidence/index.md`，三个固定槽位及其状态完整；索引不得冒充实际证据。
- Agent 与 Skill 包含规定内容。
- capability ID 引用完整且字段合法。
- 固定知识有来源、范围和日期。
- 不含凭据、生产配置、敏感数据、软链接外逃或未经授权资料。

P0 通过只表示材料结构合格。

### P1: runnable verification

- 在同一已锁定规则 revision 的受控环境中真实执行三种案例。
- 两个正常案例完成核心步骤并满足质量标准。
- 边界案例不编造、不越权，并按规则停止或升级人工。
- `planned` 或 `unavailable` 的关键能力没有被假装调用成功。
- 三个案例槽位均已由用户确认并登记为 `accepted`，且三个实际案例文件齐全。

P1 通过后才能把 `maturity` 改为 `verified`。MCP 采纳、生产部署、监控和企业正式可用属于后续技术阶段，不能由 P0/P1 自动推出。

## Template

从 `templates/skill-package/` 复制文件到正确的 `.agents/skills/<skill-purpose>/` 后再填写。不要把模板目录本身当作可运行 Skill。
