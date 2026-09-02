---
name: amazon-keyword-word-frequency
description: Count and rank non-preposition single words and adjacent ordered two-word phrases from product-library-eligible Amazon Sheet2 keywords. Use for第二板块词频统计、Listing写作前词面排序或介词断点双词；do not use for source collection, cleaning decisions, traffic weighting, classification, competition, trend, SKU matching or Listing writing.
---

# Amazon Keyword Word Frequency

## 目标

只用第二板块Sheet2中`通用词库资格=纳入`的英文关键词，删除固定英语介词并以介词为双词断点，生成可机械复算的单词和相邻双词频次。

## 输入

锁定且已通过三去向与通用词库资格闭环的第二板块工作簿、Sheet2中`通用词库资格=纳入`的唯一Keyword_ID/英文关键词人口、输入哈希、词频规则版本、固定英语介词表版本`EN_PREP_CORE_V1`及其内容哈希和输出目录。`EN_PREP_CORE_V1`的唯一完整清单见`references/workbook-contract.md`；运行时不得增删、按上下文改判或用外部词典替换。

## 输出

只含一张`词频统计`的过程工作簿、manifest和紧凑状态。Sheet内两张并列三列表：`排名、单词、出现次数`与`排名、相邻双词、出现次数`。

## 可调用能力

- `keyword.library.word-frequency`

## 执行步骤

1. 读取知识、判断边界和`references/workbook-contract.md`；锁定Sheet2总人口、`通用词库资格=纳入`人口、关键词列、哈希、规则版本、`EN_PREP_CORE_V1`的48个唯一token及内容哈希。版本、数量、内容或哈希任一不一致即停止。
2. 只读取`通用词库资格=纳入`且英文关键词非空的Sheet2行。`不纳入`和`待复核`零混入。把锁定主键、英文词和资格输入`scripts/keyword_deterministic_core.py word-frequency`；确定性核心对统计副本执行NFKC和英文小写，以空白、标点和连字符分隔，不覆盖原词。
3. 只从单词序列删除`EN_PREP_CORE_V1`中的精确token；保留数字、冠词`a/an/the`、连词`and/or`、`up/down/off/out/as/like`、其他停用词和可识别非英语词面。不得做上下文词性重判或多词介词识别。
4. 单词频次只累计非介词token。
5. 将介词作为硬断点，在每个连续非介词词段内部生成相邻有序双词；不跨介词、不统计非相邻、不交换顺序。
6. 两表按次数降序、同次数词面字符升序；保留次数1。
7. 验证单词总数和每个连续非介词词段的`max(词数-1,0)`双词闭环，检查无介词词或含介词/跨介词双词。
8. 写入独立过程工作簿和manifest，扫描公式、渲染Sheet并目视复核。

## 质量标准

- 输入只来自Sheet2中`通用词库资格=纳入`的英文关键词，源工作簿不变；其他资格零混入。
- 单词表不含`EN_PREP_CORE_V1`中的token，双词不含这些token且不跨这些断点；保留词不得因停用词或语境被额外删除。
- 计数、排序和唯一词面可机械复算，次数1保留。
- 固定确定性核心版本、输入人口哈希、`EN_PREP_CORE_V1`内容哈希和结果计数写入manifest；版本或哈希漂移不得断点复用。
- 输出不含ABA、搜索量、流量层、权重、竞争、趋势或广告结论。
- Skill保持draft/planned，未完成真实三案例不称verified。

## 异常处理

Sheet2/通用词库资格/关键词列/哈希/介词表版本、48个唯一token或内容哈希无法唯一锁定，资格人口或主键不闭合，发现白名单漂移、运行时词性重判、分词后异常、计数不闭合或渲染失败时停止并保留源文件。
