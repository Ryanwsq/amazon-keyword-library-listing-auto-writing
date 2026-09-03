# Case 01 — competition analysis normal run

- Case type: `normal`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-competition-normal-01`
- Execution environment: controlled local Amazon US run
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

Sheet2中资格为`纳入`的F1–F4人口、锁定的SIF最近30天Top3点击份额和Top3转化份额。

## Capabilities actually exercised

- `keyword.library.competition.analyze`
- `keyword.competition.outputs.write-and-verify`

`keyword.competition.sif-top3.query`未调用，因为16个目标词的两项精确证据均已存在且无冲突。

## Execution and output

输出16行、12列竞争分析：F1/F2/F3/F4人口为`1/2/3/10`。16组精确Top3数据全部复用，新增补查、未解决缺口和来源冲突均为零。

## Quality checks

- F5、Sheet3、Sheet4和不纳入人口混入均为零。
- 四档阈值边界、点击/转化差异边界和4×4等级矩阵测试通过。
- 80个公式无错误，工作簿重载、渲染、目视、外链、宏和隐私检查通过。

## Conclusion

本模块正常案例被用户接纳。Skill仍为`draft`，尚需第二个正常案例和一个边界/异常案例。
