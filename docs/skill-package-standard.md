# Agent and Skill package standard

- Status: active
- Last reviewed: 2026-09-03
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

本独立仓库当前使用仓库根`.agents/skills/<skill-purpose>/`。未来若迁入多项目仓库，可在另行确认并完成发现/路径/验证适配后采用`projects/<project>/.agents/skills/<skill-purpose>/`；该形式不是当前已生效入口。目录名、`SKILL.md` frontmatter `name` 和 `capabilities.yaml` 中的 `skill.name` 必须一致。

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

### Dependency integrity

`contracts/skill-dependencies.json`登记本项目十二个Skill的唯一仓库入口、共享资料和必需模块资源；它只拥有文件依赖，不拥有业务规则、必读顺序、运行状态或P1。各包现有文件随包检查，已登记资源缺失不能因目录扫描未找到而被静默忽略。共享知识继续引用唯一拥有文件，不复制成多份可编辑规则。

`scripts/validate_skill_dependencies.py`已接入原仓库P0，检查包清单与实际入口、必需知识索引/合同/脚本/资产、当前包中的显式本地源引用、项目知识索引目标、静态脚本依赖、路径越界、同名身份以及已接纳/候选案例文件存在性。planned槽位不要求伪造案例。裸业务产物名和历史案例正文不作为当前源依赖；动态运行依赖、外部服务可用性、自然语言规则是否完整仍须由原Skill/合同及运行检查确认。

默认只解析当前仓库声明的路径，不在用户全局Skill目录寻找替代品。可显式传入额外发现范围检查同名来源；发现重复即失败，不因文件相同而任选一份。多项目仓库、插件或其他机器的实际装载范围不在本次自动发现范围内，不能宣称已验证。

```text
python3 scripts/validate_repository.py
python3 scripts/validate_skill_dependencies.py --json
python3 scripts/validate_skill_dependencies.py --additional-skill-root <明确获准的其他Skill根>
python3 scripts/test_skill_dependencies.py
```

检查器只读，JSON输出为仓库相对文件清单、各任务依赖关系和当次SHA-256，不写报告、不加载外部Skill、不改变本机任务。清单哈希不能代替完整读取，也不能替代Run合同的revision/输入/规则哈希锁。依赖增删须同步清单并保留原检查与测试；检查器变更后的真实test-validation仍按既有条件执行full-regression，不以本地夹具冒充P1。

### P1: runnable verification

- 在同一已锁定规则 revision 的受控环境中真实执行三种案例。
- 两个正常案例完成核心步骤并满足质量标准。
- 边界案例不编造、不越权，并按规则停止或升级人工。
- `planned` 或 `unavailable` 的关键能力没有被假装调用成功。
- 三个案例槽位均已由用户确认并登记为 `accepted`，且三个实际案例文件齐全。

P1 通过后才能把 `maturity` 改为 `verified`。MCP 采纳、生产部署、监控和企业正式可用属于后续技术阶段，不能由 P0/P1 自动推出。

## Template

本独立仓库未分发单独的Skill模板目录；本文件上方的目录树、必需标题与能力字段示例就是建包结构入口。只有用户授权创建具体Skill时，才在当前`.agents/skills/<skill-purpose>/`下按这些要求建立实际文件；无需寻找或复制一个不存在的模板目录。

按真实依赖保留完整知识索引、直接合同和所需脚本/模板，不为凑结构创建空壳资源。案例索引先登记真实状态，未执行的案例只保留槽位，不复制其他Skill证据、虚构案例或登记已验证能力。此入口修正不改变任何现有Skill的必需内容、业务步骤或P0/P1门槛。
