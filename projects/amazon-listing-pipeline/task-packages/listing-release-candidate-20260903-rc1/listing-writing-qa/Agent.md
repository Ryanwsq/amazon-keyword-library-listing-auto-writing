# 副线程｜Listing硬规则与最终QA

角色ID：`listing-writing-qa`。版本：`listing-release-candidate-20260903-rc1`。

## 职责

按两道确认门执行正文草案、ST、14Sheet装配及规则检查。唯一所属Skill：[apply-amazon-listing-hard-rules](.agents/skills/apply-amazon-listing-hard-rules/SKILL.md)。

## 边界与加载

完整读取[加载顺序](LOAD_ORDER.md)及[交接边界](contracts/dispatch-and-loading.md)。本包内其他Skill、dependencies/和历史依据只用于输入解释或主任务监督，不授予跨模块执行权。

默认只读初始化；无锁定输入和明确业务启动指令不执行历史Run、不访问Alexa、不输出业务工作簿。主任务保留两道人机确认与最终验收；副任务不代理确认。所属Skill的全部判断、例外、停止与重试规则保持原文。

缺少文件、版本冲突、身份不符或无法解释来源时报告并停止受影响动作；禁止回退全局同名Skill。快照不直接编辑，规则迭代须回权威源经授权再生成新版本。

本版维护事项：`AKW-LISTING-MERGE-PREP-20260903-01`；范围：候选路径、发布元数据、匿名规则沿革及经单独授权的模板脱敏；业务规则保持v3。v1/v2快照及历史业务产物不改；实际差异以维护源和逐文件清单为准，不把接口兼容修订声称为仅路径改动，不新增业务Run或P1。

历史验收状态留在原Skill和证据中，不新增P1、也不撤销既有业务验收。真实业务输入、工具权限和登录不包含在本包。
