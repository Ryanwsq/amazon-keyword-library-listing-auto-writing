# Amazon 关键词知识库公司归档导入交接

- Status: complete, pending workspace-main review
- Date: 2026-08-07
- Logical role: keyword-maintainer
- Branch: `work/amazon-keyword-library/import-company-archive-20260807`
- Source archive SHA-256: `3602826bb957febb849afe9e723060ea2fc96acfc6eaf7fd55880a5adbfa3443`
- Commit/push: authorized by user；最终提交 ID 和远端结果以 Git 历史及任务回传为准

## Outcome

公司电脑归档已完成本地安全检查、内容阅读、现有项目对照和脱敏提炼。项目基线更新为用户已确认的 V2.1，同时明确知识库尚未完成：第一板块框架已确认，第二板块完成四轮历史清洗案例与层级修正，第三板块尚未展开；下一项是词频分析细则。

根据用户补充要求，知识事实、判定边界和执行流程已经分层：

- 人类可读的完整输入、执行、判定和本机输出流程归 `docs/end-to-end-workflow.md`。
- 稳定领域知识归 `knowledge/product-keyword-library.md`。
- 历史案例证据归 `knowledge/keyword-cleaning-case-evidence.md`。
- 已确认版本决策归 `knowledge/keyword-decision-log.md`。
- 当前完成度、未完成项和下一步归 `PROJECT.md`。
- 判定门槛归 `docs/keyword-judgment-boundaries.md`。
- 已确认的采集、品类清洗分别归业务 Skill；知识发布和版本协调归项目维护 Skill。词频和 SKU 分类尚未完成，不创建 Skill。
- 后续修改任何项目知识或 Skill 时，必须在同一批变更中同步端到端说明；没有流程影响时也要记录已复核。
- 每完成一个项目阶段，或准备切换家庭电脑与工作电脑前，必须更新交接、验证并同步到 GitHub，作为跨电脑继续工作的检查点。

## Source safety result

- ZIP 完整性测试通过。
- 共 88 个条目；压缩后约 24 MB，解压后约 196 MB，压缩比约 8.14。
- 未发现加密条目、符号链接、绝对归档路径、路径穿越、NUL 文件名或归一化后的重复路径。
- 88 个文件名均使用 Windows 反斜杠；检查时只在临时目录归一化，不覆盖仓库文件。
- 清单包含 87 个受检条目；每个大小和 SHA-256 均匹配，清单自身是唯一未自列文件。

## Classification

### Imported

- V2.1 的一级品类核心大词、产品细分品类词与 SKU 精准适配分层修正。
- Sheet2 是清洗后品类相关关键词库；同品类细分类型不因目标 SKU 配置不同在第二板块删除。
- Sheet3 其他摘除与 Sheet4 直接替代的边界；Sheet4 允许为零。
- 第一板块需分别输出类目锚点卡和 SKU 事实卡。
- 搜索框联想使用主一级品类核心大词；扩词种子可以包含品类锚点、细分品类词和其他增量表达，去重后为 1–3 个。
- 四轮历史案例的脱敏行数、闭环结果和方法性结论。
- 当前阶段、未完成项、下一步和 V2.1 版本状态。
- 知识、判定边界、执行流程的分层，以及四个项目内单一职责 Skill 的 P0 草案：两个已确认业务 Skill 和两个项目维护 Skill。
- SIF MCP、Chrome 搜索框联想、卖家精灵 MCP 和十表工作簿的能力分解；用户已确认本机两个 MCP 均已连接，不重复进行连通性验证。
- 公司版 V0.1–V2.1 的完整版本修订链；只有 V2.1 是当前基线，被替代版本只用于追溯。
- 从用户输入到本机输出的人类可读端到端说明和强制同步门。

### Local-only evidence

- 完整可读对话和结构化对话记录。
- 原始和清洗后 XLSX、逐表渲染预览、检查结果、审计 JSON 和行级数据。
- 用于确认用户决策顺序、版本修正和案例真实性的原始材料。
- 来源清单中的源电脑路径和本机任务标识。

### Excluded

- ZIP 本体、完整聊天、原始或结果 XLSX、截图、检查日志、RawData、临时脚本和一次性导出。
- 外部分类研究草案；其状态仍是待确认，不能作为稳定规则。
- 已被 V2.1 吸收的搜索框研究过程，避免重复维护。
- 原始工作簿说明页中的联系信息和二维码等不必要内容。
- 凭据、Cookie、Token、账号授权、内部地址、人员或客户信息和财务敏感实际；未将任何此类内容写入仓库。

### Needs decision

- 词频分析的对象、分词、归并、停用词和统计阈值。
- 第三板块 SKU 精准适配状态、语义标签及多标签冲突顺序。
- 竞争性、趋势性分类的数据源和证据口径。
- Sheet3 否词候选与 Sheet4 扩量候选的下游发布门槛。
- 四个现有 Skill 的 P1 案例计划；当前均保持 `draft` / `planned`。
- 词频、SKU 分类、竞争性、趋势性和应用分类的具体规则；这些内容未完成，不创建空壳 Skill 或能力 ID。

## Spreadsheet verification

使用受控的本地工作簿读取与渲染流程检查四个最终案例：

| Case | Source rows | Sheet2 | Sheet3 | Sheet4 | Formula errors | Closure |
|---|---:|---:|---:|---:|---:|---|
| Paddle Board | 1,295 | 265 | 930 | 100 | 0 | pass |
| Gaming Chair | 2,000 | 151 | 1,232 | 617 | 0 | pass |
| Vanity | 2,000 | 627 | 1,373 | 0 | 0 | pass |
| Office Chair | 2,000 | 482 | 1,391 | 127 | 0 | pass |

所有工作表均完成结构检查、渲染和人工目视复核。案例发生在 Skill 拆分之前，所以没有据此把新 Skill 标为 `verified`。

## Files changed

- 重构项目知识基线和知识索引，并将历史案例证据、版本决策和当前状态从领域知识中分离。
- 新增端到端人类说明，并按“项目流程、关键定义和判定设置、当前进度”三部分组织输入、步骤、流程图、停止点、本机输出和知识发布。
- 新增统一判定边界文档。
- 把原 operations Skill 收窄为版本协调。
- 新增来源采集、品类清洗和知识发布三个单一职责 Skill；保留收窄后的版本协调 Skill。对照后移除了未完成的 SKU 分类空壳 Skill。
- 更新项目规则、项目状态、角色路由、Skill 知识索引和 Codex 项目级发现说明。

## Validation

- Repository validation: pass；19 个 Skills（18 draft，1 个仓库既有 verified），209 个仓库文件通过 P0 检查。
- Diff check: pass；`git diff --check` 无输出。
- Git status/stat: 位于要求的短期分支；11 个已跟踪文件修改，19 个项目内新文件，项目当前共 34 个文件；未暂存、未提交、未推送。
- Sensitive-data scan: GitHub 同步前复核私钥、AWS 访问密钥、赋值型凭据、邮箱和本机绝对路径，均为 0 命中；仅有历史废弃文档中的两个公开 Amazon 参考链接。
- URL review: 只有历史 V0.1 文档中的两个公开 Amazon 参考链接；本次新增文件没有外部网址。

## Suggested commit

`feat(amazon-keywords): import V2.1 baseline and split focused skills`

## Recommended next single-responsibility task

由项目主任务安排一个“词频分析规则研究”单一职责工作，只输出规则草案与待确认问题，不创建 Skill、不运行分类、不修改稳定知识。用户确认完整执行规则后，才决定是否新增词频或分类 Skill。
