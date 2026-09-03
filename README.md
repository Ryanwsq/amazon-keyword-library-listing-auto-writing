# Amazon Keyword and Listing Workflows

同一Git仓库中的两个独立工作区。保留各自的主任务、专责模块、完整Skill、知识、判断边界及输出合同；这里只合并版本管理和发布入口。

| 项目 | 工作入口 | 负责的结果 |
|---|---|---|
| Amazon关键词词库 | [项目说明](projects/amazon-keyword-library/README.md) · [任务入口](projects/amazon-keyword-library/AGENTS.md) | 三来源关键词采集、清洗、分类与分析、八Sheet工作簿；以及合规近期词库复用 |
| Listing撰写信息决策 | [任务入口](projects/amazon-listing-pipeline/AGENTS.md) | SKU终筛、标签/痛点/卖点决策、Listing写作与最终装配 |

业务任务从所属项目目录或其明确的角色包启动。不要同时把两个项目及所有部署副本加入一个无边界的Skill发现根，也不要把全局同名Skill作为缺失文件的备用来源。

跨项目流向保持：Listing主任务锁定输入 → 关键词主任务 → 正式完整关键词输出和回执 → Listing主任务核验并给当前Run READY → SKU任务终筛 → Listing后续流程。原来的三组输入、双Run/当前事实锁、分类缺失兼容和二类词/F2区分不因合仓变化。

```sh
python3 -B scripts/validate_projects.py
```

该入口只运行项目原有结构/依赖检查及迁移清单核对，不访问业务网站、不读取真实Run输入、不产生P1。需要机械回归时按[维护说明](docs/merge-and-publication.md)执行各项目原有测试。

迁移和发布范围见[维护说明](docs/merge-and-publication.md)。历史原始输入、XLSX、截图、日志、任务绑定和账号保留在原本机目录，不作为公共仓库内容上传。可发布的必要示例资产必须具有明确的脱敏审查记录，不能因安全过滤而静默丢失业务依赖。
