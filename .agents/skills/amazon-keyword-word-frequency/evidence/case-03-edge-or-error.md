# Case 03 — standalone plus-token correction

- Case type: `edge-or-error`
- Registry status: `accepted`
- Sanitized case reference: `gaming-chair-word-frequency-plus-edge-01`
- Execution environment: controlled local calculation on locked Sheet2 population
- Locked Git revision: `4a903057765e136c85c5dc4704178c076f3ce467`
- User acceptance: `2026-08-27`

## Input

Sheet2中261条`通用词库资格=纳入`关键词、`EN_PREP_CORE_V1`固定48-token介词表和V2.2词频合同。

## Capability actually exercised

- `keyword.library.word-frequency`

## Execution and output

首个候选暴露独立加号进入token化的问题。按用户确认执行最小修正：只去除独立`+`，不改变词频规则或其他字符，再从同一锁定人口重算。最终得到918个原始token、排除48个介词、870个有效单词、165个唯一单词、561个相邻有序双词和239个唯一双词。

## Quality checks

- 20/20模块门通过，介词泄漏与加号泄漏均为零。
- 单词和双词计数闭合，双词不跨介词断点。
- 仅处理资格纳入的Sheet2人口；未读取Sheet3或Sheet4。
- 工作簿重载、渲染、目视、隐私和公式错误检查通过。

## Conclusion

接纳为词频Skill的边界案例：验证了异常符号的最小修正与重算闭环，不占用正常案例槽位。
