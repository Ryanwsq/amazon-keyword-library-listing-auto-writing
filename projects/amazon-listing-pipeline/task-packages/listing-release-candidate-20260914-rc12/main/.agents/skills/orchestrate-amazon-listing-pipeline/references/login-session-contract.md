# 任务会话登录合同

本合同只管理`full_pipeline`在真实网页或SIF/卖家精灵MCP业务动作之前的会话级登录证明，不保存或传递任何密码、验证码、Cookie、令牌或浏览器配置。它不能替代各业务Skill自己的来源、权限、站点和停止规则。

## 输入后立即执行

1. 用户填写主输入工作簿；`新品基础信息.市场选择`锁定站点，`登录准备`只登记SIF和卖家精灵的账户别名、非敏感凭据引用及登录方式。
2. 主任务先把站点摘要和下面八个任务会话逐项下发到实际拥有任务，再引导用户一次性完成登录准备。
3. SIF竞品反查按`SIF MCP > SIF官网`执行，SIF任务先核验本机MCP、权限与当前Task/host鉴权，不先要求网页登录或逐Run重复批准MCP例外。MCP明确报错时才按关键词拥有合同取证、登记未完成ASIN并准备官网备用。卖家精灵也优先MCP，仅明确报错后由主任务提示用户登录官网，可按`登录准备`使用已保存凭据/密码管理器或用户手动（引用可空）；Amazon仍由用户逐任务手动登录。
4. 每个任务验证自己的实际入口、身份和站点后生成一份本Run本地证据并独立回执。主任务不能用自己的Cookie、截图或“其他任务已登录”代替。
5. 新Run锁定`login_gate_policy=per-stage-20260914`：各分支自己的会话和数据依赖就绪即全图扫描并派发，不等待无关登录，不再要求用户重复说“开始”。八份回执全部就绪后仍须完成`login_gate`汇总；未登录的分支不得采集。旧Run未锁此策略时保留全部回执收口后才能采集的原合同，不静默升级。已授权范围之外的动作仍不自动执行。当前运行身份和恢复见[恢复合同](runtime-recovery-contract.md)。

## 固定任务会话矩阵

| session_key | 实际拥有任务 | 服务 | 依赖阶段 | 登录责任 |
|---|---|---|---|---|
| `listing:product-audit:amazon` | Listing商品审计 | Amazon | `product_audit` | 用户手动 |
| `listing:five-dimension-insights:amazon` | Listing五维洞察 | Amazon | `market_insights` | 用户手动 |
| `listing:tag-priority:amazon` | Listing标签优先级网页核验 | Amazon | `tag_priority` | 用户手动 |
| `listing:painpoint-frequency:amazon` | Listing痛点频率 | Amazon | `pain_points` | 用户手动 |
| `listing:painpoint-phrasing:amazon` | Listing痛点口语表达 | Amazon | `painpoint_phrasing` | 用户手动 |
| `keyword:autocomplete:amazon` | 关键词Amazon联想 | Amazon | `keywords` | 用户手动 |
| `keyword:sif-collector:sif` | 关键词SIF竞品反查 | SIF | `keywords` | 首选MCP鉴权；官网备用才用用户手动、已保存凭据或本机密码管理器 |
| `keyword:sellersprite-collector:sellersprite` | 关键词卖家精灵扩词 | 卖家精灵 | `keywords` | 首选MCP；仅明确报错后提示用户登录官网 |

一个`task_id + host`只能满足一个逻辑会话。任务合并、侧栏缺失或主任务可见页面都不能缩减矩阵；任务身份不明确时先核对项目、角色、Task ID、host、cwd和派发ID。

## 回执字段与验证

`pipeline_state.py confirm-login-session`逐会话登记以下非敏感字段：

- `session_key/project/role/provider`；
- `task_id/host/dispatch_id`；
- `status`：网页为`authenticated_web`；新SIF/卖家精灵首选为`authenticated_mcp`。旧`user_approved_same_provider_mcp`仅兼容原已锁Run，不作为新Run默认；
- `observed_domain/postal_code/assistant`：MCP不伪造网页域名，`authenticated_mcp`可不填；Amazon必须与当前Run锁定路由完全一致，需要购物助手的角色还必须验证Alexa或Rufus；
- Run证据目录内的`evidence_file`及自动计算的SHA-256、字节数、验证时间；
- 新SIF/卖家精灵 MCP使用`mcp_authenticated=true`及下述当前身份鉴权文件，不要求`user_approval_ref`；两者网页备用须另提供`--mcp-error-evidence`与`--web-login-notice`，另有真实web鉴权JSON。

新Run同时锁定source_policies.sif_competitor及sellersprite_expansion=mcp-first-error-only-20260914。两个来源均MCP优先，只允许明确MCP报错后提示用户登录官网备用；零、缺字段、不完整响应、缺页及保存失败不是MCP报错。错站、权限、账户冲突/验证码不能借入口切换绕过，需用户介入。人口、窗口、字段及完整性判断保持关键词拥有合同，已完成查询不重采。

### 当前任务证明

两者MCP的evidence_file字段严格为：schema=amazon-keyword-mcp-authentication/v1、run_id、task_id、host、provider（SIF或SellerSprite）、entry_type=mcp、authenticated=true，可附checked_at。与当前Listing Run及拥有任务身份一致；关键词另建Run后须按其合同重新核验绑定，不复制布尔值。

网站备用须三项真实证据，均在当前Run evidence目录：

- evidence_file：同身份、schema=amazon-keyword-web-authentication/v1、entry_type=web、authenticated=true，可附checked_at。
- --mcp-error-evidence：schema=listing-source-mcp-error/v1、run_id、task_id、host、provider、entry_type=mcp、is_error=true、非空error_code、evidence（非空原始错误{path,sha256}数组），可附checked_at。代码核对哈希和身份，拥有任务核验确为真实MCP错误而不是数据缺口。
- --web-login-notice：schema=listing-source-web-login-notice/v1、run_id、task_id、host、provider、login_requested=true，可附checked_at。先向用户要求在该任务登录，再记通知；通知不等于登录成功。

以上仅满足入口准备，正式关键词调用另需其拥有合同的原查询锁/错误/未完成人口闭环。网站既有登录不能跳过MCP。旧20260911 SIF policy及--sif-fallback-evidence仅保留原冻结Run兼容，不用于新Run。登录失效后已完全自动填充表单的一次按钮恢复仍按原来源安全门，不读/补填/记录凭据，失败或挑战交用户。

证据只能证明当前任务、当前host、当前Run的可用会话，不能包含账号密码、验证码、Cookie、令牌或可复用认证材料。任务ID和真实证据路径属于本机Run数据，不进入公开任务包或Git。

全部回执后运行`finalize-login-gate`。如果任一会话过期、登出、跳站或任务重建，运行`invalidate-login-session --reason <原因>`；状态机只阻断该会话直接依赖的阶段，其他已验证且无依赖关系的阶段可继续。重新登录后为同一会话登记新证据，再重新完成总门。

## 站点与异常

- Amazon-US固定`amazon.com/10001/Alexa for Shopping/English`；Amazon-DE固定`amazon.de/80539/Rufus/German`。
- 页面进入其他站点时，标记`marketplace_mismatch`并通知用户介入；不能自行以美国站结果补德国站。
- 德国站Rufus无可靠`New Chat`且刷新后上下文可能保留；各相关Skill继续使用包含目标ASIN的固定德语问题。面板已经可见时不得再次点击开关将其隐藏。
- 用户拒绝或无法完成某个必需登录时，保留`pending/reauth_required`并只报告依赖阶段阻断；不得把技术未执行写成“无结果”。
