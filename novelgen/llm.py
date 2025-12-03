"""
LLM实例管理
统一管理LLM实例的创建
"""
import time
import json
from typing import Any, Dict, List, Type, TypeVar
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
from novelgen.config import LLMConfig

T = TypeVar("T", bound=BaseModel)


class VerboseCallbackHandler(BaseCallbackHandler):
    """
    详细日志回调处理器
    
    支持流式输出 LLM 响应内容到控制台和/或日志文件。
    
    Args:
        stream_to_file: 可选的日志文件路径，如果提供则同时写入文件
        show_streaming: 是否实时显示流式输出（默认 True）
        show_prompt: 是否显示完整的提示词（默认 True）
    """
    
    def __init__(self, stream_to_file: str = None, show_streaming: bool = True, show_prompt: bool = True):
        self.start_time = None
        self.end_time = None
        self.prompts = []
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        # 新增：存储完整响应内容
        self.response_content = ""
        # 新增：是否实时显示流式输出
        self.show_streaming = show_streaming
        # 新增：是否显示提示词
        self.show_prompt = show_prompt
        # 新增：可选输出到文件
        self.stream_file_path = stream_to_file
        self.stream_file = None
        if stream_to_file:
            try:
                self.stream_file = open(stream_to_file, 'a', encoding='utf-8')
            except Exception as e:
                print(f"⚠️ 无法打开日志文件 {stream_to_file}: {e}")
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """LLM开始调用时"""
        self.start_time = time.time()
        self.prompts = prompts
        self.response_content = ""  # 重置响应内容
        
        print("\n" + "="*80)
        print("🤖 LLM调用开始")
        print("="*80)
        
        if self.show_prompt:
            print("\n📝 完整提示词：")
            print("-"*80)
            for i, prompt in enumerate(prompts, 1):
                print(f"\n[提示词 {i}]")
                print(prompt)
                print("-"*80)
        
        if self.show_streaming:
            print("\n📤 LLM 响应（流式输出）：")
            print("-"*80)
    
    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs) -> None:
        """聊天模型开始调用时"""
        self.start_time = time.time()
        self.response_content = ""  # 重置响应内容
        
        print("\n" + "="*80)
        print("🤖 LLM调用开始")
        print("="*80)
        
        if self.show_prompt:
            print("\n📝 完整提示词：")
            print("-"*80)
            
            for i, message_list in enumerate(messages, 1):
                print(f"\n[对话 {i}]")
                for msg in message_list:
                    role = msg.__class__.__name__.replace("Message", "")
                    content = msg.content
                    print(f"\n[{role}]")
                    print(content)
                print("-"*80)
        
        if self.show_streaming:
            print("\n📤 LLM 响应（流式输出）：")
            print("-"*80)
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """流式输出每个 token"""
        self.response_content += token
        # 实时输出到控制台
        if self.show_streaming:
            print(token, end="", flush=True)
        # 可选：写入日志文件
        if self.stream_file:
            try:
                self.stream_file.write(token)
                self.stream_file.flush()
            except Exception:
                pass  # 忽略写入错误
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """LLM调用结束时"""
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time if self.start_time else 0
        
        # 提取token使用情况
        if response.llm_output and 'token_usage' in response.llm_output:
            token_usage = response.llm_output['token_usage']
            self.total_tokens = token_usage.get('total_tokens', 0)
            self.prompt_tokens = token_usage.get('prompt_tokens', 0)
            self.completion_tokens = token_usage.get('completion_tokens', 0)
        
        # 如果没有流式输出（response_content 为空），从 response 中提取内容
        if not self.response_content and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, 'text'):
                        self.response_content += gen.text
                    elif hasattr(gen, 'message') and hasattr(gen.message, 'content'):
                        self.response_content += gen.message.content
        
        if self.show_streaming:
            print("\n" + "-"*80)
        
        print("\n" + "="*80)
        print("✅ LLM调用完成")
        print("="*80)
        print(f"\n⏱️  响应时间: {elapsed_time:.2f} 秒")
        print(f"\n🎯 Token使用情况:")
        print(f"  • 提示词Token: {self.prompt_tokens}")
        print(f"  • 生成Token: {self.completion_tokens}")
        print(f"  • 总计Token: {self.total_tokens}")
        
        # 显示完整响应内容（方便调试 JSON 解析问题）
        if self.response_content and not self.show_streaming:
            # 只有在非流式模式下才显示完整响应（流式模式已经显示过了）
            print(f"\n📄 完整响应内容：")
            print("-"*80)
            print(self.response_content)
            print("-"*80)
        
        print("\n" + "="*80 + "\n")
        
        # 写入分隔符到日志文件
        if self.stream_file:
            try:
                self.stream_file.write(f"\n{'='*80}\n")
                self.stream_file.write(f"响应时间: {elapsed_time:.2f}s, Tokens: {self.total_tokens}\n")
                self.stream_file.write(f"{'='*80}\n\n")
                self.stream_file.flush()
            except Exception:
                pass
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """LLM调用出错时"""
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time if self.start_time else 0
        
        print("\n" + "="*80)
        print("❌ LLM调用出错")
        print("="*80)
        print(f"\n⏱️  已耗时: {elapsed_time:.2f} 秒")
        print(f"\n❗ 错误信息: {error}")
        
        # 如果有部分响应内容，也显示出来帮助调试
        if self.response_content:
            print(f"\n📄 已接收的部分响应：")
            print("-"*80)
            print(self.response_content)
            print("-"*80)
        
        print("\n" + "="*80 + "\n")
        
        # 写入错误信息到日志文件
        if self.stream_file:
            try:
                self.stream_file.write(f"\n{'='*80}\n")
                self.stream_file.write(f"❌ 错误: {error}\n")
                self.stream_file.write(f"{'='*80}\n\n")
                self.stream_file.flush()
            except Exception:
                pass
    
    def __del__(self):
        """清理文件句柄"""
        if self.stream_file:
            try:
                self.stream_file.close()
            except Exception:
                pass


def get_llm(
    config: LLMConfig = None, 
    verbose: bool = False, 
    stream_to_file: str = None,
    show_streaming: bool = True,
    show_prompt: bool = True
):
    """
    获取LLM实例
    
    Args:
        config: LLM配置，如果为None则使用默认配置
        verbose: 是否启用详细日志输出（同时启用流式输出）
        stream_to_file: 可选的日志文件路径，将 LLM 响应写入文件
        show_streaming: 是否在控制台实时显示流式输出（默认 True）
        show_prompt: 是否在 verbose 模式下显示完整提示词（默认 True）
        
    Returns:
        ChatOpenAI实例
    """
    if config is None:
        config = LLMConfig()
    
    callbacks = []
    if verbose:
        callbacks.append(VerboseCallbackHandler(
            stream_to_file=stream_to_file,
            show_streaming=show_streaming,
            show_prompt=show_prompt
        ))
    
    extra_body = None
    # 为阿里云ModelScope的所有Qwen模型设置enable_thinking=False
    if config.base_url and "api-inference.modelscope.cn" in config.base_url:
        import re
        # 匹配所有Qwen系列模型
        qwen_patterns = [
            r"qwen.*",  # 通用qwen模型
            r"Qwen.*",  # 大写开头的Qwen模型
            r"Qwen3-\d+B",  # 原有的Qwen3模型
        ]
        if any(re.search(pattern, config.model_name or "", re.IGNORECASE) for pattern in qwen_patterns):
            extra_body = {"enable_thinking": False}
    
    return ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        api_key=config.api_key,
        base_url=config.base_url,
        callbacks=callbacks if callbacks else None,
        extra_body=extra_body,
        streaming=verbose  # 当 verbose=True 时启用流式传输
    )


def get_structured_llm(
    pydantic_model: Type[T], 
    config: LLMConfig = None, 
    verbose: bool = False,
    stream_to_file: str = None,
    show_streaming: bool = True,
    show_prompt: bool = True
):
    """
    获取支持结构化输出的LLM实例
    
    Args:
        pydantic_model: Pydantic模型类，用于定义输出结构
        config: LLM配置，如果为None则使用默认配置
        verbose: 是否启用详细日志输出（同时启用流式输出）
        stream_to_file: 可选的日志文件路径，将 LLM 响应写入文件
        show_streaming: 是否在控制台实时显示流式输出（默认 True）
        show_prompt: 是否在 verbose 模式下显示完整提示词（默认 True）
        
    Returns:
        配置了 with_structured_output 的 ChatOpenAI 实例
        
    Note:
        - 如果 config.use_structured_output 为 False，则返回普通 LLM 实例（不使用 structured_output）
        - 如果后端不支持 structured_output（如部分兼容端点），应在调用侧捕获异常并退回到传统解析路径
    """
    if config is None:
        config = LLMConfig()
    
    # 如果配置明确禁用 structured_output，返回普通 LLM
    if not config.use_structured_output:
        return get_llm(
            config=config, 
            verbose=verbose,
            stream_to_file=stream_to_file,
            show_streaming=show_streaming,
            show_prompt=show_prompt
        )
    
    # 创建基础 LLM 实例
    base_llm = get_llm(
        config=config, 
        verbose=verbose,
        stream_to_file=stream_to_file,
        show_streaming=show_streaming,
        show_prompt=show_prompt
    )
    
    # 使用 with_structured_output 包装
    try:
        return base_llm.with_structured_output(pydantic_model)
    except Exception as e:
        # 如果 with_structured_output 不被支持，打印警告并返回普通 LLM
        print(f"⚠️  警告: 当前后端不支持 structured_output，将使用传统解析路径。错误: {e}")
        return base_llm

