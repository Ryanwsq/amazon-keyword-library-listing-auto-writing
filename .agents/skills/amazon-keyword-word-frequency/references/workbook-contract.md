# Word-frequency workbook contract

## Input lock

锁定第二板块工作簿名称和SHA-256、Sheet2唯一Keyword_ID总人口、`通用词库资格=纳入`的唯一Keyword_ID/英文关键词人口、词频规则版本，以及固定英语介词白名单`EN_PREP_CORE_V1`的版本、48个唯一token和内容SHA-256。只读取资格为`纳入`且非空的Sheet2英文关键词，不覆盖源文件。版本、数量、内容或哈希任一不一致即停止。

## Tokenization

1. 对统计副本执行Unicode NFKC。
2. 英文字母小写。
3. 空白、标点和连字符作为分隔符。
4. 不合并单复数、同义词、拼写变体、词干、词序或翻译。
5. `通用词库资格`只作上游人口筛选，不重算；不读取ABA、搜索量、来源、SKU事实、竞争或广告字段。

## Preposition filter

使用固定英语介词白名单`EN_PREP_CORE_V1`，按ASCII字典序的完整48-token清单为：

```text
about, above, across, after, against, along, among, around, at, before,
behind, below, beneath, beside, between, beyond, by, despite, during, except,
for, from, in, inside, into, near, of, on, onto, opposite,
outside, over, past, per, since, through, throughout, to, toward, towards,
under, underneath, until, upon, via, with, within, without
```

只对标准化后与上述清单精确相等的单token应用过滤。白名单token：

- 不进入单词频次；
- 是相邻双词的硬断点；
- 不得在删除后跨越连接两侧token。

例如`paddle board for adults`只计单词`paddle/board/adults`和双词`paddle board`，不计`for`、`board for`、`for adults`或`board adults`。`a/an/the`、`and/or`、`up/down/off/out/as/like`明确保留；它们不是本版本白名单成员，不得因停用词、常见词或运行时语境额外删除。

本组件不做上下文词性重判，也不识别`because of`、`in front of`等多词介词；每个标准化token只按固定清单成员身份机械处理。

介词清单、版本、token数量和内容SHA-256必须写入manifest，不在不同Run间静默改变。任何增删、别名、词典替换或顺序外重写都必须先形成新的已确认版本，不得仍标记为`EN_PREP_CORE_V1`。

## Counting and sorting

- 单词：每个非介词token出现一次计一次。
- 双词：在每个连续非介词词段内部生成相邻有序pair。
- 排序：次数降序；同次数标准化词面字符升序。
- 保留所有唯一词面，包括次数1。
- 不建立高/中/低频、权重或占比。

## Fixed output

一个独立过程工作簿，只含一张`词频统计`Sheet。两张表并列：

| 单词词频 | 相邻双词词频 |
|---|---|
| `排名、单词、出现次数` | `排名、相邻双词、出现次数` |

## Manifest

记录输入名称/哈希、Sheet2总人口、`纳入/不纳入/待复核`资格人口、实际输入人口、分词规则、介词清单/版本/token数量/内容SHA-256、原始token数、按白名单token分别统计的过滤次数、过滤介词总数、有效单词总数/唯一数、双词总数/唯一数、保留词抽查、公式/渲染、输出哈希、状态和唯一问题文档。

## Quality gate

1. 输入行数等于Sheet2中`通用词库资格=纳入`且英文关键词非空的行数；`不纳入/待复核`零混入。
2. 单词计数和等于全部非介词token数；输出无介词。
3. 双词计数和等于各连续非介词词段`max(词数-1,0)`之和。
4. 双词不含介词且不存在跨介词组合。
5. 输出行数等于唯一单词/双词数，排序稳定且保留次数1。
6. `a/an/the`、`and/or`、`up/down/off/out/as/like`若在输入中出现，必须按普通token进入对应单词/双词候选，不得被白名单误删。
7. 工作簿只有一张词频Sheet；公式扫描、渲染和目视复核通过。
