## Why
当前NovelGen系统使用JSON文件存储中间结果，缺乏持久化状态管理和记忆检索能力，导致生成过程中无法保持角色状态一致性和利用历史内容上下文。

## What Changes
- 新增persistence capability：提供数据库和向量存储基础设施
- 修改orchestration capability：在每个链执行后自动保存状态快照到数据库
- 添加核心数据模型：EntityStateSnapshot、StoryMemoryChunk等，支持状态版本化和文本分块存储
- 实现抽象接口层：runtime/db.py和runtime/vector_store.py，与具体存储实现解耦

## Impact
- Affected specs: persistence (新增), orchestration (修改)
- Affected code: novelgen/models.py, novelgen/runtime/orchestrator.py, 新增runtime/db.py, runtime/vector_store.py
- **BREAKING**: 无破坏性变更，现有生成流程保持不变
