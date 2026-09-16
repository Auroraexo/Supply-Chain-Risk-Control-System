"""Prometheus 指标模块。

集中定义所有业务指标，避免多处定义同一指标导致重复注册。
蓝图告警规则对应：
- Agent 超时率 > 5% （由 agent_errors_total / agent_calls_total 计算）
- 决策置信度 < 0.6 （由 decision_confidence 指标暴露）
"""

from prometheus_client import Counter, Gauge, Histogram

# === HTTP API 指标 ===
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# === Agent 指标 ===
AGENT_CALLS_TOTAL = Counter(
    "agent_calls_total",
    "Agent 调用总数",
    ["agent_name", "node_name", "status"],
)

AGENT_LATENCY_SECONDS = Histogram(
    "agent_latency_seconds",
    "Agent 节点执行耗时",
    ["agent_name", "node_name"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

AGENT_TOKENS_TOTAL = Counter(
    "agent_tokens_total",
    "Agent Token 消耗总数",
    ["agent_name", "token_type"],
)

LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "LLM 调用总数",
    ["provider", "model", "status"],
)

# === 决策指标 ===
DECISION_CONFIDENCE = Gauge(
    "decision_confidence",
    "最近一次决策的置信度",
    ["decision_type"],
)

DECISIONS_TOTAL = Counter(
    "decisions_total",
    "决策总数",
    ["decision_type", "risk_level"],
)


def record_llm_usage(agent_name: str, llm, resp, logger=None) -> None:
    """记录单次 LLM 调用的 token 用量与调用计数。

    供各 Agent 节点在 llm.ainvoke 后调用；指标采集失败不影响业务。
    """
    try:
        usage = getattr(resp, "usage_metadata", None) or {}
        prompt_tokens = usage.get("input_tokens") or 0
        completion_tokens = usage.get("output_tokens") or 0
        if prompt_tokens:
            AGENT_TOKENS_TOTAL.labels(agent_name=agent_name, token_type="prompt").inc(prompt_tokens)
        if completion_tokens:
            AGENT_TOKENS_TOTAL.labels(agent_name=agent_name, token_type="completion").inc(completion_tokens)
        model = getattr(llm, "model_name", None) or getattr(llm, "model", "") or "unknown"
        LLM_CALLS_TOTAL.labels(provider="default", model=str(model), status="success").inc()
    except Exception:
        if logger:
            logger.debug("metrics.llm_usage_record_failed", agent=agent_name)
