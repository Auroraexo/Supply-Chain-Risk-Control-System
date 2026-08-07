"""LLM Provider 抽象层。

支持多 Provider 切换：OpenAI / Anthropic / Azure OpenAI / 本地模型。
测试环境可注入 Mock LLM，避免真实 API 调用。
"""

from enum import Enum
from functools import lru_cache
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"


@lru_cache
def get_llm(
    provider: Optional[LLMProvider] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    mock: Optional[bool] = None,
) -> BaseChatModel:
    """获取 LLM 实例（工厂方法）。

    Args:
        provider: LLM Provider，默认使用配置中的 LLM_PROVIDER
        temperature: 温度参数，默认使用配置值
        max_tokens: 最大 token 数，默认使用配置值
        mock: 是否使用 Mock 模式，默认使用配置中的 LLM_MOCK_MODE

    Returns:
        BaseChatModel 实例
    """
    settings = get_settings()

    # Mock 模式
    if mock is None:
        mock = settings.LLM_MOCK_MODE
    if mock:
        return GenericFakeChatModel(messages=iter([]))

    # 确定 provider
    provider = provider or LLMProvider(settings.LLM_PROVIDER)
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

    common_kwargs = {
        "temperature": temp,
        "max_tokens": tokens,
        "timeout": settings.LLM_TIMEOUT,
        "max_retries": 2,
    }

    if provider == LLMProvider.OPENAI:
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            **common_kwargs,
        )

    elif provider == LLMProvider.AZURE_OPENAI:
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            **common_kwargs,
        )

    elif provider == LLMProvider.LOCAL:
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key="not-needed",
            base_url=settings.LLM_BASE_URL or "http://localhost:8000/v1",
            **common_kwargs,
        )

    elif provider == LLMProvider.ANTHROPIC:
        try:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                **common_kwargs,
            )
        except ImportError:
            raise ImportError(
                "langchain-anthropic 未安装。请运行: pip install langchain-anthropic"
            )

    raise ValueError(f"不支持的 LLM Provider: {provider}")


async def get_smart_llm(query: str, **kwargs) -> BaseChatModel:
    """根据查询复杂度智能选择 Ollama 模型。

    自动检测本地 Ollama 可用模型，分析查询复杂度，
    简单查询路由到小模型，复杂查询路由到大模型。

    Args:
        query: 用户查询文本
        **kwargs: 传递给 ChatModel 的额外参数（temperature 等）

    Returns:
        BaseChatModel 实例
    """
    from app.core.model_selector import get_smart_llm as _smart
    return await _smart(query, **kwargs)


def get_smart_llm_sync(query: str, **kwargs) -> BaseChatModel:
    """get_smart_llm 的同步包装。"""
    import asyncio
    import concurrent.futures

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, get_smart_llm(query, **kwargs)
                )
                return future.result(timeout=30)
    except RuntimeError:
        pass
    return asyncio.run(get_smart_llm(query, **kwargs))