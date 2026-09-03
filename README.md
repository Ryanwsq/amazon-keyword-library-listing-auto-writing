# Amazon Keyword Library + Listing Auto Writing

同一 Git 仓库、一个 Codex 项目中的两个独立业务模块。Listing 主任务是整条产品输入到 Listing 交付的统一入口；关键词主任务管理关键词子流程及其专责模块。完整 Skill、知识、判断边界、双 Run、正式回执和两道人机确认门均保留，不合并业务执行权。

当前GitHub仓库：[amazon-keyword-library-listing-auto-writing](https://github.com/Ryanwsq/amazon-keyword-library-listing-auto-writing)。这是原仓库改名，不是新仓库；两个内部项目ID和相对目录保持不变，历史交接中的旧名称保留其当时含义。见[仓库名称与版本记录](docs/repository-identity.md)。

| 项目 | 工作入口 | 负责的结果 |
|---|---|---|
| Amazon关键词词库 | [项目说明](projects/amazon-keyword-library/README.md) · [任务入口](projects/amazon-keyword-library/AGENTS.md) | 三来源关键词采集、清洗、分类与分析、八Sheet工作簿；以及合规近期词库复用 |
| Listing撰写信息决策 | [任务入口](projects/amazon-listing-pipeline/AGENTS.md) | SKU终筛、标签/痛点/卖点决策、Listing写作与最终装配 |

业务任务从所属项目目录或其明确的角色包启动。不要同时把两个项目及所有部署副本加入一个无边界的Skill发现根，也不要把全局同名Skill作为缺失文件的备用来源。

跨项目流向保持：Listing主任务锁定输入 → 关键词主任务 → 正式完整关键词输出和回执 → Listing主任务核验并给当前Run READY → SKU任务终筛 → Listing后续流程。原来的三组输入、双Run/当前事实锁、分类缺失兼容和二类词/F2区分不因合仓变化。

## 新电脑从哪里开始

只克隆这一个仓库，将总仓目录添加为一个 Codex 项目；不另建独立 Listing 代码仓库，也不需要再为两个子目录分别添加 Codex 项目。在同一个目标项目中初始化 Listing 总控和其完整注册角色，以及关键词主任务和其固定副任务。已有目标任务先核对复用，缺少任务只有获得用户明确创建授权后才补齐；仅打开仓库或读取本文不授权创建任务。

当前角色清点为 Listing 10 个（1 总控、7 业务、2 接收整理）和关键词 11 个（1 主任务、10 长期副任务）；具体职责和加载要求仍以各项目拥有的角色表、当前注册表为准。日常整条流程向 Listing 总控提交输入；明确的关键词独立任务仍可交关键词主任务。旧电脑或旧项目的任务、聊天、原始输入和历史产物完整保留，不迁移、不删除，也不自动成为新 Run 输入或新目标的已加载任务。

```sh
git clone https://github.com/Ryanwsq/amazon-keyword-library-listing-auto-writing.git akw
cd akw
```

示例刻意使用短目录名`akw`；GitHub名称不要求与本地目录同名。Windows建议使用短路径，例如`C:\work\akw`，避免长角色包路径叠加深层用户目录。仓库的`.gitattributes`禁止Git自动换行转换：冻结清单校验文件原始字节，不能用重新生成哈希来掩盖CRLF漂移。

先准备Python 3.11或更新版本、Node.js 20或更新版本及Git。关键词装配隐私检查还依赖支持`-Z1`和`-p`的`unzip`；装配夹具额外需要支持`-q -r`的`zip`。这些工具必须在运行任务的同一个环境中可执行，不能仅在另一套终端里可用。Windows不默认视为已安装；缺少时先由设备管理员安装兼容工具，不能跳过隐私检查。工作簿生成、重载、公式及图表渲染另外需要执行环境提供的Spreadsheets Skill及其规定的Artifact Tool；仓库不打包该运行时，也不能用只有openpyxl的环境冒充已具备完整渲染能力。

macOS / Linux，在总仓根执行：

```sh
python3 -B scripts/check_environment.py
python3 -B scripts/validate_projects.py
```

Windows PowerShell，在总仓根执行：

```powershell
py -3 -B scripts/check_environment.py
py -3 -B scripts/validate_projects.py
```

环境检查不读取密钥、不调用付费接口、不证明网站已登录。通过后仍需完成下面的账号、MCP和角色绑定预检。使用Codex附带运行时时，应在本机发现其路径，不照抄另一台电脑的绝对路径。完整首启与迁移步骤见[跨电脑启动说明](docs/cross-device-setup.md)。

## 哪些网站账号需要登录

| 网站 / 能力 | 哪个任务使用 | 账号和登录要求 |
|---|---|---|
| [SIF官网](https://www.sif.com/) | 关键词：SIF竞品反查 | 有竞品流量词查询及所需字段访问权限的SIF账号；在SIF副任务实际使用的浏览器会话登录。优先网页，未登录先回传主任务`awaiting_login`；只有用户明确无法在当前设备/会话登录，才允许同提供商MCP备用。 |
| [卖家精灵官网](https://www.sellersprite.com/) | 关键词：关键词挖掘 | 有关键词挖掘及完整官方导出权限的卖家精灵账号；在卖家精灵副任务实际使用的浏览器会话登录。每个获准种子只成功导出一次。未登录先回传主任务，不直接切MCP；已登录但完整官方导出链路仍不可用时才允许同提供商MCP备用。 |
| [Amazon US](https://www.amazon.com/)搜索联想 | 关键词：Amazon联想 | **不登录**，固定US、All、邮编10001；首选内置浏览器，无法稳定操作时按原合同使用普通Chrome备用。不得为了Alexa登录而污染这个未登录采集环境。 |
| Alexa for Shopping | Listing：商品信息审计、五维洞察、痛点等获准上游任务 | 具有可用Alexa for Shopping访问权限的Amazon买家账号或已授权连接；在对应任务实际使用的会话登录并确认能访问该能力。普通Amazon页面可打开不等于Alexa可用；Seller Central卖家账号也不能替代此能力。不可用时按所属Skill停止，不能换普通搜索、商品页或模型猜测。 |
| Sorftime账户中心 | 关键词：趋势备用来源配置 | 用于开通MCP、取得密钥、查询用量；不要求采集期间持续登录网页，不授权用其其他数据替代SIF或Alexa。 |
| 飞书 | 仅明确授权的云文档同步 | 能访问并编辑目标文档的飞书账号。不是关键词/Listing本地工作簿生产的必需账号，未要求同步时不因此阻断业务。 |

登录发生在**真正执行该模块的任务和浏览器会话**中，不能只在主任务或别的浏览器登录后就声称副任务就绪。账号、密码、验证码由用户直接在官网输入；不写进输入表、聊天、README、Skill、manifest或Git。每次实际采集前仍按所属Skill复核登录，Git拉取不会迁移Cookie。

## 需要配置哪些MCP

| MCP | 本项目需要的只读数据能力 | 使用边界 |
|---|---|---|
| SellerSprite MCP | 精确关键词的历史月搜索量；关键词挖掘作为获准备用入口 | 趋势首选提供商。准备有效密钥、所需接口权限和足够用量；网页会员与MCP可用次数分别检查。挖掘仍优先官网完整导出，不因MCP已配置而跳过网页。 |
| SIF MCP | 获准竞品ASIN流量词及合同所需SIF证据字段 | 仅按SIF网页登录备用条件启用。竞争判断仍只使用SIF的Top3点击份额和Top3转化份额；不能借机换成其他提供商指标。 |
| Sorftime MCP | 精确完整关键词的历史月搜索量 | SellerSprite趋势不可用时的备用。一个Run的全部趋势词和月份只使用一个提供商；不跨源补月，中途切换须按原合同重跑全部趋势人口。 |

MCP服务名可以因客户端配置不同而变化；启动时按提供商、工具参数和实际字段核对，不能只认同名插件。当前公开仓库不内置这些服务，不附送会员、额度或密钥；可看到工具列表不等于鉴权、权限、周期覆盖及额度都正常。Alexa和Amazon联想不因装好这三个MCP而获得替代来源。

### MCP配置步骤

1. 用本人或获授权组织账号进入各提供商官方后台，分别开通需要的MCP权限并取得连接配置。不要使用来历不明的第三方代理或把Cookie改装成备用接口。
2. 在当前电脑的Codex配置中登记服务地址、传输方式和官方要求的认证方式。配置是本机状态；仓库忽略`.codex/`、`.env*`等敏感文件，不提交真实配置。Codex支持`[mcp_servers.<name>]`、环境变量认证头及`codex mcp list`检查登记，详见[OpenAI MCP配置文档](https://developers.openai.com/codex/mcp/)。
3. 刷新连接后，在实际拥有任务中检查工具是否可见。先用提供商可用的连接/账户能力检查鉴权和额度；若没有余额接口就登录官方后台确认，不能把未返回用量写成0。业务接口的最小预检只在获准Run内按所属Skill执行，不为部署说明重复采集或导出。
4. 分开登记`工具已发现`、`鉴权可用`、`权限/用量`、`网页登录`；缺失项按模块合同报告。不得公开密钥、带密钥的URL、完整headers、Cookie或本机任务ID。

卖家精灵官方地址为`https://mcp.sellersprite.com/mcp`，认证头名称固定为`secret-key`。可使用以下**无密钥**配置结构，并在本机安全设置`SELLERSPRITE_MCP_SECRET`环境变量，让启动Codex的进程能够读取它；这不是让用户将密钥提交到仓库。[提供商接入说明](https://open.sellersprite.com/mcp/16)

```toml
[mcp_servers.sellersprite]
url = "https://mcp.sellersprite.com/mcp"
env_http_headers = { "secret-key" = "SELLERSPRITE_MCP_SECRET" }
```

Sorftime在官方账户中心激活MCP后提供服务地址和密钥，公开示例为`https://mcp.sorftime.com?key=<YOUR_KEY>`；含实际密钥的完整URL只能存本机敏感配置，不贴聊天、截图或Git。[Sorftime官方配置入口](https://www.sorftime.com/en-US/mcp)

SIF应使用本人账号在官方MCP入口提供的地址、认证字段和密钥；此仓库不猜测其认证方式，也不把另一提供商的`secret-key`头套给SIF。若后台无法提供或新任务无法发现对应只读能力，报告“SIF MCP未配置/待验证”，不要宣称备用链路已就绪。

统一校验入口只运行项目原有结构/依赖检查及迁移清单核对，不访问业务网站、不读取真实Run输入、不产生P1。需要机械回归时按[维护说明](docs/merge-and-publication.md)执行各项目原有测试。

迁移和发布范围见[维护说明](docs/merge-and-publication.md)。历史原始输入、XLSX、截图、日志、任务绑定和账号保留在原本机目录，不作为公共仓库内容上传。可发布的必要示例资产必须具有明确的脱敏审查记录，不能因安全过滤而静默丢失业务依赖。
