# 实施任务清单

## 1. 创建记忆工具函数层
- [x] 1.1 在`novelgen/runtime/memory_tools.py`中实现`search_story_memory_tool()`函数
- [x] 1.2 实现`get_entity_state_tool()`函数用于查询实体状态
- [x] 1.3 实现`get_recent_timeline_tool()`函数用于获取时间线上下文
- [x] 1.4 添加错误处理和降级逻辑

## 2. 实现记忆上下文检索链
- [x] 2.1 创建`novelgen/chains/memory_context_chain.py`文件
- [x] 2.2 设计Prompt模板，引导LLM分析场景需求
- [x] 2.3 实现`create_memory_context_chain()`函数
- [x] 2.4 实现`retrieve_scene_memory_context()`主函数
- [x] 2.5 配置PydanticOutputParser，输出`SceneMemoryContext`对象
- [x] 2.6 实现JSON文件持久化逻辑

## 3. 编写单元测试
- [x] 3.1 创建`test_memory_context_chain.py`测试文件
- [x] 3.2 测试基础的记忆检索功能
- [x] 3.3 测试降级处理（数据库不可用时）
- [x] 3.4 测试输出JSON格式正确性
- [x] 3.5 手动验证检索结果的相关性

## 4. 文档和集成准备
- [x] 4.1 在chain文件中添加完整的中文docstring
- [x] 4.2 更新README或相关文档说明新功能
- [x] 4.3 确认与orchestrator的集成接口（不实现集成，仅确认接口）
- [x] 4.4 验证所有测试通过
