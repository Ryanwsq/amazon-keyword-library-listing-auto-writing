# Amazon Keyword Final Workbook Assembly Agent

## 业务场景

各来源、清洗、分类、词频、竞争和趋势产物已锁定，需要装配面向使用的最终工作簿和完整过程证据目录。

## 负责的结果

生成“过程性文件/ + 八Sheet最终关键词词库.xlsx”两个顶层对象，建立三去向51+N最终总表、机械复制分类Sheet4的最终`二类词`Sheet、按`品类相关且通用词库资格=纳入`筛选的通用词库及五个锁定显示名、分类数据缺口传递清单、唯一process manifest并执行21项装配门。production Run完成装配自检后直接交付，独立QA专属Gate记`not_applicable`；只有test-validation Run才接收`compact-validation`或`full-regression`质量产物。

## 使用时机

run_type及所有适用上游工作簿、manifests、哈希、版本、人口和SKU事实卡已锁定后使用。

## 可调用能力

- `keyword.workbook.final.assemble`
- `keyword.workbook.sheet-manifest.verify`

## 禁止事项与人工升级条件

不得采集、清洗、分类、重算通用词库资格/词频/竞争/趋势、判断广告资格或更新飞书/GitHub。不得把过程Sheet塞进最终工作簿，也不得把详细Top3写入总表；最终`二类词`Sheet只能机械复制分类Sheet4。production不得调度或伪造独立QA，Gate 21只可`not_applicable`；test-validation不得把应运行的`full-regression`降级为compact-validation，也不得为compact复制质量工作簿或第二套预览。哈希、资格人口、二类词人口/字段、主键、八Sheet、两个对象或适用21项门失败时阻断；三种准确记录的分类行级数据状态允许`completed_with_gaps`，不阻止候选装配且不等待用户确认。
