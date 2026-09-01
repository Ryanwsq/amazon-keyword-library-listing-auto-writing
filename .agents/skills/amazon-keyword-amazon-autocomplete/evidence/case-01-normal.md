# Case 01 — Amazon autocomplete normal run

- Case type: `normal`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-autocomplete-normal-01`
- Execution environment: Amazon US未登录、Department=`All`、邮编`10001`、Codex内置浏览器
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

用户确认类目不存在多个稳定产品类型细分，因此唯一联想锚点使用一级品类核心词。原始截图、账号状态、本机路径和逐词长表不进入本证据。

## Capability actually exercised

- `keyword.source.autocomplete.capture`

## Execution and output

完整执行69个固定输入，因一次受控词组展开产生70次执行；68个输入返回可见建议，1个输入为`no_suggestions`，没有失败输入。共保存619条可见建议事件并形成535个机械唯一键。

## Quality checks

- 69/69输入均达到终态，顺序和证据指针完整。
- 未按Enter、未进入结果页，未使用网页搜索或API替代。
- 底部商品卡、价格卡和商品轮播未进入来源事件。
- 四Sheet来源工作簿重载、渲染、目视和公式错误扫描通过，隐藏损失与异常均为零。

## Conclusion

本模块正常案例被用户接纳。Skill仍为`draft`；尚需第二个正常案例和一个边界/异常案例才能评估P1。
