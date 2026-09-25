"""LLM Provider 抽象层。

支持多 Provider 切换：OpenAI / Anthropic / Azure OpenAI / 本地模型。
测试环境可注入 Mock LLM，避免真实 API 调用。
"""

from enum import StrEnum
from itertools import repeat
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import get_effective_llm_config, get_settings


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"


def get_llm(
    provider: LLMProvider | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    mock: bool | None = None,
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
    config = get_effective_llm_config()
    if provider is not None:
        config["provider"] = provider.value
    if temperature is not None:
        config["temperature"] = temperature
    if max_tokens is not None:
        config["max_tokens"] = max_tokens
    if mock is not None:
        config["mock_mode"] = mock
    return build_llm(config)


def build_llm(config: dict[str, Any]) -> BaseChatModel:
    """Single factory shared by real Agent calls and connection tests."""
    settings = get_settings()

    # Mock 模式
    mock = bool(config.get("mock_mode", False))
    if mock:
        # 使用无限迭代器产出确定性假回复，避免 StopIteration 崩溃
        return GenericFakeChatModel(
            messages=iter(repeat(AIMessage(content="[mock] 这是模拟 LLM 回复")))
        )

    # 确定 provider
    provider = LLMProvider(str(config["provider"]))
    temp = float(config["temperature"])
    tokens = int(config["max_tokens"])

    common_kwargs: dict[str, Any] = {
        "temperature": temp,
        "max_tokens": tokens,
        "timeout": settings.LLM_TIMEOUT,
        "max_retries": 2,
    }

    api_key = SecretStr(str(config["api_key"]))
    if provider != LLMProvider.LOCAL and not api_key.get_secret_value():
        raise ValueError("云端模型必须配置 API Key")
    model = str(config["model"])
    configured_base_url = str(config.get("base_url") or "").strip()

    if provider == LLMProvider.OPENAI:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            **({"base_url": configured_base_url} if configured_base_url else {}),
            **common_kwargs,
        )

    elif provider == LLMProvider.AZURE_OPENAI:
        from langchain_openai import AzureChatOpenAI

        if not configured_base_url:
            raise ValueError("Azure OpenAI 需要配置 LLM_BASE_URL")
        return AzureChatOpenAI(
            azure_endpoint=configured_base_url,
            azure_deployment=model,
            api_version=str(config.get("api_version") or "2024-10-21"),
            api_key=api_key,
            **common_kwargs,
        )

    elif provider == LLMProvider.LOCAL:
        # LOCAL 统一走 Ollama 的 OpenAI 兼容端点，与 model_selector 保持一致
        ollama_base = str(config["ollama_base_url"]).rstrip("/")
        base_url = configured_base_url or f"{ollama_base}/v1"
        return ChatOpenAI(
            model=model,
            api_key=SecretStr("not-needed"),
            base_url=base_url,
            **common_kwargs,
        )

    elif provider == LLMProvider.ANTHROPIC:
        try:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model,  # type: ignore[call-arg]  # langchain 1.x 存根滞后，运行时接受 model
                api_key=api_key,
                **({"base_url": configured_base_url} if configured_base_url else {}),
                **common_kwargs,
            )
        except ImportError as err:
            raise ImportError(
                "langchain-anthropic 未安装。请运行: pip install langchain-anthropic"
            ) from err

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
    config = get_effective_llm_config()
    if config["provider"] != "local" or not config["smart_routing"]:
        return get_llm(**kwargs)
    from app.core.model_selector import get_smart_llm as _smart

    return await _smart(query, **kwargs)


def get_smart_llm_sync(query: str, **kwargs) -> BaseChatModel:
    """get_smart_llm 的同步包装。

    在已有运行中的事件循环场景下（如 FastAPI 请求上下文），通过独立线程
    运行一个全新的事件循环来避免死锁；否则直接在当前线程 asyncio.run。
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 当前线程无运行中的事件循环，直接同步运行
        return asyncio.run(get_smart_llm(query, **kwargs))

    # 当前线程已有事件循环在运行，需在新线程中运行，避免阻塞/死锁
    import concurrent.futures

    def _run_in_new_loop() -> BaseChatModel:
        return asyncio.run(get_smart_llm(query, **kwargs))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_run_in_new_loop).result(timeout=30)
