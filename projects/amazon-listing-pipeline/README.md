# Amazon Listing Pipeline

仓内目标：`projects/amazon-listing-pipeline`。本项目负责 Listing 信息决策、双人工确认、写作与十四 Sheet 装配；关键词生产由独立的 `projects/amazon-keyword-library` 项目负责，经正式回执和主任务 READY 后才进入本项目 SKU 终筛。

从 `AGENTS.md` 和 `task-packages/registry.json` 进入明确角色。业务流程、字段、来源、判断、例外及停止/恢复条件保留在完整 Skill 与其必读 references/知识中；本说明不替代它们。

目录保留完整维护源、十角色部署包、依赖合同、必要资产、构建器与只读校验器。真实任务 ID、设备路径、登录、原始输入输出、采集问答及历史运行状态不属于此发布候选。

原始讨论记录未发布；`project-control/listing-writing-iteration-log.md` 为不含原话/身份的规则沿革索引，完整现行正文在知识库。匿名规则说明保留适用边界，不是训练数据、已验收案例或任何新 SKU 的事实来源。未确认的时间戳复用待办不作为生效规则导入。

新环境使用前仍须完成角色装载、依赖/登录检查、当前输入锁及两道人机确认。候选结构或夹具测试不提升任何 P1 状态，也不授权自动采集、上传 Amazon 或修改 Git 远端。
