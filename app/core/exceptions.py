"""全局异常定义模块。

定义统一的异常码体系和自定义异常类。
所有异常通过 FastAPI Exception Handler 转换为统一响应格式。
"""

from enum import Enum


class ErrorCode(str, Enum):
    """统一错误码枚举。"""

    # 通用错误
    UNKNOWN = "ERR_UNKNOWN"
    VALIDATION = "ERR_VALIDATION"
    NOT_FOUND = "ERR_NOT_FOUND"
    FORBIDDEN = "ERR_FORBIDDEN"
    UNAUTHORIZED = "ERR_UNAUTHORIZED"
    RATE_LIMITED = "ERR_RATE_LIMITED"

    # 数据库错误
    DB_CONNECTION = "ERR_DB_001"
    DB_QUERY = "ERR_DB_002"
    DB_INTEGRITY = "ERR_DB_003"

    # Agent 错误
    AGENT_TIMEOUT = "ERR_AGENT_001"
    AGENT_LLM_ERROR = "ERR_AGENT_002"
    AGENT_STATE_ERROR = "ERR_AGENT_003"
    AGENT_TOOL_ERROR = "ERR_AGENT_004"

    # 规则引擎错误
    RULE_PARSE = "ERR_RULE_001"
    RULE_EXECUTION = "ERR_RULE_002"
    RULE_NOT_FOUND = "ERR_RULE_003"

    # 业务错误
    RISK_ANALYSIS_FAILED = "ERR_BIZ_001"
    DECISION_FAILED = "ERR_BIZ_002"
    DATA_QUALITY_LOW = "ERR_BIZ_003"
    HUMAN_REVIEW_REQUIRED = "ERR_BIZ_004"


class AppException(Exception):
    """应用自定义异常基类。

    属性:
        code: 错误码 (ErrorCode)
        message: 错误描述
        status_code: HTTP 状态码
        detail: 额外详情
    """

    def __init__(
        self,
        code: ErrorCode = ErrorCode.UNKNOWN,
        message: str = "服务器内部错误",
        status_code: int = 500,
        detail: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源未找到异常。"""

    def __init__(self, message: str = "资源未找到", detail: dict | None = None) -> None:
        super().__init__(code=ErrorCode.NOT_FOUND, message=message, status_code=404, detail=detail)


class ValidationException(AppException):
    """参数校验异常。"""

    def __init__(self, message: str = "参数校验失败", detail: dict | None = None) -> None:
        super().__init__(
            code=ErrorCode.VALIDATION, message=message, status_code=422, detail=detail
        )


class ForbiddenException(AppException):
    """权限不足异常。"""

    def __init__(self, message: str = "权限不足", detail: dict | None = None) -> None:
        super().__init__(code=ErrorCode.FORBIDDEN, message=message, status_code=403, detail=detail)


class AgentTimeoutException(AppException):
    """Agent 超时异常。"""

    def __init__(self, agent_name: str, timeout: int) -> None:
        super().__init__(
            code=ErrorCode.AGENT_TIMEOUT,
            message=f"Agent [{agent_name}] 执行超时 ({timeout}s)",
            status_code=504,
            detail={"agent": agent_name, "timeout": timeout},
        )


class AgentLLMException(AppException):
    """LLM 调用异常。"""

    def __init__(self, agent_name: str, error: str) -> None:
        super().__init__(
            code=ErrorCode.AGENT_LLM_ERROR,
            message=f"Agent [{agent_name}] LLM 调用失败: {error}",
            status_code=502,
            detail={"agent": agent_name, "llm_error": error},
        )


class RuleExecutionException(AppException):
    """规则执行异常。"""

    def __init__(self, rule_id: str, error: str) -> None:
        super().__init__(
            code=ErrorCode.RULE_EXECUTION,
            message=f"规则 [{rule_id}] 执行失败: {error}",
            status_code=500,
            detail={"rule_id": rule_id, "error": error},
        )


class DataQualityException(AppException):
    """数据质量过低异常。"""

    def __init__(self, score: float, issues: list[str]) -> None:
        super().__init__(
            code=ErrorCode.DATA_QUALITY_LOW,
            message=f"数据质量评分过低 ({score:.2f})，需人工介入",
            status_code=422,
            detail={"quality_score": score, "issues": issues},
        )


class HumanReviewRequiredException(AppException):
    """需要人工审核异常。"""

    def __init__(self, request_id: str, reason: str) -> None:
        super().__init__(
            code=ErrorCode.HUMAN_REVIEW_REQUIRED,
            message=f"请求 [{request_id}] 需要人工审核: {reason}",
            status_code=200,  # 非错误状态，业务正常流转
            detail={"request_id": request_id, "reason": reason},
        )