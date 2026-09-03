# Case 01 — SellerSprite official export normal run

- Case type: `normal`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-sellersprite-normal-01`
- Execution environment: SellerSprite已登录官网、Amazon US、完整官方导出
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

用户确认类目不存在多个稳定产品类型细分，因此仅使用唯一一级核心种子；查询月份、站点、过滤和四个业务字段均锁定。账号、凭据、原始导出和本机路径不进入本证据。

## Capabilities actually exercised

- `keyword.source.sellersprite.web-query`
- `keyword.source.sellersprite.paginate-and-verify`

## Execution and output

通过官网顶部导出入口取得两次一致的完整官方导出，没有使用MCP或页面抄取。共保留752条原始事件、376个机械唯一键和376条重复血缘；第二次Pass没有新增、删除或字段冲突。

## Quality checks

- 单种子、月份、市场和字段与输入锁一致。
- 四字段业务工作簿为376行，重载验证通过。
- 10个翻译缺失和3个含官方导出隐藏字符的机械键按原样保留，没有补值或语义改写；未观察到关键词损失。

## Conclusion

本模块正常案例被用户接纳。所列缺口是可见残余风险，不改变本模块完整导出和机械交接的通过结论；Skill仍需另外两个案例完成P1。
