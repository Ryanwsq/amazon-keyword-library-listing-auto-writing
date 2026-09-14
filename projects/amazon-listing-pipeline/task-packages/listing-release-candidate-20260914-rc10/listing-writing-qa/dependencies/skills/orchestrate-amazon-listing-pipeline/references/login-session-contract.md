# 任务会话登录合同

本合同只管理`full_pipeline`在真实网页或SIF MCP业务动作之前的会话级登录证明，不保存或传递任何密码、验证码、Cookie、令牌或浏览器配置。它不能替代各业务Skill自己的来源、权限、站点和停止规则。

## 输入后立即执行

1. 用户填写主输入工作簿；`新品基础信息.市场选择`锁定站点，`登录准备`只登记SIF和卖家精灵的账户别名、非敏感凭据引用及登录方式。
2. 主任务先把站点摘要和下面八个任务会话逐项下发到实际拥有任务，再引导用户一次性完成登录准备。
3. SIF竞品反查按`SIF MCP > SIF官网`执行，SIF任务先核验本机MCP、权限与当前Task/host鉴权，不先要求网页登录或逐Run重复批准MCP例外。MCP不可用/不完整时才按关键词拥有合同取证、登记未完成ASIN并准备官网备用。卖家精灵仍优先网页，可按`登录准备`使用已保存凭据/密码管理器或用户手动（引用可空）；Amazon仍由用户逐任务手动登录。
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
| `keyword:sellersprite-collector:sellersprite` | 关键词卖家精灵扩词 | 卖家精灵 | `keywords` | 用户手动、已保存凭据或本机密码管理器 |

一个`task_id + host`只能满足一个逻辑会话。任务合并、侧栏缺失或主任务可见页面都不能缩减矩阵；任务身份不明确时先核对项目、角色、Task ID、host、cwd和派发ID。

## 回执字段与验证

`pipeline_state.py confirm-login-session`逐会话登记以下非敏感字段：

- `session_key/project/role/provider`；
- `task_id/host/dispatch_id`；
- `status`：网页为`authenticated_web`；新SIF首选为`authenticated_mcp`。旧`user_approved_same_provider_mcp`仅兼容原已锁Run，不作为新Run默认；
- `observed_domain/postal_code/assistant`：MCP不伪造网页域名，`authenticated_mcp`可不填；Amazon必须与当前Run锁定路由完全一致，需要购物助手的角色还必须验证Alexa或Rufus；
- Run证据目录内的`evidence_file`及自动计算的SHA-256、字节数、验证时间；
- 新SIF MCP使用`mcp_authenticated=true`及下述当前身份鉴权文件，不要求`user_approval_ref`；SIF网页备用须另提供`--sif-fallback-evidence`。

新Run锁定`source_policies.sif_competitor=mcp-first-20260911`。SIF备用按关键词拥有合同：MCP不可用或不能完整完成原锁查询时，保留原因和未完成ASIN，登录同提供商官网备用；实际鉴权失败、错站或权限不明仍停止并通知用户，不能借切换入口绕过。允许的行级指标缺失、来源未返回日期或真实零结果不因此重采。已完整成功的ASIN不重复查询，不跨入口补单行指标，来源人口/周期/七列/300条不变。卖家精灵/SIF登录失效时，只有本机浏览器已自动填满账户和密码才允许点一次登录并复核原锁；不得读取、复制、显示、补填或记录凭据。空白/部分填充、验证码/MFA、失败、错账号/站点或再次跳转仍交用户处理。

### SIF当前任务证明

新MCP的`evidence_file`是JSON，字段严格为`schema=amazon-keyword-mcp-authentication/v1、run_id、task_id、host、provider=SIF、entry_type=mcp、authenticated=true`，可附非敏感`checked_at`。必须与本次Listing Run/Task/host完全一致，不接受只填hash或布尔自报而没有身份内容；拥有任务仍须实际验证服务可用。关键词创建自己的Run后另按关键词合同绑定，不能将Listing Run证明包装为关键词Run证明。

网页备用的附加证据必须位于当前Run证据目录，使用`schema=listing-sif-web-fallback/v1、run_id、task_id、host、provider=SIF、entry_type=mcp、reason=mcp_unavailable|mcp_incomplete`，可附`checked_at`；主任务核对真实不可用观察，不以原因字符串代替实际来源事实。这只满足入口准备，正式关键词查询仍须其拥有合同的原查询锁、失败证据与未完成ASIN闭环。没有MCP原因不能因网页已登录就跳过优先入口。源策略、回执状态和证据均保留哈希；历史Run不补新策略或静默改门。

证据只能证明当前任务、当前host、当前Run的可用会话，不能包含账号密码、验证码、Cookie、令牌或可复用认证材料。任务ID和真实证据路径属于本机Run数据，不进入公开任务包或Git。

全部回执后运行`finalize-login-gate`。如果任一会话过期、登出、跳站或任务重建，运行`invalidate-login-session --reason <原因>`；状态机只阻断该会话直接依赖的阶段，其他已验证且无依赖关系的阶段可继续。重新登录后为同一会话登记新证据，再重新完成总门。

## 站点与异常

- Amazon-US固定`amazon.com/10001/Alexa for Shopping/English`；Amazon-DE固定`amazon.de/80539/Rufus/German`。
- 页面进入其他站点时，标记`marketplace_mismatch`并通知用户介入；不能自行以美国站结果补德国站。
- 德国站Rufus无可靠`New Chat`且刷新后上下文可能保留；各相关Skill继续使用包含目标ASIN的固定德语问题。面板已经可见时不得再次点击开关将其隐藏。
- 用户拒绝或无法完成某个必需登录时，保留`pending/reauth_required`并只报告依赖阶段阻断；不得把技术未执行写成“无结果”。
