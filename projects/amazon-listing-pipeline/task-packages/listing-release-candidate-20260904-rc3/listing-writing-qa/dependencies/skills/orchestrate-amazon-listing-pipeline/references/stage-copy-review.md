# 阶段：标题、Item Highlights与五点文案交互确认

适用于 `schema_version=2.0` 的新Run。旧版已封存Run保持原合同；不得因升级Skill而静默重开或补跑历史任务。

## 两道独立确认

1. 信息决策确认：07的标签、卖点/配置优劣势、痛点与样本、P0、主图、A+、ST口径七类对象。未通过前不写最终文案。
2. 文案确认：在第一道门后生成Title、Item Highlights及全部Bullet（当前至少5条、通常5–6条）的可讨论草案。主线程展示、接收修改、逐项确认完整文字；它不是再次让用户确认只有排序的表。

采用新的标题知识库 `knowledge-base/listing-title-highlight-writing-rules.md` 和五点软性规则。允许只读直接竞品写法参考，记录来源，不移植其产品事实、关键词准入、原句或不合规声明。无需为参考写法新建任务；现有写作任务产草案，主线程负责人机讨论。

## 顺序与停止条件

`07完整确认 → 09关键词/标签计划 → listing_draft → copy_checkpoint → 最终ST与09实际覆盖回填 → 10扩展装配 → final_qa`

- 09草案可记录计划落位，尚未产生的实际次数留空，不用0冒充未执行。ST此时只有候选池，不生成最终ST。
- 写作任务产出带版本的 `evidence/copy-review/listing-copy-draft-vNN.json`，主线程在聊天展示英文原文、必要中文解释、事实依据、核心词源、字符计数和需要取舍的项。无需每次固定生成多套版本。
- 讨论范围含Title、Item Highlights、Bullet 1–N（当前policy至少5条、通常5–6条，五条已完整就不补第六条）。用户只改其中一项时，只重写受影响字段，但仍锁定整套最新文案快照；其他已经确认字段沿用。
- 用户只确认标签、说“继续写”或没有回复，都不能代替文案确认。明确确认当前完整草案或逐项全部确认后才可调用 `confirm-copy`。
- 未确认时：`copy_checkpoint=needs_input`、`overall_status=WAITING_COPY_CONFIRMATION`；不产出标为最终的10、不生成最终ST、不标记final_qa完成。
- 如用户要求先看Excel草案，可以输出清楚标注DRAFT的预览，但不能占用已封存最终文件路径，不能标为可直接提交。

## 机器可读草案合同

JSON包含：

| 字段 | 要求 |
|---|---|
| run_id / asin / revision | Run_ID必须一致；asin为十位大写字母/数字并匹配input.product_asin；revision为非空版本字符串；不得继承其他Run |
| title | 完整Title英文 |
| item_highlights | 完整Item Highlights英文 |
| writing_rules_version | 新v2.2 Run草案须与manifest的writing_rules_version一致；旧2.0无此字段仍沿用原五条合同 |
| bullet_count_policy | 新Run和草案共同锁定coverage_based_5_to_6；至少5条，按必要信息覆盖决定5或6条；旧v2.2缺该字段沿用原锁定合同，不静默迁移 |
| bullet_points | 非空英文字符串数组；当前policy至少5条、通常5–6条，不凑第六条，也不因名称“五点”截断已确认六条 |
| bullet_count_approval | 当前policy仅超过6条时必填：count、confirmed_by、note、source_lock(path/sha256)；锁定真实用户条数确认及目标环境说明并纳入source_locks。5或6条无需单独条数审批，但完整正文仍须确认；少于5条不准入。旧v2.2无policy时保留原非6条审批逻辑 |
| source_locks | 每项为path、sha256；覆盖已确认07、已验收06、原00和所有人工补充事实文件 |
| field_notes | 字段任务、采用关键词原文、事实指针、参考竞品写法与未采用理由 |

用状态脚本完成：

1. `set-stage --stage listing_draft --status running`。
2. 草案经词源/事实/基本规则预检后，`set-stage --stage listing_draft --status completed --output <草案JSON>`。
3. 展示后 `set-stage --stage copy_checkpoint --status needs_input` 并等待用户。
4. 收到明确确认，`confirm-copy --copy-file <被确认JSON> --confirmed-by User --note <用户原话及确认范围>`。
5. 生成最终ST、回填09，再进入 `listing_generation`。10中的Title、Highlights和五点必须逐字等于确认JSON；格式整理也不能静默改词。

草案文件、07、06或任何事实源哈希变化，文案确认失效。调用 `reopen-copy --reason <修改原因>` 保留上一版本/确认轨迹，再生成新版本并重新讨论；不能覆盖已确认JSON后假装仍已确认。07排序或事实变化还要回到相应信息决策门。实际后台强制限制造成正文修改时，同样需要确认修订版。

新版状态脚本在阶段完成时登记输出文件的 `output_sha256`；06必须与关键词验收时登记的哈希一致，不能只把磁盘上的新文件哈希写进草案就当作重新验收。

`confirm-copy` 同时核对草案完成登记时的SHA-256，拒绝对之后被改写的草案直接确认。已确认门只能先`reopen-copy`后再修改/登记/确认，`--force`不能绕过；完全相同正文和来源的重复确认只读返回`already_confirmed`，不重新盖章。确认记录保留ASIN、revision和完整正文快照，重开后旧确认与快照进入历史。新版本应另存文件，不覆盖先前已确认草案。

## 写法版本与讨论展示

新Run init锁定writing_rules_version=v2.2及bullet_count_policy=coverage_based_5_to_6；草案同值。至少五条，五或六条按必要信息覆盖决定，不另设五条例外审批；超过六条须有环境/条数确认。脚本只验证条数及证据，必要信息覆盖与自然可读性须人工逐项检查，不由计数合格替代。旧Run不通过补字段强行升级；用户授权局部改稿时在独立revision目录记录来源、写法版本及待确认状态，不改旧manifest；另有明确替换交付授权时先保留原件，再登记局部修订及其依赖变化，不改旧schema。条数确认只针对条数，不能代替实际正文确认。

展示标题“先月搜索量排序→卖点对照→选词”的取舍，Title已覆盖卖点清单、IH剔除项以及尚未表达T0/重要配置/必要标签的增量覆盖，以及每条的购买理由、用途组合、事实和补词。去重粒度未锁定时明确提出方案供用户确认，不默认所有共有词根禁用。写法规则更新不等于这些未决项或正文已确认。

涉及尺寸时，在field_notes中记录原值/单位、数值或可感知表达的选择及依据，检查Title/IH/Bullet，不能仅检查前两个字段。IH另记录同部件合讲的源卖点ID/原优先级、同收益下保留/省略项及原因；省略IH配置不删除事实，也不自动删除Bullet的有效解释。若新增“加宽”等表达，须有当前事实或用户确认，不给普通事实短语补造搜索指标。

## 五点字符数

不设置项目内部固定字数目标、下限、255或500上限，不再使用“长度例外”状态。仍报告字符计数，评估清晰、完整、画面感、冗余和可读性。实际Seller Central/类目模板的限制单独登记，未知写“后台限制待核验”；不将取消项目限制描述成取消Amazon限制。
