# Case 01 — classification normal run

- Case type: `normal`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-classification-normal-01`
- Execution environment: controlled local Amazon US run
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

锁定清洗输出的261行Sheet2、740行Sheet3和125行Sheet4，以及ABA、搜索量、资格和当前分类合同。

## Capabilities actually exercised

- `keyword.library.classify`
- `keyword.classification.sheet2.apply`
- `keyword.classification.sheet4.apply`
- `keyword.classification.negative-library.build`
- `keyword.classification.outputs.write-and-verify`

## Execution and output

在锁定revision上重新对齐执行后，Sheet2和Sheet4共分类386行；合并流量层人口为F1/F2/F3/F4/F5=`7/4/15/26/334`。Sheet2生成15个动态语义列，否词库收录199行且不含否定方式。

## Quality checks

- 上游字段、主键、人口、F1–F5重算、F5唯一主标签和LT检查通过。
- Sheet4仅追加四个固定分类列；没有重判二类词身份。
- 公式错误为零，10/10分段渲染、目视和隐私扫描通过。
- 已知`CLASS-F5-001`为用户决定暂不处理的非阻断跨Run优先级候选，没有伪装成已解决。

## Conclusion

本模块正常案例被用户接纳；非阻断开放项不改变本次行级分类闭环。Skill仍需另外两个案例完成P1。
