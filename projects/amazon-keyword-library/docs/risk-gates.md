# Risk gates

所有工作台主任务、项目主任务和副任务都必须在执行前判断风险。

| Risk | Examples | Default action |
|---|---|---|
| low | 只读检查、脱敏草稿、本地验证、可回滚且不含敏感信息 | 在已分配范围内执行并回传 |
| medium | 修改共享记忆或公共 Skill、跨项目变更、准备外部写入、公司内容的脱敏迁移 | 暂停写入，由相应主任务审查范围与回滚方式 |
| high | 凭据、客户/员工隐私、权限管理、公开、删除、不可逆外部写入、公司资料离开受控环境 | 必须获得用户明确确认和所需公司批准 |
| uncertain | 无法判断所有权、敏感度、影响范围、目标仓库或回滚方式 | 按中高风险暂停，不猜测 |

## Escalation path

- 项目副任务 → 项目主任务。
- 项目主任务 → 工作台主任务，适用于跨项目、共享层或仓库级影响。
- 工作台主任务 → 用户或公司授权方，适用于高风险、政策和不可逆动作。

## Risk package

```text
Source project and logical role:
Task:
Risk level:
Resources or data involved:
Proposed action:
Impact and sharing scope:
Sensitive information:
Rollback method:
Why normal workflow is insufficient:
Recommended decision:
Required approver:
```

私有仓库不降低数据本身的分类，也不等于允许从公司电脑同步到个人设备。
