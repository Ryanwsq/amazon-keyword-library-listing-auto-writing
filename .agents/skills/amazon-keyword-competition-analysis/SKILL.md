---
name: amazon-keyword-competition-analysis
description: Build the standalone competition-analysis sheet for product-library-eligible classified Amazon Sheet2 F1-F4 keywords using only exact SIF Top3 click and conversion shares. Use for关键词头部锁定竞争等级、Top3结构分化和竞争输出质检；do not use for trend charts, source mining, classification, negative targeting or ad eligibility.
---

# Amazon Keyword Competition Analysis

## 目标

为Sheet2中`通用词库资格=纳入`的F1–F4完整词建立固定十二列竞争Sheet，只使用同周期SIF Top3点击/转化份额计算头部集中和锁定等级。

## 输入

锁定的分类Sheet2总人口、`通用词库资格=纳入`的F1–F4人口、Keyword_ID、第一板块Top3、站点、周期、竞争版本和获准SIF补查范围。

## 输出

一个十二列竞争过程工作簿、manifest和紧凑状态；不写广告行动。

## 可调用能力

- `keyword.library.competition.analyze`
- `keyword.competition.sif-top3.query`
- `keyword.competition.outputs.write-and-verify`
- `keyword.competition.matrix.calculate`

## 执行步骤

1. 读取知识、判断边界和`references/output-contract.md`，锁定Sheet2资格人口、`纳入`且为F1–F4的人口、主键、周期和版本；不读取SKU事实，不重算通用词库资格。
2. 按完整关键词复用第一板块SIF Top3。同词多记录一致时合并来源，不平均。
3. 任一Top3缺失或冲突时，才按完整词精确补拉SIF；同一行两项必须来自同一查询周期。补拉后仍缺失/冲突、周期或单位不明时不出等级。
4. 把资格纳入F1–F4人口、同周期完整词精确Top3两项、明确单位和完整性状态输入`scripts/keyword_deterministic_core.py competition`。由确定性核心将可确认的0–1小数转换为百分比；单位不能确认时停止。
5. 由同一确定性核心分别按30/50/70%阈值计算点击和转化集中等级，计算`点击转化差=转化-点击`及结构判断。
6. 由同一确定性核心按固定4×4矩阵输出综合竞争等级。综合字段只写低/中/高/极高，结构分化只写结构判断。脚本只计算已锁定数值，不补拉、不近似匹配、不决定人口。
7. 写入固定十二列，验证人口、主键、来源周期、阈值、矩阵、空值门、公式和渲染。

## 质量标准

- 人口恰好等于Sheet2中`通用词库资格=纳入`的F1–F4；`不纳入/待复核`、F5、Sheet3和Sheet4零混入。
- 正式输入只有Top3点击和转化份额，且为完整词精确、同周期值。
- 阈值、差值和矩阵可复算；缺值/冲突/周期或单位不明行无等级。
- 确定性计算版本、适用人口和结果JSON哈希进入manifest；它不替代SIF完整性、周期、单位、字段、工作簿和渲染检查。
- 无CPC、SPR、商品数、市场CVR、Top3 ASIN、比较池、样本门、置信度或广告建议。
- Skill保持draft/planned，未通过真实三案例不称verified。

## 异常处理

SIF补查不可用时保留第一板块值和缺口，不回退其他来源。通用词库资格、主键/人口、周期或单位无法锁定时阻断相应等级并回传主任务。
