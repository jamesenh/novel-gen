---
name: /commit-code2
id: commit-code2
category: local
description: commit all code
---
## 目标

提交代码到当前分支

## 步骤

1. 检测当前工作区的暂未提交的代码
2. 根据代码的变更内容以及其中的文档生成对应的commit message
3. 提交代码

## 限制

1. commit message中需要使用中文描述代码变更
2. 提交代码时标注好当前的修改人是"jamesenh"
3. 标注好修改的时间
4. 如果是基于openspec的提案则需要在提交信息中明确指明涉及到了哪些提案的修改
5. 只是提交代码, 不可push到远程分支