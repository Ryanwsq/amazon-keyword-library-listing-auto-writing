# 输入合同

先读取 `project-adapter.md`。本文件下述“单一输入工作簿”合同仅适用于 `full_pipeline`；本项目默认 `downstream_intake` 的 01–05 封存包合同及 06 独立关键词接口由适配层定义。

## 固定必需 Sheet

### 1. 新品基础信息

恰好一条产品记录，列名与顺序固定：

`ASIN｜产品类型｜产品人群画像｜使用场景｜用途｜核心卖点｜市场选择`

`市场选择`是必填下拉字段，只允许`Amazon-US`或`Amazon-DE`。它在预检后规范化为内部`marketplace`锁，并派生不可拆分的站点路由：`Amazon-US=amazon.com/10001/Alexa for Shopping/English`；`Amazon-DE=amazon.de/80539/Rufus/German`。`--marketplace`只用于再次断言，不能替代工作簿字段；两者同时存在必须一致，缺失或不支持的站点阻断，不能静默默认US。

### 2. 新品基础配置

恰好一条产品记录，列名与顺序固定：

`产品尺寸参数｜产品包装参数｜包含配件/组件｜卖点`

允许把 `包含配件 / 组件` 规范化为同一字段。

### 3. 竞品对标ASIN

列名与顺序固定：

`价格竞品｜颜色竞品｜尺寸竞品｜材质竞品｜风格竞品`

五类各至少一个合法 ASIN。同一 ASIN 可以跨类别重复；执行前去重并保留全部类别标签。该 Sheet 用于商品字段审计和客观参数对比，不等于正式市场统计样本池。

### 4. 登录准备

列名与顺序固定：

`服务｜账户别名｜凭据引用｜登录方式｜说明`

固定三行服务：`SIF`、`卖家精灵`、`Amazon`。SIF与卖家精灵必须填写账户别名、该电脑上的非敏感凭据引用（例如浏览器配置名或密码管理器条目名），登录方式只允许`浏览器已保存凭据`或`本机密码管理器`；Amazon的登录方式固定为`用户手动`，账户别名和凭据引用不填写。

本Sheet严禁增加或填写密码、验证码、Cookie、token、secret等字段。预检会直接拒绝任何暗示保存明文认证信息的表头。凭据引用只用于指导实际拥有任务在本机调用已保存登录能力，不是密码本身，也不进入公开Run包。

## 推荐 Sheet

### 5. 市场竞品ASIN池

列名与顺序固定：

`ASIN｜父体ASIN｜是否启用｜采样用途｜备注`

- `是否启用` 允许：`是/否`、`Yes/No`、`1/0`；空白默认启用。
- `采样用途` 可写 `五维洞察`、`痛点频率`、`关键词`，多值用分号分隔；空白表示三者均使用。
- 正式 Coverage 和痛点频率要求至少 10 个去重、相关、有效 ASIN。
- 同父体重复子体应只保留一个代表 ASIN；无法确认父体时保留并在下游标记待核验。

缺少本 Sheet 时，临时回退到 `竞品对标ASIN` 的去重集合，并自动标记样本风险；不得把两个 ASIN包装成正式市场统计。

完整输入与站点锁定后，`full_pipeline`按[任务会话登录合同](login-session-contract.md)先进入固定八会话登录门。主任务立即引导用户准备全部会话：SIF/卖家精灵任务按本Sheet引用使用已保存凭据或本机密码管理器，六个Amazon拥有任务由用户逐任务手动登录。未全部回执前不得发起查询、提问、导出或联想；主任务或其他会话的Cookie不能代替拥有任务。

## ASIN 与值校验

- ASIN 规范化：去不可见字符、去首尾空格、转大写，匹配 `^[A-Z0-9]{10}$`。
- 本品 ASIN 不得出现在任一竞品集合。
- 必需字段不能空白；`无/不适用/None/N/A` 是明确事实，不等于空白。
- 数值、单位和范围必须保留原文；预检不擅自换算或修复。
- 公式错误、合并单元格导致值不可读、工作表歧义属于阻断错误。

## 预检输出

`validate_input.py` 输出 JSON：

- `valid`：是否无阻断错误。
- `errors[]`：阻断错误，必须一次性报告。
- `warnings[]`：可继续但会降级的风险。
- `product_asin`。
- `benchmark_asins[]`。
- `market_asins[]`。
- `formal_sample_ready`。
- `marketplace`及`marketplace_route`。
- `login_profiles`：只含SIF/卖家精灵/Amazon的账户别名、凭据引用和登录方式，不含秘密。

只有 `errors[]` 为空才能启动 Alexa 阶段。警告不会阻断 Run，但必须进入质量闸门和决策包。

新建schema2.0 Run时，`pipeline_state.py init` 必须同时传入 `--product-asin <已核对的本品ASIN>` 和 `--marketplace <Amazon-US|Amazon-DE>`，分别登记为`input.product_asin`、`marketplace/input.marketplace`，并保存完整`marketplace_route`与输入哈希。主线程先把这些值与预检结果或封存清单逐字段核对；状态脚本只检查格式和后续身份一致性，不替代工作簿事实预检。不修改已有schema1.0或旧schema2.0 Run。

每个实际拥有任务使用`pipeline_state.py confirm-login-session`登记独立回执，字段至少含`session-key/task-id/host/dispatch-id/status/observed-domain/evidence-file`；Amazon再带锁定邮编，需要购物助手的角色再带Alexa或Rufus。八份回执齐全后使用`finalize-login-gate`完成总门。任一会话失效时使用`invalidate-login-session`，只阻断其直接依赖阶段。完整矩阵、SIF同提供商MCP例外和证据边界见[任务会话登录合同](login-session-contract.md)。

## 关键词跨项目附加输入（不改变原始三表）

进入关键词支线前完整读取[关键词交接合同](keyword-handoff-contract.md)。随原输入明确发送三组来源定位（产品基础信息配置、产品配置卖点、竞品对标ASIN）、目标Amazon类目及用户确认的多稳定产品类型细分是/否、站点、品牌与当前SKU事实身份、保留原顺序的直接竞品及已有类型证据、双方Run/revision、来源与合同哈希。不用“其他字段”代替此对象；不修改以上Alexa三表，不要求用户提供核心词，不由Listing预筛代表ASIN。关键词Run尚未创建时允许null，正式回执必须补录。

## 写作阶段附加输入（不改变原始三表）

- 标题/IH 知识库：`knowledge-base/listing-title-highlight-writing-rules.md`；关键词来源固定为当前已验收 06 的 `SKU可用关键词库` Sheet，不另索要 Sorftime 或竞品词库。
- 用户可提供直接竞品的标题/五点原文、文件或明确页面供写法参照；登记 ASIN/URL（已知时）、提供时间与来源。旧标题仅作表达结构参照，不套用其字数或现行规则。
- 竞品参考仅进入写作支线，不替代 Alexa 专属审计/洞察，不作为本品材质、参数、功能、收益或关键词来源。
- 实际文案 JSON 锁定当前 Run、ASIN、标题/IH/全部 Bullet及写法版本（v2.2新Run及草案锁定bullet_count_policy=coverage_based_5_to_6，至少5条、通常5–6条；超过6条附真实环境/条数确认source_lock），并带 `source_locks`：00、人工事实补充、06、07 的精确路径与 SHA-256；参照材料及规则版本也在证据中登记。
- 07 信息确认后进入独立文案交互；正文和来源确认规则见 `stage-copy-review.md`。文案未确认不生成最终 ST/10。
