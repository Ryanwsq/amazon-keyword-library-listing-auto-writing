# MCP优先、报错后官网备用（2026-09-14）

仅适用于卖家精灵扩词、SIF竞品反查；本文件由两个来源Skill共同引用。新Run固定`source_policies={sif_competitor:mcp-first-error-only-20260914,sellersprite_expansion:mcp-first-error-only-20260914}`。其他来源和趋势`SellerSprite MCP > Sorftime MCP`不变。

## 执行顺序

1. 所属任务核验当前Run/Task/host的MCP真实鉴权与锁定查询，取得`authenticated_mcp`后查询；不前置打开官网，不等待网页登录。
2. 仅真实MCP调用明确报错（包括有原始错误的连接、超时、服务或认证错误），保存原始错误、错误码、查询锁及已完成/未完成人口后，才允许同提供商官网备用。工具尚未发现先做工具发现；仅未配置、未知、猜测不可用不算已报错。零结果、缺字段、截断/不完整响应、缺页及保存失败不是MCP报错；按原缺口/技术异常门处理，不伪装成报错换入口。
3. 官网备用前，由主任务明确提示用户在对应拥有任务浏览器登录该官网；记录通知，再由该任务核验`authenticated_web`，才开始查询/导出。未登录回传`awaiting_login`。不读取或转发密码、Cookie、令牌、验证码；不通过换入口绕过权限、账号冲突、验证码或错站，需用户介入。
4. 只处理原锁未完成ASIN/种子，保持站点、最近30天、顺序、过滤、字段、SIF每ASIN300条及完整性门。已完成不重采。不能证明跨入口无遗漏/重复时，受影响查询另批完整官网查询，旧partial保留诊断但不混装。每种子只接纳一个成功完整结果，不做交叉重复验证。

## 当前证明格式

查询锁沿用`amazon-keyword-source-query/v1`，增加`source_policy=mcp-first-error-only-20260914`，首选`entry_type=mcp`。dispatch 的`admission.source_access`指向本机JSON：

- 共同字段：`schema=amazon-keyword-source-access/v2,run_id,task_id,host,source_provider(SIF或SellerSprite),entry_type,query_lock_sha256,authentication_evidence`。
- 所有指针为`{path,sha256}`；身份必须与实际dispatch目标一致，不能复制另一个任务/项目的鉴权布尔值。
- 鉴权JSON：`schema=amazon-keyword-mcp-authentication/v1`（官网改`amazon-keyword-web-authentication/v1`）、`run_id,task_id,host,provider,entry_type,authenticated=true`，可附`checked_at`，无其他字段。
- 官网proof额外且必须包含`reason=mcp_error,primary_query_lock,mcp_error_evidence,completed_queries,login_notice`。原MCP锁保留，新web锁除`entry_type`及按原顺序剩余的`queries`外逐项相同。
- 报错JSON：`schema=amazon-keyword-mcp-error/v1,run_id,task_id,host,provider,entry_type=mcp,is_error=true,error_code,query_lock_sha256(原MCP锁),evidence`；`evidence`为非空原始报错指针数组，可附`checked_at`。报错文字须来自实际工具响应，不以自行解释数据缺口代替。
- 登录通知JSON：`schema=amazon-keyword-web-login-notice/v1,run_id,task_id,host,provider,login_requested=true`，可附`checked_at`。通知不是登录完成；另需网站鉴权证明。

运行`python3 -B scripts/source_execution.py source-access --stage sif|sellersprite --input <proof.json> --query-lock <query.json>`进行机械绑定检查；不代替真实工具鉴权、错误判断或完整性验收。官网重派发前关闭旧执行占用，新合同用`locks.sif_query_lock_sha256`或`locks.sellersprite_query_lock_sha256`锁定新web查询，保留旧合同/envelope。两个项目各自拥有Run与证明；跨项目只通过正式交接绑定。

## 历史与业务边界

旧`mcp-first-20260911`允许的`mcp_incomplete/mcp_unavailable`仅用于已冻结历史合同验证，不适用于新Run；更早web-first同样不迁移。新build/reserve不得缺失或降回旧policy。SellerSprite MCP按原连续分页、四字段、事件账本与损失风险要求取得完整结果；只有官网备用才要求官方XLSX导出及export-population检查。SIF仍固定七列、原ASIN范围与300条接口范围。机械回归不表示实际来源可用或P1通过。
