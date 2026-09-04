# 加载顺序

1. 核对明确下发的角色 `selling-point-intake`、版本 `listing-release-candidate-20260904-rc3` 和 [package-manifest.json](package-manifest.json) 哈希。
2. 完整读取 [Agent.md](Agent.md) 和 [任务包交接边界](contracts/dispatch-and-loading.md)。
3. 完整读取所属 [receive-listing-selling-point-files](.agents/skills/receive-listing-selling-point-files/SKILL.md)。
4. 按Skill要求完整读取必需reference与知识正文；[知识索引](knowledge-base/index.md)与[规则映射](rules/index.md)只作导航，不代替正文。
5. 再核对本次锁定输入、来源、Run/SKU及启动授权；没有业务输入时停止在只读READY。

主任务包保留全项目规则用于监督和分发；非所属Skill不在当前任务执行业务。副任务包只包含本角色所需完整材料与明确依赖。证据与结构测试范围见[evidence/index.md](evidence/index.md)。
