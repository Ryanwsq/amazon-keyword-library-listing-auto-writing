# 任务会话登录合同

本合同只管理`full_pipeline`在真实网页动作之前的会话级登录证明，不保存或传递任何密码、验证码、Cookie、令牌或浏览器配置。它不能替代各业务Skill自己的来源、权限、站点和停止规则。

## 输入后立即执行

1. 用户填写主输入工作簿；`新品基础信息.市场选择`锁定站点，`登录准备`只登记SIF和卖家精灵的账户别名、非敏感凭据引用及登录方式。
2. 主任务先把站点摘要和下面八个任务会话逐项下发到实际拥有任务，再引导用户一次性完成登录准备。
3. SIF和卖家精灵任务可按`登录准备`使用浏览器已保存凭据或本机密码管理器；凭据引用只是该电脑上的项目名称/条目名称，不能是密码本身。Amazon必须由用户在每个拥有Amazon动作的任务中手动登录。
4. 每个任务验证自己的页面、身份和站点后生成一份本Run本地证据并独立回执。主任务不能用自己的Cookie、截图或“其他任务已登录”代替。
5. 八份回执全部就绪后才完成`login_gate`；在此之前不得查询、提问、导出或采集联想。

## 固定任务会话矩阵

| session_key | 实际拥有任务 | 服务 | 依赖阶段 | 登录责任 |
|---|---|---|---|---|
| `listing:product-audit:amazon` | Listing商品审计 | Amazon | `product_audit` | 用户手动 |
| `listing:five-dimension-insights:amazon` | Listing五维洞察 | Amazon | `market_insights` | 用户手动 |
| `listing:tag-priority:amazon` | Listing标签优先级网页核验 | Amazon | `tag_priority` | 用户手动 |
| `listing:painpoint-frequency:amazon` | Listing痛点频率 | Amazon | `pain_points` | 用户手动 |
| `listing:painpoint-phrasing:amazon` | Listing痛点口语表达 | Amazon | `painpoint_phrasing` | 用户手动 |
| `keyword:autocomplete:amazon` | 关键词Amazon联想 | Amazon | `keywords` | 用户手动 |
| `keyword:sif-collector:sif` | 关键词SIF竞品反查 | SIF | `keywords` | 已保存凭据或本机密码管理器 |
| `keyword:sellersprite-collector:sellersprite` | 关键词卖家精灵扩词 | 卖家精灵 | `keywords` | 已保存凭据或本机密码管理器 |

一个`task_id + host`只能满足一个逻辑会话。任务合并、侧栏缺失或主任务可见页面都不能缩减矩阵；任务身份不明确时先核对项目、角色、Task ID、host、cwd和派发ID。

## 回执字段与验证

`pipeline_state.py confirm-login-session`逐会话登记以下非敏感字段：

- `session_key/project/role/provider`；
- `task_id/host/dispatch_id`；
- `status`；网页为`authenticated_web`，SIF仅在用户明确批准且同提供商MCP已鉴权时可为`user_approved_same_provider_mcp`；
- `observed_domain/postal_code/assistant`；Amazon必须与当前Run锁定路由完全一致，需要购物助手的角色还必须验证Alexa或Rufus；
- Run证据目录内的`evidence_file`及自动计算的SHA-256、字节数、验证时间；
- SIF MCP例外所需的`user_approval_ref`和`mcp_authenticated=true`。

证据只能证明当前任务、当前host、当前Run的可用会话，不能包含账号密码、验证码、Cookie、令牌或可复用认证材料。任务ID和真实证据路径属于本机Run数据，不进入公开任务包或Git。

全部回执后运行`finalize-login-gate`。如果任一会话过期、登出、跳站或任务重建，运行`invalidate-login-session --reason <原因>`；状态机只阻断该会话直接依赖的阶段，其他已验证且无依赖关系的阶段可继续。重新登录后为同一会话登记新证据，再重新完成总门。

## 站点与异常

- Amazon-US固定`amazon.com/10001/Alexa for Shopping/English`；Amazon-DE固定`amazon.de/80539/Rufus/German`。
- 页面进入其他站点时，标记`marketplace_mismatch`并通知用户介入；不能自行以美国站结果补德国站。
- 德国站Rufus无可靠`New Chat`且刷新后上下文可能保留；各相关Skill继续使用包含目标ASIN的固定德语问题。面板已经可见时不得再次点击开关将其隐藏。
- 用户拒绝或无法完成某个必需登录时，保留`pending/reauth_required`并只报告依赖阶段阻断；不得把技术未执行写成“无结果”。
