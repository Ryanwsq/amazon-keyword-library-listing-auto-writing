# Case 01 — trend analysis normal run

- Case type: `normal`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-trend-normal-01`
- Execution environment: controlled local Amazon US run; SellerSprite single-provider trend source
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

Sheet2中资格为`纳入`的F1–F3完整词人口、最新完整月和至少24个月合同。

## Capabilities actually exercised

- `keyword.library.trend.analyze`
- `keyword.trend.sellersprite.query`
- `keyword.trend.outputs.write-and-verify`

## Execution and output

对6个唯一关键词完成25个已结束月份的精确词搜索量收集，F1/F2/F3人口为`1/2/3`。输出月度矩阵、季度矩阵、两张实际搜索量折线图及环同比表格；同一Run没有混入Sorftime。

## Quality checks

- 6/6关键词、25/25月份闭合，不补0、不插值。
- 两张图各含6个实际搜索量序列，环同比未作为折线图数据。
- 工作簿重载、公式错误、OOXML关系、渲染和目视检查通过。

## Conclusion

本模块正常案例被用户接纳。Skill仍需另外两个案例完成P1。
