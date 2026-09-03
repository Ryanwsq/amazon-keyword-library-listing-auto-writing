# 2026-08-21 output-contract synchronization handoff

- Status: confirmed rules synchronized; P1 pending
- Sharing: sanitized
- Cleaning baseline: V2.1
- Word-frequency component: V2.2
- Skill maturity: all twelve remain draft/planned

## Scope

本次把首轮运行后用户逐项确认的减负规范写回稳定知识、判定边界、端到端流程、项目状态和各单一职责Skill合同。它只改变抓取、过程输出、派生计算和最终装配合同，不把旧案例升级为P1，也不创建新清洗版本。

## Confirmed replacements

- 第一板块由十表改为两Sheet业务工作簿；三来源原始证据和分页只保存在过程目录及manifest。
- 第二板块固定四Sheet且不复制完整源表；Sheet2/3/4共同闭合第一板块人口。
- 分类只输出Sheet2与Sheet4增强表和最小否词库；动态语义列归第三板块。
- 词频删除英语介词，介词同时作为相邻双词断点。
- 竞争只用SIF Top3点击/转化份额并输出固定12列。
- 趋势使用卖家精灵至少24个完整月，展示最近12月月搜索量/环比/同比及最近4季度搜索量/环比/同比，并生成两张百分比折线图。
- 最终交付只有过程文件夹和七Sheet最终工作簿；最终总表覆盖三去向完整人口并固定50列加N个动态语义列。
- 独立质量验证使用两Sheet最小报告、唯一问题文档和21项最终装配门。

## Validation boundary

首轮旧工作簿仍是旧规则问题发现证据。下一步必须在锁定的新仓库revision上，从用户输入开始按当前合同完成一次全程只读Run；运行中不修改知识或Skills，所有错误只进入一个问题文档。完成两个正常案例和一个边界/异常案例前，所有能力继续标记`planned`。

## Publication boundary

本次可同步GitHub功能分支和现有项目飞书流程文档。原始响应、真实业务工作簿、账号、Token、任务ID和绝对路径不得进入Git或飞书。
