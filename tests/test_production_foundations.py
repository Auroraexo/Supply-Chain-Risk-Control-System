"""Offline regression tests: real SQL persistence, mocked external transports."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.settings import public_config, resolve_key, rollback_llm
from app.api.v1.settings import test_llm_connection as infer_test
from app.api.v1.treatment import update_treatment
from app.core.config import Settings, get_effective_llm_config, request_llm_config
from app.models import (
    AnalysisResult,
    AuditEvent,
    Base,
    Decision,
    DecisionResult,
    RawData,
    User,
    UserRole,
)
from app.models.system_setting import SystemSetting
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.settings import LLMConfigRequest, LLMTestRequest, NotificationChannel
from app.schemas.treatment import TreatmentUpdate
from app.services.decision_service import DecisionService
from app.services.settings_service import SettingsService


class AsyncBridge:
    """Exercise production SQL against SQLite, without an additional async driver."""

    def __init__(self, session):
        self.session = session

    def add(self, row):
        self.session.add(row)

    async def get(self, model, identifier):
        return self.session.get(model, identifier)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def flush(self):
        self.session.flush()

    async def refresh(self, row):
        self.session.refresh(row)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield AsyncBridge(session)
    engine.dispose()


@pytest.fixture
def cipher(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        "app.services.settings_service.get_settings",
        lambda: SimpleNamespace(SETTINGS_ENCRYPTION_KEY=key),
    )
    return key


@pytest.mark.parametrize("role", ["admin", "decider", "invalid", None])
def test_public_registration_cannot_choose_privileged_role(role):
    with pytest.raises(ValidationError):
        RegisterRequest(
            username="tester", email="tester@example.com", password="strong-password", role=role
        )


def test_public_registration_defaults_to_analyst():
    assert (
        RegisterRequest(
            username="tester", email="tester@example.com", password="strong-password"
        ).role
        == "analyst"
    )


@pytest.mark.parametrize("value", ["", "change-me-to-a-random-secret-key", "short"])
def test_production_rejects_insecure_jwt(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="production", JWT_SECRET_KEY=value)


def production_config():
    return {
        "_env_file": None,
        "ENVIRONMENT": "production",
        "JWT_SECRET_KEY": "a" * 48,
        "DATABASE_URL": "mysql+asyncmy://app:strong-secret@localhost/db",
        "RABBITMQ_URL": "amqp://app:strong-secret@localhost/",
        "SETTINGS_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "DEBUG": False,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"DATABASE_URL": "mysql+asyncmy://root:password@localhost/db"},
        {"DEBUG": True},
        {"RABBITMQ_URL": "amqp://guest:guest@localhost/"},
        {"SETTINGS_ENCRYPTION_KEY": "bad"},
    ],
)
def test_production_rejects_unsafe_dependencies(change):
    with pytest.raises(ValidationError):
        Settings(**{**production_config(), **change})


def test_production_accepts_explicit_secrets():
    assert Settings(**production_config()).is_production


@pytest.mark.parametrize("provider", ["typo", "deepseek", ""])
def test_unknown_provider_is_not_reported_as_success(provider):
    with pytest.raises(ValidationError):
        LLMTestRequest(provider=provider)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:pass@host/v1",
        "https://host?key=secret",
        "javascript:bad",
    ],
)
def test_model_urls_reject_non_http_or_embedded_credentials(url):
    with pytest.raises(ValidationError):
        LLMConfigRequest(base_url=url)


def test_azure_requires_resource_url():
    with pytest.raises(ValidationError):
        LLMConfigRequest(provider="azure_openai")


def test_blank_model_rejected():
    with pytest.raises(ValidationError):
        LLMConfigRequest(model="   ")


def test_masked_key_cannot_be_reused_across_providers():
    with pytest.raises(HTTPException) as error:
        resolve_key(
            {"provider": "anthropic", "api_key": "••••••••"},
            {"provider": "openai", "api_key": "secret"},
        )
    assert error.value.status_code == 422


def test_public_config_never_exposes_secret():
    cfg = LLMConfigRequest(api_key="secret-value").model_dump(exclude={"version"})
    assert "secret-value" not in json.dumps(public_config(cfg, 1))


async def test_missing_encryption_key_does_not_block_read_of_environment_defaults(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.settings_service.get_settings",
        lambda: SimpleNamespace(SETTINGS_ENCRYPTION_KEY=""),
    )
    assert await SettingsService(db).read("llm") == (None, 0)


async def test_settings_are_encrypted_versioned_and_survive_new_session(db, cipher):
    service = SettingsService(db)
    assert await service.read("llm") == (None, 0)
    assert await service.write("llm", {"api_key": "private-key"}, "admin", 0) == 1
    await db.commit()
    row = db.session.get(SystemSetting, "llm")
    assert "private-key" not in row.encrypted_value
    db.session.expunge_all()
    assert await SettingsService(db).read("llm") == ({"api_key": "private-key"}, 1)
    assert (await service.history("llm"))[0]["updated_by"] == "admin"
    assert await service.write("llm", {"api_key": "new-key"}, "other-admin", 1) == 2
    await db.commit()
    with pytest.raises(HTTPException) as error:
        await service.write("llm", {}, "stale", 1)
    assert error.value.status_code == 409
    assert len((await db.execute(select(AuditEvent))).scalars().all()) == 2


async def test_concurrent_initial_settings_write_conflicts(db, cipher):
    await SettingsService(db).write("llm", {}, "admin", 0)
    await db.commit()
    with pytest.raises(HTTPException) as error:
        await SettingsService(db).write("llm", {}, "second", 0)
    assert error.value.status_code == 409


async def test_missing_encryption_key_fails_without_storing_plaintext(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.settings_service.get_settings",
        lambda: SimpleNamespace(SETTINGS_ENCRYPTION_KEY=""),
    )
    with pytest.raises(HTTPException) as error:
        await SettingsService(db).write("llm", {"api_key": "secret"}, "admin", 0)
    assert error.value.status_code == 503


async def test_configuration_rollback_creates_new_revision(db, cipher):
    service = SettingsService(db)
    cfg = LLMConfigRequest(provider="local", model="original").model_dump(exclude={"version"})
    await service.write("llm", cfg, "admin", 0)
    await db.commit()
    await service.write("llm", {**cfg, "model": "other"}, "admin", 1)
    await db.commit()
    result = await rollback_llm(
        1, LLMConfigRequest(provider="local", version=2), db, {"sub": "admin"}
    )
    assert result.data["model"] == "original"
    assert result.data["version"] == 3


async def test_model_test_performs_inference_even_when_mock_requested(db, monkeypatch):
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="OK")))
    captured = []
    monkeypatch.setattr("app.core.llm.build_llm", lambda cfg: captured.append(cfg) or model)
    result = await infer_test(
        LLMTestRequest(provider="openai", model="selected-model", api_key="key", mock_mode=True),
        db,
        {"sub": "admin"},
    )
    assert result.data["success"]
    model.ainvoke.assert_awaited_once()
    assert captured[0]["model"] == "selected-model"
    assert captured[0]["mock_mode"] is False


async def test_model_error_message_is_sanitized(db, monkeypatch):
    model = SimpleNamespace(ainvoke=AsyncMock(side_effect=Exception("provider echoed secret-key")))
    monkeypatch.setattr("app.core.llm.build_llm", lambda cfg: model)
    result = await infer_test(LLMTestRequest(api_key="secret-key"), db, {"sub": "admin"})
    assert result.data["success"] is False
    assert "secret-key" not in json.dumps(result.data)


def seed_decision(db):
    db.add(
        User(
            id="owner",
            username="owner",
            email="owner@example.com",
            hashed_password="not-a-real-password",
            role=UserRole.DECIDER,
        )
    )
    db.add(
        RawData(
            id="raw", source_type="test", source_id="s", payload={"delay_days": 3}, data_hash="hash"
        )
    )
    db.session.flush()
    db.add(AnalysisResult(id="analysis", raw_data_id="raw", request_id="request"))
    db.session.flush()
    db.add(
        DecisionResult(
            id="decision",
            request_id="request",
            analysis_id="analysis",
            decision=Decision.PENDING_REVIEW,
            confidence=0.62,
        )
    )
    db.session.commit()
    return db.session.get(DecisionResult, "decision")


async def test_review_preserves_model_confidence_and_audits_comment(db):
    seed_decision(db)
    result = await DecisionService(db).submit_review(
        "decision", "approve", "reviewer", "checked evidence"
    )
    assert result["decision"] == "approve"
    decision = db.session.get(DecisionResult, "decision")
    assert decision.confidence == 0.62
    assert decision.revision == 1
    event = (await db.execute(select(AuditEvent))).scalar_one()
    assert event.comment == "checked evidence" and event.before == {"decision": "pending_review"}
    with pytest.raises(Exception) as error:
        await DecisionService(db).submit_review("decision", "approve", "other", "again")
    assert error.value.status_code == 409


async def test_reject_without_reason_is_rejected(db):
    seed_decision(db)
    with pytest.raises(Exception) as error:
        await DecisionService(db).submit_review("decision", "reject", "reviewer")
    assert error.value.status_code == 422


async def test_review_pagination_has_real_total_and_offset(db):
    seed_decision(db)
    db.add(
        DecisionResult(
            id="second",
            request_id="second-request",
            analysis_id="analysis",
            decision=Decision.PENDING_REVIEW,
        )
    )
    await db.commit()
    service = DecisionService(db)
    first = await service.get_pending_reviews(page=1, page_size=1)
    second = await service.get_pending_reviews(page=2, page_size=1)
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["request_id"] != second["items"][0]["request_id"]


async def test_treatment_lifecycle_requires_assignment_evidence_and_review(db):
    seed_decision(db)
    user = {"sub": "owner", "role": "decider"}
    with pytest.raises(HTTPException):
        await update_treatment(
            "decision", TreatmentUpdate(status="closed", revision=0, comment="skip"), db, user
        )
    with pytest.raises(HTTPException):
        await update_treatment(
            "decision",
            TreatmentUpdate(status="in_progress", revision=0, comment="missing owner"),
            db,
            user,
        )
    req = {"owner_id": "owner", "due_at": "2030-01-01T00:00:00Z", "comment": "assigned"}
    await update_treatment(
        "decision", TreatmentUpdate(status="in_progress", revision=0, **req), db, user
    )
    with pytest.raises(HTTPException) as error:
        await update_treatment(
            "decision",
            TreatmentUpdate(status="resolved", revision=0, resolution="evidence", **req),
            db,
            user,
        )
    assert error.value.status_code == 409
    await update_treatment(
        "decision",
        TreatmentUpdate(
            status="resolved", revision=1, resolution="supplier delivery confirmed", **req
        ),
        db,
        user,
    )
    with pytest.raises(HTTPException):
        await update_treatment(
            "decision", TreatmentUpdate(status="closed", revision=2, **req), db, user
        )
    await DecisionService(db).submit_review("decision", "approve", "owner", "verified")
    await update_treatment(
        "decision", TreatmentUpdate(status="closed", revision=3, **req), db, user
    )
    assert db.session.get(DecisionResult, "decision").case_status == "closed"


@pytest.mark.parametrize(
    "channel",
    [
        {"type": "email", "config": "bad"},
        {"type": "webhook", "config": "file:///secret"},
        {"type": "slack", "config": ""},
    ],
)
def test_invalid_enabled_notification_channel(channel):
    with pytest.raises(ValidationError):
        NotificationChannel(id="1", name="test", enabled=True, **channel)


def test_request_context_isolation():
    before = get_effective_llm_config()
    token = request_llm_config.set({"model": "isolated"})
    try:
        assert get_effective_llm_config()["model"] == "isolated"
    finally:
        request_llm_config.reset(token)
    assert get_effective_llm_config() == before


def test_auth_cookies_are_http_only_and_scoped(monkeypatch):
    from app.core.session import set_auth_cookies

    monkeypatch.setattr(
        "app.core.session.get_settings",
        lambda: SimpleNamespace(
            is_production=True, JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15, JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
        ),
    )
    response = Response()
    set_auth_cookies(response, "access", "refresh")
    cookies = response.headers.getlist("set-cookie")
    assert all("HttpOnly" in c and "Secure" in c and "SameSite=lax" in c for c in cookies)
    assert "Path=/api/v1/auth" in cookies[1]


def guarded_client(monkeypatch, redis):
    from app.core.request_guard import RequestGuardMiddleware

    monkeypatch.setattr("app.core.request_guard.get_redis", AsyncMock(return_value=redis))
    monkeypatch.setattr(
        "app.core.request_guard.get_settings",
        lambda: SimpleNamespace(
            REQUEST_BODY_MAX_SIZE_MB=1,
            LOGIN_RATE_LIMIT_PER_MINUTE=2,
            RATE_LIMIT_PER_MINUTE=5,
            is_production=True,
            cors_origins_list=["https://allowed.test"],
        ),
    )
    app = FastAPI()
    app.add_middleware(RequestGuardMiddleware)

    @app.post("/api/v1/auth/login")
    async def login():
        return {"ok": True}

    return TestClient(app)


def test_distributed_rate_limit_and_retry_header(monkeypatch):
    redis = SimpleNamespace(eval=AsyncMock(side_effect=[1, 2, 3]))
    with guarded_client(monkeypatch, redis) as client:
        assert client.post("/api/v1/auth/login", json={}).status_code == 200
        assert client.post("/api/v1/auth/login", json={}).status_code == 200
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 429 and "retry-after" in resp.headers


def test_cookie_writes_reject_untrusted_origin(monkeypatch):
    with guarded_client(monkeypatch, SimpleNamespace(eval=AsyncMock(return_value=1))) as client:
        resp = client.post(
            "/api/v1/auth/login",
            headers={"Cookie": "access_token=token", "Origin": "https://evil.test"},
        )
        assert resp.status_code == 403


def test_request_size_limit_and_unavailable_redis_fail_closed(monkeypatch):
    with guarded_client(
        monkeypatch, SimpleNamespace(eval=AsyncMock(side_effect=ConnectionError()))
    ) as client:
        assert (
            client.post(
                "/api/v1/auth/login", content=b"x", headers={"Content-Length": "2000000"}
            ).status_code
            == 413
        )
        assert client.post("/api/v1/auth/login", json={}).status_code == 503


async def test_mq_json_and_routing(monkeypatch):
    from app.core.mq import publish_risk_alert

    exchange = SimpleNamespace(publish=AsyncMock())
    channel = SimpleNamespace(get_exchange=AsyncMock(return_value=exchange))
    monkeypatch.setattr("app.core.mq.get_mq_channel", AsyncMock(return_value=channel))
    await publish_risk_alert("critical", {"event_id": "event", "name": "风险"})
    message = exchange.publish.call_args.args[0]
    assert json.loads(message.body)["name"] == "风险"
    assert message.message_id == "event" and message.content_type == "application/json"
    assert exchange.publish.call_args.kwargs["routing_key"] == "risk.alert.high"


async def test_notification_failed_delivery_has_bounded_retries(monkeypatch):
    from app.workers.notifications import retry_or_dead_letter

    exchange = SimpleNamespace(publish=AsyncMock())
    monkeypatch.setattr(
        "app.workers.notifications.get_mq_channel",
        AsyncMock(return_value=SimpleNamespace(default_exchange=exchange)),
    )
    msg = SimpleNamespace(
        headers={"attempts": 3},
        reject=AsyncMock(),
        body=b"{}",
        message_id="event",
        routing_key="risk.alert.high",
        ack=AsyncMock(),
        nack=AsyncMock(),
    )
    await retry_or_dead_letter(msg)
    msg.reject.assert_awaited_once_with(requeue=False)
    msg.headers = {"attempts": 1}
    await retry_or_dead_letter(msg)
    msg.ack.assert_awaited_once()
    assert exchange.publish.call_args.args[0].headers["attempts"] == 2


async def test_browser_login_response_does_not_expose_tokens(monkeypatch):
    from app.api.v1.auth import login

    result = TokenResponse(
        access_token="access-secret",
        refresh_token="refresh-secret",
        expires_in=900,
        user={
            "id": "u",
            "username": "user",
            "email": "u@example.com",
            "role": "analyst",
            "is_active": True,
            "created_at": "2026-01-01",
        },
    )
    monkeypatch.setattr("app.api.v1.auth.AuthService.login", AsyncMock(return_value=result))
    monkeypatch.setattr("app.api.v1.auth.set_auth_cookies", lambda *args: None)
    browser = await login(
        LoginRequest(username="user", password="password123"),
        None,
        Response(),
        SimpleNamespace(headers={"origin": "http://localhost:5173"}),
    )
    assert "access_token" not in browser.data and "refresh_token" not in browser.data
    cli = await login(
        LoginRequest(username="user", password="password123"),
        None,
        Response(),
        SimpleNamespace(headers={}),
    )
    assert cli.data["access_token"] == "access-secret"


async def test_refresh_token_rotation_is_single_use(monkeypatch):
    from app.core.session import new_session, rotate_session

    class Redis:
        def __init__(self):
            self.values = {}

        async def set(self, key, value, **kwargs):
            self.values[key] = value
            return True

        async def eval(self, script, keys, key, old, new, ttl):
            current = json.loads(self.values.get(key, "{}"))
            if current.get("refresh_id") != old:
                return 0
            current["refresh_id"] = new
            self.values[key] = json.dumps(current)
            return 1

    redis = Redis()
    monkeypatch.setattr("app.core.session.get_redis", AsyncMock(return_value=redis))
    claims = {
        "sub": "user",
        "username": "user",
        "role": "analyst",
        "scopes": ["read"],
        "is_active": True,
    }
    _, refresh = await new_session(claims)
    await rotate_session(refresh, claims)
    with pytest.raises(HTTPException):
        await rotate_session(refresh, claims)


async def test_dependency_health_reports_each_dependency(monkeypatch):
    from app.core.health import dependency_health

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, statement):
            return None

    monkeypatch.setattr(
        "app.core.health.get_engine", lambda: SimpleNamespace(connect=lambda: Connection())
    )
    monkeypatch.setattr(
        "app.core.health.get_redis", AsyncMock(return_value=SimpleNamespace(ping=AsyncMock()))
    )
    monkeypatch.setattr(
        "app.core.health.get_mq_connection",
        AsyncMock(return_value=SimpleNamespace(is_closed=False)),
    )
    assert await dependency_health() == {
        "status": "ok",
        "database": "connected",
        "redis": "connected",
        "rabbitmq": "connected",
    }
    monkeypatch.setattr(
        "app.core.health.get_mq_connection", AsyncMock(side_effect=ConnectionError())
    )
    assert (await dependency_health())["rabbitmq"] == "unavailable"


async def test_websocket_requires_valid_origin_and_session(monkeypatch):
    from app.api.v1.websocket import authorized

    socket = SimpleNamespace(
        headers={"origin": "http://localhost:5173"}, cookies={"access_token": "token"}
    )
    monkeypatch.setattr(
        "app.api.v1.websocket.decode_token",
        lambda token: {"type": "access", "sid": "s", "sub": "u"},
    )
    monkeypatch.setattr(
        "app.api.v1.websocket.get_redis",
        AsyncMock(return_value=SimpleNamespace(get=AsyncMock(return_value='{"sub":"u"}'))),
    )
    assert await authorized(socket)
    socket.headers["origin"] = "https://evil.test"
    assert not await authorized(socket)
