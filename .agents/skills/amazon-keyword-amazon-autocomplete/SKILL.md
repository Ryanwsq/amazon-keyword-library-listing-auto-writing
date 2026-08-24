---
name: amazon-keyword-amazon-autocomplete
description: Capture the required Amazon US search-box autocomplete matrix in the Codex in-app browser or an ordinary Chrome fallback. Use for第一板块Amazon联想、固定未登录环境和可见建议证据；do not use for search results, web search, SIF, SellerSprite, source merging or semantic filtering.
---

# Amazon Keyword Amazon Autocomplete

## 目标

在固定可复核环境中，只围绕主一级品类核心大词采集必选 Amazon 搜索框可见联想矩阵。

## 输入

锁定的 `Run_ID`、唯一一级品类核心大词、站点 US、真实品类功能/配置探针、规格敏感性判断、本机忽略输出目录，以及首选 Codex 内置浏览器或获准普通 Chrome 备用入口。本模块不使用可能等于细分核心词的主执行锚点。

## 输出

触发输入清单、每个输入的成功/无建议/失败状态、全部可见建议与顺序、实际浏览器环境、登录状态、Department、邮编、时间、执行次数和证据指针。

## 可调用能力

- `keyword.source.autocomplete.capture`

## 执行步骤

1. 完整读取 `knowledge/index.md`、`../../../docs/keyword-judgment-boundaries.md` 和 `references/source-contract.md`，核对唯一一级品类核心大词、探针、固定环境和停止门。
2. 首选 Codex 内置浏览器；当前设备无法稳定识别或操作时，记录首选入口失败事实并切换普通 Chrome。无论入口都必须打开 Amazon US，确认未登录、Department=`All`、配送邮编=`10001`，并记录真实浏览器入口；不写无痕模式。
3. 依次执行基础输入、后置 A–Z、前置 A–Z、`for/with/without`、真实品类功能/配置的前后组合；规格敏感产品再执行0–9，否则记录不适用。
4. 每个输入等待下拉建议稳定，只读取当次搜索框上方关键词联想区的建议和顺序；不按 Enter、不进入结果页、不递归扩展新词、不使用`how/what/why`。普通关键词建议行、关键词建议卡片和关键词建议组内选项都必须完整可见；关键词建议被该区域内轮播或横向控件遮挡时，在输入不变的前提下用该区域控件使其完整显示，并保存操作前后证据。仍无法完整显示的建议只记异常，不进入来源事件；状态提示数量不能替代可见文本。底部商品卡、价格卡和商品轮播全部排除，即使完整可见也不形成来源事件，不操作商品轮播来采集其内容。
5. 功能/配置探针记录目标 SKU 为具备、不具备或待核实；联想结果不能转成产品宣称。
6. 每个输入保存状态、建议、环境、时间和可见证据指针；同一建议由多个输入触发时保留全部来源事件。
7. 核对适用矩阵输入均有状态，形成只含联想来源的回传清单；不合并到总词池。

## 质量标准

- 环境固定且记录完整；内置浏览器与普通Chrome备用入口均可追溯，没有搜索结果页、网页搜索或API替代。
- 每个适用输入都有成功、无建议或失败状态。
- 只保存上方关键词联想区的可见关键词建议，重复触发来源不丢失；底部商品卡、价格卡和商品轮播零混入。
- 建议顺序只作为原始字段，不被解释为流量等级。
- 不执行来源合并、语义判断或产品宣称。

## 异常处理

内置浏览器不能稳定识别或操作时先记录并切换普通Chrome；两个入口都不可用，或任一入口无法确认页面、登录状态、部门或邮编时，保存未执行证据并回传`not_executed/incomplete`。不得使用搜索结果页、网页搜索或API模拟联想，也不能把被遮挡或仅由状态提示推断的内容写成已采集建议。
