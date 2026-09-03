# Repository identity

2026-09-03按用户要求，将原仓库名加上全英文“Listing自动编写”：

- 旧名：`Ryanwsq/amazon-keyword-library`。
- 新名：`Ryanwsq/amazon-keyword-library-listing-auto-writing`。
- [当前GitHub入口](https://github.com/Ryanwsq/amazon-keyword-library-listing-auto-writing)。
- GitHub repository ID仍为`1340369974`；此次改名不新建仓库，不重写原提交历史。
- 默认分支仍为`main`；项目ID、Skill名称、角色包路径、Run合同、判断边界和输出结构不随远端名称改变。

已有克隆在确认它原本指向该仓库后，只更新远端URL；不要将下面的命令用于其他不相关仓库：

```sh
git remote set-url origin https://github.com/Ryanwsq/amazon-keyword-library-listing-auto-writing.git
git remote -v
```

本地文件夹可以保留原名称，受控工作树与真实任务绑定也不会因GitHub改名而自动迁移。不要通过批量替换所有`amazon-keyword-library`字符串来改名，否则会破坏内部项目ID和引用。

历史handoff及`migration/`中先前的合仓/部署审查记录保持当时版本；其中旧仓库名和适配哈希不是当前在线状态。当前文件的精确发布哈希仍由`migration/release-files.json`拥有。本批只变更当前仓库入口文案，不修改知识、Skill、原始资产、业务脚本或案例状态。
