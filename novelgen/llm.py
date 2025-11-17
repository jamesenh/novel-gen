"""
LLM实例管理
统一管理LLM实例的创建
"""
import time
import json
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
from novelgen.config import LLMConfig


class VerboseCallbackHandler(BaseCallbackHandler):
    """详细日志回调处理器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.prompts = []
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """LLM开始调用时"""
        self.start_time = time.time()
        self.prompts = prompts
        
        print("\n" + "="*80)
        print("🤖 LLM调用开始")
        print("="*80)
        print("\n📝 完整提示词：")
        print("-"*80)
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[提示词 {i}]")
            print(prompt)
            print("-"*80)
    
    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs) -> None:
        """聊天模型开始调用时"""
        self.start_time = time.time()
        
        print("\n" + "="*80)
        print("🤖 LLM调用开始")
        print("="*80)
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
    
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """LLM调用结束时"""
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time
        
        # 提取token使用情况
        if response.llm_output and 'token_usage' in response.llm_output:
            token_usage = response.llm_output['token_usage']
            self.total_tokens = token_usage.get('total_tokens', 0)
            self.prompt_tokens = token_usage.get('prompt_tokens', 0)
            self.completion_tokens = token_usage.get('completion_tokens', 0)
        
        print("\n" + "="*80)
        print("✅ LLM调用完成")
        print("="*80)
        print(f"\n⏱️  响应时间: {elapsed_time:.2f} 秒")
        print(f"\n🎯 Token使用情况:")
        print(f"  • 提示词Token: {self.prompt_tokens}")
        print(f"  • 生成Token: {self.completion_tokens}")
        print(f"  • 总计Token: {self.total_tokens}")
        print("\n" + "="*80 + "\n")
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """LLM调用出错时"""
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time if self.start_time else 0
        
        print("\n" + "="*80)
        print("❌ LLM调用出错")
        print("="*80)
        print(f"\n⏱️  已耗时: {elapsed_time:.2f} 秒")
        print(f"\n❗ 错误信息: {error}")
        print("\n" + "="*80 + "\n")


def get_llm(config: LLMConfig = None, verbose: bool = False):
    """
    获取LLM实例
    
    Args:
        config: LLM配置，如果为None则使用默认配置
        verbose: 是否启用详细日志输出
        
    Returns:
        ChatOpenAI实例
    """
    if config is None:
        config = LLMConfig()
    
    callbacks = []
    if verbose:
        callbacks.append(VerboseCallbackHandler())
    
    extra_body = None
    if config.base_url and "api-inference.modelscope.cn" in config.base_url and "Qwen3-32B" in config.model_name:
        extra_body = {"enable_thinking": False}
    
    return ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        api_key=config.api_key,
        base_url=config.base_url,
        callbacks=callbacks if callbacks else None,
        extra_body=extra_body
    )

