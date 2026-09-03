# Amazon Listing Pipeline — 项目入口

本目录是独立 Listing 项目，不与相邻关键词项目合并业务规则。先读取 `task-packages/registry.json`，按明确下发的角色、候选版本和 manifest 哈希加载对应角色包的 `AGENTS.md`、`Agent.md`、`LOAD_ORDER.md` 及完整 Skill 依赖。不得从 cwd、全局同名 Skill 或历史部署猜测角色。

保留主任务、七个业务副任务、两个接收整理任务。每个部署包只有一个所属执行入口；`dependencies/skills/` 是完整参考依赖，不授予越权执行。主任务保留完整规则、跨项目来源锁、两道人机确认和最终验收。

本候选不含真实任务绑定、输入、运行结果、聊天记录或登录。具体任务绑定和业务输入由安装环境单独明确提供；没有当前 Run、产品身份、来源哈希及启动授权，只能只读初始化。不同 Run 隔离，忙任务排队，不重复派发。文件存在和结构检查通过均不是业务 READY。

`.agents/skills/`、`knowledge-base/` 是本候选的维护源；`task-packages/<version>/<role>/` 是生成的只读快照。只经明确授权修改维护源后生成新版本，不直接改快照、不静默升级历史 Run。本候选不携带原项目的历史快照或业务产物。

验证入口：`python3 -B scripts/task_packages.py validate`、`python3 -B scripts/validate_skill_packages.py`。它们不启动业务，不证明外部工具、登录、Amazon 审核、真实案例或 P1。只执行当前明确请求的范围。

来源、候选适配与发布状态见 `PUBLICATION.md` 和 `release/candidate-manifest.json`。公共包不是运行授权；不得把模板的示例或匿名规则说明当新 SKU 事实。
