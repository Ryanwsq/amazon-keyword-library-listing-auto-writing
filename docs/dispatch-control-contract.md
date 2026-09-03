# Dispatch control contract

本合同只拥有调度身份、幂等派发、消息增量和技术恢复；不拥有业务判断、来源选择、完成门或质量结论。入口是`scripts/dispatch_guard.py`，能力仍为`planned`。控制器不会调用Codex任务工具或外部服务，也不自动生成业务完成状态；主任务和拥有副任务必须实际执行下列接线。

适用于fresh-collection/recent-library-reuse的新业务阶段，不把只读初始化、登录准备或approved iteration维护假装成业务Run。上述准备/维护消息也不授权开展采集或装配。

## 身份与状态隔离

- 当前Run来自主任务本次输入锁及本次派发消息，不从最近文件、旧handoff、任务标题或历史聊天猜测。`--run`必须独立取自该锁，不能反向照抄待验旧文件。
- 固定逻辑角色/标题以`docs/thread-roles.md`为准。主任务先读取本机映射，再用当前Codex任务元数据取得独立`observed`快照；接收端使用自身真实任务身份和执行cwd。不得把目标spec复制成observed冒充核对。
- envelope锁定Run、模式、run_type、revision、三输入哈希、角色、阶段键、固定目标身份、合同文件字节SHA-256、依赖文件字节SHA-256及当前Run输出目录。`contract_file_sha256`是文件字节哈希，不与fresh合同内部的canonical `contract_sha256`混用。
- 主任务与每个副任务各自只写自身工作树的`.local/dispatch-control/journal.sqlite3`。这是跨Run任务占用和去重的本机控制元数据，不是业务产物；必须Git忽略，不进入业务工作簿、process manifest或共享仓库。原始/过程/最终业务文件仍只写`.local/runs/<Run_ID>/`。每Run的request、spec、envelope、回执及事件存其本机Run目录。
- 不清空或重建ledger来解除占用。换设备先按既有本机映射重建规则核对任务真实状态，不因缺少旧ledger认定旧任务未运行。

## 新阶段派发与接收

1. 主任务完成原有输入、固定任务身份、版本、登录和依赖门。`build`从当前合同机械生成spec，不手工抄写Run/revision/stage key/三输入哈希。request只填写`contract_path、stage、target、output_root、admission`；target字段为`thread_id、host、title、cwd`，均只在本机。
2. fresh的admission给出`status_dir`及来源阶段的`preflight`路径。脚本执行原有`ready`和规则校验，冻结实际依赖status/preflight文件哈希，不变更业务图。复用见下节，不强求fresh上游。
   登录preflight使用本次派发的不可变快照，不与其他分支共用可变文件；另一个提供商更新登录状态不改写本派发快照。首次真实查询前仍由来源Skill复核实际登录，快照不是持续认证保证。observed中的status从当前产品任务状态机械规范为`idle`等单值，不能用上次空闲快照替代本次读取。
3. 主任务`reserve`在本机SQLite事务中先占位。只有第一次返回`allowed_to_send=true`才调用既有`send_message_to_thread`。相同`Run+role+stage_key`只对应一个dispatch；相同键但envelope不同阻断。同一个目标任务有未解决派发，或实时状态不为空闲时，不插入另一Run/阶段。无依赖的其他固定任务不被占用阻断。
4. 发出的紧凑消息包含当前Run、role、dispatch_id、envelope绝对路径、唯一目标、允许动作和必读入口，不重复粘贴全文合同/历史报告。成功后用`sent`记录dispatch_id、返回任务ID和实际工具response；实际tool call ID可用时也保留，不能编造接口未返回的ID。不把“发送成功”当“业务完成”。
5. 拥有副任务在新阶段第一次业务动作、查询或输出写入前执行`accept`。脚本核对自身任务、实际进程cwd、Git HEAD、目标规则文件、合同/依赖哈希和输出目录；旧Run、旧输入、错误角色/任务或越界输出失败即回主任务。不能等工作簿已生成才检查。
6. `accept`只有首次返回`execute=true`才启动新阶段。重复收到原派发只回已有状态，不重新采集或装配。脚本返回的`output_root`是本次唯一业务输出根，继续沿用该模块获准子目录名称，不更改原业务目录结构。
7. 每个拥有副任务仍完整读取自身Skill及直接合同，并执行所有业务门。受控继续原已接受阶段不等于新派发：明确的登录恢复/中断续跑消息须引用原dispatch，先复核同一锁和本地断点，再按既有Skill继续未完成部分；不能借“继续”重复已成功查询、覆盖冻结产物或另开旧Run。

例：所有参数都是本机获准路径，命令中的占位符不得原样执行。

```text
python3 scripts/dispatch_guard.py build --run <current-run> --input <request.json> --out <current-run-spec.json>
python3 scripts/dispatch_guard.py reserve --run <current-run> --ledger <local-journal> --input <spec.json> --observed <live-task.json> --out <envelope.json>
python3 scripts/dispatch_guard.py sent --run <current-run> --ledger <main-journal> --input <send-receipt.json>
python3 scripts/dispatch_guard.py accept --run <current-run> --ledger <owner-journal> --input <envelope.json> --observed <own-live-task.json>
```

`--out`只能写当前cwd下的当前Run目录，已有不同文件拒绝覆盖。reserve之后崩溃仍保留占位；不能因为没有拿到返回值而再次发送。

## 网络不确定与受控恢复

- 超时、断线、没有最终回复或看不到新消息不等于未送达，不自动重发或创建替代任务。
- 主任务读取精确目标任务的派发记录/turn和工具回执，保存与dispatch_id绑定的本机reconciliation evidence。字段为`dispatch_id、thread_id、tool_call_id或observed_turn_id、observed_task_status、outcome`；不能用无内容的“看过了”自证，也不能编造接口未返回的ID。
- 只有明确`definitely_not_sent`、`business_executed=false`且目标idle时，`reconcile`给同一dispatch一次重发授权；再次请求不再授权。若第二次又不确定，继续查证，不循环重发。
- 已送达使用`delivered`修正传输状态；不会再次发送。失败后改输入/规则/阶段键前，须确认旧执行已结束；`closed`需要目标idle及`execution_stopped=true`，主任务与拥有任务分别关闭自身ledger占用，之后新锁才可派发。旧事件不能恢复已关闭任务。
- 登录仍按原入口和用户升级门；业务失败、QA未执行和行级缺口的含义不由本控制器重定义。
- 明确继续未完成原阶段时，`resume_existing`要求精确任务已停、`execution_stopped=true、authorize_resume=true`，重验同一合同后只允许原dispatch续跑，不生成新发送许可、不清空事件序号或旧证据；已完成/取消阶段不能重开。主任务与拥有任务各记录恢复回执，再按原Skill继续。来源登录状态文件在新查询前需更新时按原运行合同重新核验并冻结；已冻结依赖发生变化不能伪装成相同派发续跑，需先关闭旧占用，再由主任务生成新锁/新派发。

## 紧凑事件与等待

拥有任务先在自己的ledger用`observe`登记事件，再向主任务发送同一小事件；主任务用自己的ledger核验。事件包含`dispatch_id、run_id、role、stage_key、revision、input_hashes、thread_id、output_root、seq、status、cursor`；seq为该派发严格递增正整数，cursor保存产品返回的原值，不按字符串比较顺序。成功回传另含`population、gaps、verification=owner_checks_completed、artifacts[{path,sha256}]`，指向当前Run的工作簿与manifest/检查证据；不把原始逐行数据贴进消息。

- 相同seq、相同内容仅确认一次；相同seq内容不同阻断。较旧seq不回退当前状态。仅cursor/seq变化更新控制状态，不重新读取报告或重跑门。
- 状态、人口、证据哈希、缺口或错误变化必须返回主任务；错误Run/任务/输入/输出即使是重复或较旧消息也必须先拦截，不能静默去重。
- 完成事件核对实际文件路径/字节哈希及人口字段，终态不得被迟到running覆盖。`observe`不是业务验收；主任务仍按原Skill复核人口、语义风险、资格、字段、完整性及所有适用Gate，然后才写runtime stage status。
- 同时等待已有并行任务，使用各自最新cursor；优先消费完成/异常事件。没有变化不调用`read_thread`重读全文、不重复派发、不重复粘贴报告。需要诊断具体异常才定向读取对应turn/文件。
- 主任务需要进行短进度沟通时只使用已知状态，不为“保持活跃”制造额外查询。等待按产品可用机制与单次等待上限执行；不创建额外自动化、任务或守护进程。下游依赖闭合后立即按原并行图派发，不能为合并通知而延迟就绪分支。
- 小事件和完整证据各有作用：任何必读Skill/合同及完整业务人口检查都不能被状态摘要、哈希缓存或去重替代。

## recent-library-reuse 接线

先完整执行operations的复用合同；dispatch guard不负责判断30天资格或七Sheet业务等值。独立复用合同使用`input_hashes`保存当前三项输入，`rule_owner_hashes`保存`仓库相对拥有文件: SHA-256`映射；其余事实/source血缘与必需拥有文件仍按原复用合同全部锁定。test-validation明确`qa_mode`和`change_flags`，变更时仍full-regression。

主任务资格预检完成后保存`reuse-admission.json`：`run_id、stage、contract_file_sha256、ready、evidence_files[{path,sha256}]`。assembly指向新事实/历史source及资格/兼容性检查证据；测试QA另指向本次已完成装配及适用质量路由证据。`admission.receipt`是该文件路径/哈希。脚本由合同字节哈希、stage及自身版本生成派发阶段键，不调用fresh graph，不制造上游completed。仅允许装配和test-validation QA；装配封口仍复核期限、规则、八Sheet及全部原门。

## 验证与限制

`python3 scripts/test_dispatch_guard.py`覆盖重复/并发派发、接收重放、不同Run争用、错误身份/输入/目录、哈希漂移、迟到与冲突事件、登录/异常不漏报、网络不确定及复用路由。脚本夹具不连接真实任务，不产生案例/P1，也不能证明真实节省比例。修改后真实test-validation仍full-regression，并核对主键人口、业务判断/字段、输出和Gate覆盖等价。

本脚本是强制执行入口协议，不是对Codex所有工具调用的全局拦截器；如果任务绕过入口，工具本身不会被此脚本沙箱阻止。下一轮应检查reserve/accept/observe回执是否齐全，缺失不得宣称此调度能力已验证。
