# receive-listing-selling-point-files

## 业务场景

保留接收整理入口，默认只核验与登记；不另造优势或重排卖点。完整SOP见[SKILL.md](SKILL.md)。

## 负责的结果

只读接收回执、字段证据映射、冲突和缺口。不替代其他模块的结果或人工确认。

## 使用时机

本模块收到明确分发的角色、Run/SKU、规则版本、输入路径与SHA-256和启动授权后。输入：锁定Run、SKU、路径和哈希的卖点配置文件。只读初始化时不启动业务。

## 可调用能力

- `listing.selling-point-intake.execute`：登记于[capabilities.yaml](capabilities.yaml)；状态planned不表示已验证可用，实际工具按原SOP和当次授权确认。

## 禁止事项与人工升级条件

不扩大角色权限、不改历史Run、不以参考Skill代替执行模块、不以技术失败或未知填0、不代用户确认。输入冲突、来源/哈希变化、规则缺失或当前模块规定的访问阻断时，按原SOP停止受影响动作并回主任务。各模块自己的问题、次数、停止与重试合同原样保留，不套统一重试规则。

资料读取路由和完整判断边界在[知识索引](knowledge/index.md)及原SOP中。包拆分不改变既有项目内验收；新结构revision的证据登记见[evidence/index.md](evidence/index.md)。
