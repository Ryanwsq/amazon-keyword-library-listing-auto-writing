# Category trend output contract

## Input lock

锁定分类工作簿名称/哈希、Sheet2总人口与通用词库资格人口、`通用词库资格=纳入`的F1–F3唯一Keyword_ID人口、站点、最新完整月、至少24完整月查询范围、来源优先级、选定提供商、趋势批次和规则版本。`不纳入/待复核`、F4/F5、Sheet3、Sheet4及SKU事实不输入。

## Formal source

来源优先级固定为`SellerSprite -> Sorftime`。默认使用卖家精灵精确关键词月搜索量；卖家精灵不可用时可使用Sorftime精确关键词月搜索量。选定正式来源后，全部关键词和月份只使用该提供商；主来源批次中途失败时，备用来源必须从头重跑全部人口，不能拼接已取得主来源月份。主来源恢复只在新Run重新成为首选。

每条月份必须非空且可解析。当前未结束月排除；缺值留空，不填0、不插值、不前值延续、不回退SIF、词根或近义词。记录提供商、入口、精确查询词、查询时间、实际首尾月份和有效/缺失月份。

## One-sheet structure

### Keyword index

固定四列：`Keyword_ID、英文关键词、中文翻译、流量层`。

### Monthly matrix

固定前两列`月份、指标`，后续每个F1–F3关键词一个Keyword_ID动态列。最近12个完整月，每月固定三行`月搜索量、月环比、月同比`，共36行。

### Quarterly matrix

固定前两列`季度、指标`，后续每个F1–F3关键词一个Keyword_ID动态列。最近4个完整自然季度，每季固定三行`季度搜索量、季度环比、季度同比`，共12行。

只作同比/环比基准或实际搜索量绘图、但不在最近12月表格范围内的历史月保留在本地manifest/图表辅助区，不另铺最终展示矩阵。

## Calculations

- 月环比=`(本月-上月)/上月`
- 月同比=`(本月-上年同月)/上年同月`
- 季度搜索量=该自然季度三个完整月之和
- 季环比=`(本季度-上季度)/上季度`
- 季同比=`(本季度-上年同季度)/上年同季度`

当前值/基准缺失或基准为0时留空。季度任一月缺失时，该词该季度搜索量和两项比率全部留空。

## Charts

1. 月度图横轴为锁定数据中全部已结束完整年月，纵轴为实际月搜索量；每个关键词一条线。
2. 季度图横轴为锁定观察范围内全部完整自然季度，纵轴为三个完整月搜索量之和；每个关键词一条线。观察范围缺少任一日历月的季度不进入季度图；单个关键词缺月时其季度点留空。
3. 月环比、月同比、季环比和季同比只保留在表格矩阵，不得成为图表序列或纵轴。
4. 两图各有`关键词数`条理论序列，图例使用英文关键词；不得因序列多删除关键词。

## Stable OOXML audit

Artifact Tool完成生成、重载和公式检查后，必须运行包级审计器：

```bash
python3 .agents/skills/amazon-keyword-trend-analysis/scripts/audit_trend_ooxml.py \
  <trend-workbook.xlsx> \
  --manifest <trend-manifest.json> \
  --json-out <verification-directory>/trend-ooxml-audit.json
```

审计器必须枚举`workbook -> 全部worksheet -> 各自全部drawing -> 各自全部chart`关系，解析常见前缀/默认OOXML命名空间和包内相对/绝对关系目标；不得只检查首个Sheet、首个drawing或固定`xl/charts`路径。月度图与季度图必须分别识别，所有series的分类与数值引用都须落入manifest锁定的实际搜索量辅助区；series名称、源公式和数值单元格格式不得显示MoM、QoQ、YoY、环比、同比或百分比证据。

manifest至少声明：

- `population.actual`和`formula_count`；
- `charts.count=2`；
- `charts.monthly`、`charts.quarterly`各自的`metric`、`source_range`、`series`和`percentage_series=0`。

退出码固定为：`0=pass`、`1=business_failure`、`2=auditor_failure`。关系断裂、目标部件缺失、输入不可解析，或manifest/OOXML包声明存在图表或公式而审计得到零，均属于`auditor_failure`；此时不能据此否定工作簿，也不能静默放行，必须停止该验证门并修复或更换审计路径后重跑。`business_failure`只用于审计器已完整解析后发现的人口、公式、月/季图、实际量引用或百分比序列合同不闭合。

## Manifest

记录输入哈希、人口/唯一主键、站点、来源优先级、选定提供商/入口、查询时间、查询月份、逐词有效/缺失月份、环同比空值/零分母、不完整季度、两矩阵尺寸、图表年月/季度范围和序列、`formula_count`、两图实际搜索量`source_range`、公式/渲染、输出哈希、原始响应相对目录、状态和唯一问题文档。

## Status

- `completed`：全部词24个月完整且矩阵/图表闭合。
- `completed_with_gaps`：每词有数据但部分月份缺失，合同允许的空值准确。
- `incomplete`：至少一词零有效数据，或所需同比/环比基准整体不足。
- `not_executed`：接口不可用或全局无完整月。
- `blocked`：主键、人口、矩阵、公式或图表无法闭合。

## Quality gate

人口等于Sheet2中`通用词库资格=纳入`的F1–F3，`不纳入/待复核`零混入；每词由同一选定提供商精确查询且至少覆盖24完整月；月度36行、季度12行；每词在两矩阵各一列；两图理论序列均为关键词数、引用实际搜索量正确范围且百分比序列为零；公式错误为零；Sheet和两图完成渲染目视复核。

## Runtime calculation

单一提供商的至少24完整月原值使用仓库级`trend`确定性核心计算月/季矩阵和两张实际搜索量图表数据。脚本不执行来源查询、提供商切换、补0、插值或跨源补月；缺失和零分母继续留空。执行器版本、提供商、适用人口、月份人口和结果哈希写入manifest，仍必须执行工作簿公式、渲染和OOXML包级审计。
