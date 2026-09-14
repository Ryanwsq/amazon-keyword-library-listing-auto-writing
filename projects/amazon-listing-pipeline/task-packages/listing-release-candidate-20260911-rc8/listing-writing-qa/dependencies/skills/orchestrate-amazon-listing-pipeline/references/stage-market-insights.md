# 阶段：竞品五维洞察与标签优先级

## 子阶段 A｜五维洞察

调用 `$extract-amazon-product-insights`。

### ASIN 来源

优先读取 `市场竞品ASIN池` 中启用且采样用途包含 `五维洞察` 的 ASIN；没有专用 Sheet 时回退到五类对标竞品去重集合并标记样本风险。

### 执行边界

- 每个 ASIN 按依赖 Skill 的固定五题、双问隔离和 A∪B 规则执行。
- 不从 Listing、评论页、网页或模型常识补全。
- 保存固定两 Sheet 输出为 `01_竞品Alexa五维洞察并集.xlsx`。
- 技术停止保留已完成状态，不把未执行当未出现。

## 子阶段 B｜标签优先级

阶段 A 完成后调用 `$prioritize-amazon-insight-tags`。

### 输入

1. `00_锁定输入.xlsx`
2. `01_竞品Alexa五维洞察并集.xlsx`

### 输出

保存固定五 Sheet 工作簿为 `05_Amazon标签优先级决策.xlsx`。

### 给决策层的数据

- P1/P2/P3/不采用的人群、场景、用途、频率标签；
- Coverage、Market Expression、Direct Fit、Differentiation、Proofability；
- 支撑产品参数和主要竞品事实；
- 有效竞品数、介绍度有效样本数与样本状态。

## 禁止

- 不把五类对标竞品矩阵直接当正式市场池。
- 不把 N<正式门槛的 Coverage 当正式市场共识。
- 不把标签优先级直接描述为核心卖点；它回答谁、在哪里、做什么和是否值得表达。
- 不绕过依赖 Skill 的公式驱动分类和固定五 Sheet。
