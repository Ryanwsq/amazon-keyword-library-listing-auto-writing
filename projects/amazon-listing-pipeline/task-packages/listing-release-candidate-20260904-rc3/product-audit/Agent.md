# 副线程｜Alexa商品信息审计

角色ID：`product-audit`。版本：`listing-release-candidate-20260904-rc3`。

## 职责

02/03接收；获明确采集授权后才按十字段合同执行审计。唯一所属Skill：[audit-alexa-shopping-product-info](.agents/skills/audit-alexa-shopping-product-info/SKILL.md)。

## 边界与加载

完整读取[加载顺序](LOAD_ORDER.md)及[交接边界](contracts/dispatch-and-loading.md)。本包内其他Skill、dependencies/和历史依据只用于输入解释或主任务监督，不授予跨模块执行权。

默认只读初始化；无锁定输入和明确业务启动指令不执行历史Run、不访问Alexa、不输出业务工作簿。主任务保留两道人机确认与最终验收；副任务不代理确认。所属Skill的全部判断、例外、停止与重试规则保持原文。

缺少文件、版本冲突、身份不符或无法解释来源时报告并停止受影响动作；禁止回退全局同名Skill。快照不直接编辑，规则迭代须回权威源经授权再生成新版本。

本版维护事项：`AKW-TASK-SESSION-LOGIN-20260904-01`；范围：在rc2德国站路由与来源修复基础上，增加无秘密登录准备Sheet、固定八Task/host会话矩阵、逐会话回执/失效和分支阻断；Amazon由用户逐任务登录，SIF/卖家精灵使用本机已保存凭据；本批不执行新业务Run或P1。v1/v2快照及历史业务产物不改；实际差异以维护源和逐文件清单为准，不把接口兼容修订声称为仅路径改动，不新增业务Run或P1。

历史验收状态留在原Skill和证据中，不新增P1、也不撤销既有业务验收。真实业务输入、工具权限和登录不包含在本包。
