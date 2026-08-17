"""Prompt 加载器。支持文件/DB 双源，热更新。"""
import structlog
import yaml
from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent / "prompts"

logger = structlog.get_logger(__name__)

# Prompt 必备字段，缺失时给出明确告警
REQUIRED_KEYS = ("system_prompt", "description")


class PromptLoader:
    """Prompt 加载器。"""

    def __init__(self, source: str = "file"):
        self._cache: dict[str, dict] = {}
        self._source = source

    async def get_prompt(self, agent_name: str, version: str = "v1") -> dict:
        """获取 Prompt 内容。

        Args:
            agent_name: Agent 名称 (scout/analyst/decider/reflection)
            version: 版本号 (v1/v2/...)

        Returns:
            包含 system_prompt 和 description 的字典
        """
        cache_key = f"{agent_name}:{version}"
        if cache_key not in self._cache:
            self._cache[cache_key] = await self._load_from_file(agent_name, version)
        return self._cache[cache_key]

    async def _load_from_file(self, agent_name: str, version: str) -> dict:
        """从 YAML 文件加载 Prompt，并做字段校验。"""
        file_path = PROMPTS_DIR / f"{agent_name}_{version}.yaml"
        if not file_path.exists():
            logger.warning(
                "prompt_loader.file_not_found",
                agent_name=agent_name,
                version=version,
            )
            return {"system_prompt": f"Agent: {agent_name}", "description": ""}

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        missing = [k for k in REQUIRED_KEYS if not data.get(k)]
        if missing:
            logger.warning(
                "prompt_loader.missing_required_fields",
                agent_name=agent_name,
                version=version,
                missing_fields=missing,
            )
            data.setdefault("system_prompt", f"Agent: {agent_name}")
            data.setdefault("description", "")

        if not data.get("system_prompt", "").strip():
            logger.warning(
                "prompt_loader.empty_system_prompt",
                agent_name=agent_name,
                version=version,
            )
        return data

    async def refresh(self) -> None:
        """热更新：清空缓存。"""
        self._cache.clear()


# 全局单例
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """获取全局 Prompt 加载器单例。"""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader