"""智能模型选择系统。

功能：
1. 检测本地 Ollama 可用模型并枚举
2. 按参数量分类为 small / large
3. 分析查询复杂度（simple / complex）
4. 路由到合适模型（简单→小模型，复杂→大模型）
5. 记录选择决策和性能指标

使用方式：
    from app.core.model_selector import get_smart_llm, select_model_for_query

    # 方式 1：直接获取适合查询的 LLM 实例
    llm = await get_smart_llm("解释多 Agent 系统的架构")

    # 方式 2：先选择模型再获取
    decision = await select_model_for_query("你好")
    llm = decision.to_chat_model()
"""

import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

import httpx
import structlog

from app.core.config import get_settings

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────
# 枚举与数据模型
# ──────────────────────────────────────────────

class ModelCategory(str, Enum):
    SMALL = "small"
    LARGE = "large"


class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


@dataclass
class ModelInfo:
    name: str
    size_bytes: int
    parameter_count: float
    category: ModelCategory
    quantization: Optional[str] = None
    family: Optional[str] = None

    def to_chat_model(self, **kwargs) -> "BaseChatModel":
        from langchain_openai import ChatOpenAI

        settings = get_settings()
        return ChatOpenAI(
            model=self.name,
            api_key="not-needed",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            temperature=kwargs.get("temperature", settings.LLM_TEMPERATURE),
            max_tokens=kwargs.get("max_tokens", settings.LLM_MAX_TOKENS),
            timeout=kwargs.get("timeout", settings.LLM_TIMEOUT),
            max_retries=2,
        )


@dataclass
class ComplexityScore:
    score: float
    level: QueryComplexity
    factors: dict = field(default_factory=dict)


@dataclass
class SelectionDecision:
    query_preview: str
    complexity: ComplexityScore
    selected_model: ModelInfo
    candidate_count: int
    reason: str
    timestamp: str
    elapsed_ms: float

    def to_chat_model(self, **kwargs) -> "BaseChatModel":
        return self.selected_model.to_chat_model(**kwargs)


# ──────────────────────────────────────────────
# Ollama 模型检测器
# ──────────────────────────────────────────────

class OllamaModelDetector:
    """检测本地 Ollama 可用模型。"""

    def __init__(self, base_url: str, cache_ttl: int = 300):
        self.base_url = base_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self._cache: Optional[list[ModelInfo]] = None
        self._cache_time: float = 0.0
        self._lock = threading.Lock()

    async def list_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        if not force_refresh and self._cache and (time.time() - self._cache_time) < self.cache_ttl:
            return self._cache

        # 加锁避免 TTL 过期时并发请求同时触发 fetch
        with self._lock:
            if not force_refresh and self._cache and (time.time() - self._cache_time) < self.cache_ttl:
                return self._cache

            try:
                models = await self._fetch_models()
                self._cache = models
                self._cache_time = time.time()
                logger.info(
                    "model_detector.models_detected",
                    count=len(models),
                    small=[m.name for m in models if m.category == ModelCategory.SMALL],
                    large=[m.name for m in models if m.category == ModelCategory.LARGE],
                )
                return models
            except httpx.ConnectError:
                logger.warning("model_detector.ollama_unreachable", base_url=self.base_url)
                return []
            except Exception as e:
                logger.error("model_detector.fetch_failed", error=str(e), exc_info=True)
                return []

    async def _fetch_models(self) -> list[ModelInfo]:
        settings = get_settings()
        threshold = settings.MODEL_SELECTOR_SMALL_THRESHOLD

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()

        models: list[ModelInfo] = []
        for item in data.get("models", []):
            name = item.get("name", item.get("model", ""))
            size_bytes = item.get("size", 0)
            details = item.get("details", {})

            param_count = self._parse_param_size(details.get("parameter_size", ""))
            if param_count == 0:
                param_count = self._parse_param_from_name(name)
            if param_count == 0 and size_bytes > 0:
                param_count = round(size_bytes / 0.6 / 1e9, 1)

            category = ModelCategory.SMALL if param_count < threshold else ModelCategory.LARGE

            models.append(ModelInfo(
                name=name,
                size_bytes=size_bytes,
                parameter_count=param_count,
                category=category,
                quantization=details.get("quantization_level"),
                family=details.get("family"),
            ))

        models.sort(key=lambda m: m.parameter_count)
        return models

    @staticmethod
    def _parse_param_size(size_str: str) -> float:
        if not size_str:
            return 0.0
        cleaned = size_str.strip().upper().replace("B", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_param_from_name(name: str) -> float:
        match = re.search(r":(\d+(?:\.\d+)?)b", name.lower())
        if match:
            return float(match.group(1))
        match = re.search(r"(\d+(?:\.\d+)?)b$", name.lower())
        if match:
            return float(match.group(1))
        return 0.0

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


# ──────────────────────────────────────────────
# 查询复杂度分析器
# ──────────────────────────────────────────────

class QueryComplexityAnalyzer:
    """基于多因子的查询复杂度分析。"""

    COMPLEX_KEYWORDS_ZH = [
        "分析", "比较", "对比", "设计", "实现", "解释", "为什么",
        "如何", "架构", "优化", "重构", "评估", "推导", "证明",
        "调试", "排查", "诊断", "预测", "规划", "策略", "审查",
    ]
    COMPLEX_KEYWORDS_EN = [
        "analyze", "compare", "design", "implement", "explain",
        "why", "how", "architecture", "optimize", "refactor",
        "evaluate", "derive", "prove", "debug", "diagnose",
        "predict", "strategy", "plan", "review",
    ]
    TECHNICAL_INDICATORS = [
        "```", "def ", "class ", "function ", "import ",
        "SELECT", "WHERE", "API", "HTTP", "SQL", "Agent",
        "算法", "复杂度", "并发", "异步", "分布式", "事务",
    ]

    def analyze(self, query: str) -> ComplexityScore:
        if not query or not query.strip():
            return ComplexityScore(score=0.0, level=QueryComplexity.SIMPLE, factors={"empty": True})

        scores: dict[str, float] = {}
        meta: dict = {}

        # 因子 1：长度 (0 ~ 0.3)
        length = len(query)
        if length < 15:
            scores["length"] = 0.0
        elif length < 40:
            scores["length"] = 0.1
        elif length < 80:
            scores["length"] = 0.2
        else:
            scores["length"] = 0.3
        meta["char_count"] = length

        # 因子 2：复杂关键词 (0 ~ 0.3，每个 0.1)
        query_lower = query.lower()
        matched = []
        for kw in self.COMPLEX_KEYWORDS_ZH + self.COMPLEX_KEYWORDS_EN:
            if kw in query or kw in query_lower:
                matched.append(kw)
        scores["keywords"] = min(0.3, len(matched) * 0.1)
        meta["matched_keywords"] = matched

        # 因子 3：结构复杂度 (0 ~ 0.2)
        sentence_count = query.count("。") + query.count(".") + query.count("；") + query.count(";")
        question_count = query.count("？") + query.count("?")
        structure = 0.0
        if sentence_count > 1:
            structure += 0.1
        if question_count > 1:
            structure += 0.1
        scores["structure"] = structure
        meta["sentence_count"] = sentence_count
        meta["question_count"] = question_count

        # 因子 4：技术指标 (0 ~ 0.2)
        tech_count = sum(1 for ind in self.TECHNICAL_INDICATORS if ind in query or ind in query_lower)
        scores["technical"] = min(0.2, tech_count * 0.1)
        meta["tech_indicators"] = tech_count

        total = min(1.0, sum(scores.values()))
        threshold = get_settings().MODEL_SELECTOR_COMPLEXITY_THRESHOLD
        level = QueryComplexity.COMPLEX if total >= threshold else QueryComplexity.SIMPLE

        return ComplexityScore(
            score=round(total, 3),
            level=level,
            factors={**scores, **meta},
        )


# ──────────────────────────────────────────────
# 性能追踪器
# ──────────────────────────────────────────────

class ModelPerformanceTracker:
    """追踪模型选择决策和性能指标。"""

    def __init__(self):
        self._stats: dict[str, dict] = {}
        self._lock = threading.Lock()

    def record_selection(self, model_name: str, complexity: str, elapsed_ms: float) -> None:
        with self._lock:
            if model_name not in self._stats:
                self._stats[model_name] = {
                    "count": 0,
                    "total_latency_ms": 0.0,
                    "simple_count": 0,
                    "complex_count": 0,
                }
            s = self._stats[model_name]
            s["count"] += 1
            s["total_latency_ms"] += elapsed_ms
            if complexity == QueryComplexity.SIMPLE.value:
                s["simple_count"] += 1
            else:
                s["complex_count"] += 1

    def get_stats(self) -> dict:
        with self._lock:
            result = {}
            for name, s in self._stats.items():
                avg = s["total_latency_ms"] / s["count"] if s["count"] > 0 else 0
                result[name] = {
                    "count": s["count"],
                    "avg_latency_ms": round(avg, 1),
                    "simple_count": s["simple_count"],
                    "complex_count": s["complex_count"],
                }
            return result


# ──────────────────────────────────────────────
# 模型路由器
# ──────────────────────────────────────────────

class ModelRouter:
    """根据查询复杂度路由到合适的模型。"""

    def __init__(self):
        settings = get_settings()
        self.detector = OllamaModelDetector(
            base_url=settings.OLLAMA_BASE_URL,
            cache_ttl=settings.MODEL_SELECTOR_CACHE_TTL,
        )
        self.analyzer = QueryComplexityAnalyzer()
        self.tracker = ModelPerformanceTracker()
        self._preferred_small = settings.MODEL_SELECTOR_PREFERRED_SMALL
        self._preferred_large = settings.MODEL_SELECTOR_PREFERRED_LARGE

    async def select(self, query: str) -> SelectionDecision:
        t0 = time.monotonic()
        complexity = self.analyzer.analyze(query)
        models = await self.detector.list_models()

        if not models:
            raise RuntimeError("无可用 Ollama 模型，请确认 Ollama 服务已启动")

        target_category = (
            ModelCategory.SMALL if complexity.level == QueryComplexity.SIMPLE
            else ModelCategory.LARGE
        )

        candidates = [m for m in models if m.category == target_category]

        if not candidates:
            # 目标类别无可用模型 → 使用另一类别中最接近的
            other = [m for m in models if m.category != target_category]
            if target_category == ModelCategory.SMALL:
                # 想要小模型但没有 → 取最小的大模型
                candidates = sorted(other, key=lambda m: m.parameter_count)
                reason = "无小模型可用，降级使用最小大模型"
            else:
                # 想要大模型但没有 → 取最大的小模型
                candidates = sorted(other, key=lambda m: m.parameter_count, reverse=True)
                reason = "无大模型可用，升级使用最大小模型"
        else:
            preferred = self._preferred_small if target_category == ModelCategory.SMALL else self._preferred_large
            if preferred:
                pref_match = [m for m in candidates if m.name == preferred]
                if pref_match:
                    candidates = pref_match
                    reason = f"命中首选{target_category.value}模型: {preferred}"
                else:
                    if target_category == ModelCategory.SMALL:
                        candidates = sorted(candidates, key=lambda m: m.parameter_count)
                    else:
                        candidates = sorted(candidates, key=lambda m: m.parameter_count, reverse=True)
                    reason = f"首选模型 {preferred} 未安装，使用{target_category.value}类别中最优"
            else:
                if target_category == ModelCategory.SMALL:
                    candidates = sorted(candidates, key=lambda m: m.parameter_count)
                    reason = "简单查询→选择最小小模型"
                else:
                    candidates = sorted(candidates, key=lambda m: m.parameter_count, reverse=True)
                    reason = "复杂查询→选择最大大模型"

        selected = candidates[0]
        elapsed = round((time.monotonic() - t0) * 1000, 1)

        self.tracker.record_selection(
            model_name=selected.name,
            complexity=complexity.level.value,
            elapsed_ms=elapsed,
        )

        preview = query[:80].replace("\n", " ") + ("..." if len(query) > 80 else "")
        decision = SelectionDecision(
            query_preview=preview,
            complexity=complexity,
            selected_model=selected,
            candidate_count=len(models),
            reason=reason,
            timestamp=datetime.now().isoformat(),
            elapsed_ms=elapsed,
        )

        logger.info(
            "model_router.selected",
            query_preview=preview,
            complexity_score=complexity.score,
            complexity_level=complexity.level.value,
            selected_model=selected.name,
            model_category=selected.category.value,
            param_count=selected.parameter_count,
            candidate_count=len(models),
            reason=reason,
            elapsed_ms=elapsed,
        )

        return decision


# ──────────────────────────────────────────────
# 单例 & 便捷函数
# ──────────────────────────────────────────────

_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


async def select_model_for_query(query: str) -> SelectionDecision:
    """分析查询复杂度并选择合适的 Ollama 模型。"""
    router = get_model_router()
    return await router.select(query)


async def get_smart_llm(query: str, **kwargs) -> "BaseChatModel":
    """根据查询复杂度智能选择 LLM 实例。"""
    decision = await select_model_for_query(query)
    return decision.to_chat_model(**kwargs)


def get_performance_stats() -> dict:
    """获取模型选择性能统计。"""
    return get_model_router().tracker.get_stats()