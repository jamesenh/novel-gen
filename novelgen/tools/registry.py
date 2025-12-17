"""
工具注册表模块
管理可调用工具、安全门控、确认策略

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
import os
from typing import Optional, List, Dict, Any, Callable, Literal
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ToolCategory(str, Enum):
    """工具分类"""
    WORKFLOW = "workflow"        # 工作流操作 (run/resume/status/rollback/export)
    PREFERENCE = "preference"    # 偏好管理 (set/list/forget)
    GRAPH = "graph"              # 图谱查询 (whois/relations/events)
    MEMORY = "memory"            # 记忆检索 (scene/entity)
    FINE_GRAINED = "fine_grained"  # 细粒度生成工具 (章节计划/正文范围生成)


class ConfirmLevel(str, Enum):
    """确认级别"""
    NONE = "none"                # 无需确认
    NORMAL = "normal"            # 普通确认（可被 /auto on 关闭）
    DESTRUCTIVE = "destructive"  # 破坏性确认（始终需要）


class Tool(BaseModel):
    """工具定义"""
    name: str = Field(description="工具名称")
    category: ToolCategory = Field(description="工具分类")
    description: str = Field(description="工具描述")
    confirm_level: ConfirmLevel = Field(
        default=ConfirmLevel.NONE,
        description="确认级别"
    )
    slash_command: Optional[str] = Field(
        default=None,
        description="对应的斜杠命令（如 '/run'）"
    )
    handler: Optional[Callable] = Field(
        default=None,
        description="工具处理函数",
        exclude=True  # 不序列化
    )
    
    class Config:
        arbitrary_types_allowed = True


class ToolResult(BaseModel):
    """工具执行结果"""
    tool_name: str = Field(description="工具名称")
    success: bool = Field(description="是否成功")
    message: str = Field(default="", description="结果消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    executed_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="执行时间"
    )


class ToolPlan(BaseModel):
    """工具执行计划"""
    tool_name: str = Field(description="要调用的工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    requires_confirmation: bool = Field(
        default=False,
        description="是否需要确认"
    )
    confirmation_message: Optional[str] = Field(
        default=None,
        description="确认提示消息"
    )


class SessionState(BaseModel):
    """会话状态"""
    project_id: str = Field(description="项目ID")
    auto_confirm: bool = Field(default=False, description="是否开启自动确认模式")
    tool_call_count: int = Field(default=0, description="当前轮次的工具调用次数")
    max_tool_calls: int = Field(default=10, description="单轮最大工具调用次数")
    max_retrieval_attempts: int = Field(default=3, description="信息补齐最大尝试次数")
    retrieval_attempt_count: int = Field(default=0, description="当前信息补齐尝试次数")


class ToolRegistry:
    """工具注册表
    
    管理所有可用工具，提供工具查找、执行和安全门控功能
    """
    
    def __init__(self, project_dir: str, project_id: str):
        """初始化工具注册表
        
        Args:
            project_dir: 项目目录路径
            project_id: 项目ID
        """
        self.project_dir = project_dir
        self.project_id = project_id
        self._tools: Dict[str, Tool] = {}
        self._slash_commands: Dict[str, str] = {}  # slash_command -> tool_name
        
        # 从环境变量读取配置
        self.max_tool_calls = int(os.getenv("NOVELGEN_CHAT_MAX_TOOL_CALLS", "10"))
        self.max_retrieval_attempts = int(os.getenv("NOVELGEN_CHAT_RETRIEVAL_MAX_ATTEMPTS", "3"))
        self.confirm_by_default = os.getenv("NOVELGEN_CHAT_CONFIRM_DEFAULT", "true").lower() in ("true", "1", "yes")
        
        # 初始化会话状态
        self.session = SessionState(
            project_id=project_id,
            max_tool_calls=self.max_tool_calls,
            max_retrieval_attempts=self.max_retrieval_attempts
        )
    
    def register(self, tool: Tool):
        """注册工具
        
        Args:
            tool: 工具定义
        """
        self._tools[tool.name] = tool
        if tool.slash_command:
            self._slash_commands[tool.slash_command] = tool.name
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            工具定义或 None
        """
        return self._tools.get(name)
    
    def get_tool_by_slash(self, slash_command: str) -> Optional[Tool]:
        """通过斜杠命令获取工具
        
        Args:
            slash_command: 斜杠命令（如 '/run'）
            
        Returns:
            工具定义或 None
        """
        tool_name = self._slash_commands.get(slash_command)
        if tool_name:
            return self._tools.get(tool_name)
        return None
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """列出工具
        
        Args:
            category: 可选，按分类过滤
            
        Returns:
            工具列表
        """
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    def list_slash_commands(self) -> Dict[str, str]:
        """列出所有斜杠命令
        
        Returns:
            {slash_command: tool_name} 字典
        """
        return dict(self._slash_commands)
    
    def requires_confirmation(self, tool: Tool) -> bool:
        """检查工具是否需要确认
        
        考虑工具的确认级别和会话的自动确认状态
        
        Args:
            tool: 工具定义
            
        Returns:
            是否需要确认
        """
        if tool.confirm_level == ConfirmLevel.NONE:
            return False
        
        if tool.confirm_level == ConfirmLevel.DESTRUCTIVE:
            # 破坏性操作始终需要确认
            return True
        
        if tool.confirm_level == ConfirmLevel.NORMAL:
            # 普通确认可被 /auto on 关闭
            return not self.session.auto_confirm
        
        return False
    
    def can_call_more_tools(self) -> bool:
        """检查是否还可以调用更多工具
        
        Returns:
            是否可以继续调用工具
        """
        return self.session.tool_call_count < self.session.max_tool_calls
    
    def can_retrieve_more(self) -> bool:
        """检查是否还可以进行更多信息检索尝试
        
        Returns:
            是否可以继续检索
        """
        return self.session.retrieval_attempt_count < self.session.max_retrieval_attempts
    
    def increment_tool_call(self):
        """增加工具调用计数"""
        self.session.tool_call_count += 1
    
    def increment_retrieval_attempt(self):
        """增加信息检索尝试计数"""
        self.session.retrieval_attempt_count += 1
    
    def reset_turn_counters(self):
        """重置轮次计数器（每轮对话开始时调用）"""
        self.session.tool_call_count = 0
        self.session.retrieval_attempt_count = 0
    
    def set_auto_confirm(self, enabled: bool):
        """设置自动确认模式
        
        Args:
            enabled: 是否启用
        """
        self.session.auto_confirm = enabled
    
    def execute_plan(self, plan: ToolPlan) -> ToolResult:
        """执行工具计划
        
        Args:
            plan: 工具执行计划
            
        Returns:
            执行结果
        """
        tool = self.get_tool(plan.tool_name)
        if tool is None:
            return ToolResult(
                tool_name=plan.tool_name,
                success=False,
                error=f"未找到工具: {plan.tool_name}"
            )
        
        if not self.can_call_more_tools():
            return ToolResult(
                tool_name=plan.tool_name,
                success=False,
                error=f"已达到单轮最大工具调用次数 ({self.session.max_tool_calls})"
            )
        
        if tool.handler is None:
            return ToolResult(
                tool_name=plan.tool_name,
                success=False,
                error=f"工具 {plan.tool_name} 未实现处理函数"
            )
        
        try:
            self.increment_tool_call()
            result = tool.handler(**plan.params)
            
            if isinstance(result, ToolResult):
                return result
            elif isinstance(result, dict):
                return ToolResult(
                    tool_name=plan.tool_name,
                    success=True,
                    data=result
                )
            else:
                return ToolResult(
                    tool_name=plan.tool_name,
                    success=True,
                    message=str(result)
                )
                
        except Exception as e:
            return ToolResult(
                tool_name=plan.tool_name,
                success=False,
                error=str(e)
            )
    
    def create_plan(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        custom_confirmation: Optional[str] = None
    ) -> ToolPlan:
        """创建工具执行计划
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            custom_confirmation: 自定义确认消息
            
        Returns:
            工具执行计划
        """
        tool = self.get_tool(tool_name)
        requires_confirm = False
        confirm_msg = None
        
        if tool:
            requires_confirm = self.requires_confirmation(tool)
            if requires_confirm:
                confirm_msg = custom_confirmation or f"确定要执行 {tool.name} 吗？"
        
        return ToolPlan(
            tool_name=tool_name,
            params=params or {},
            requires_confirmation=requires_confirm,
            confirmation_message=confirm_msg
        )
