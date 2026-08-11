"""
供应链风险控制系统 - 全模块综合测试
覆盖：认证、规则引擎、风险评估、决策、审核、仪表盘、原始数据、用户管理、WebSocket、健康检查
"""

import requests
import json
import time
import sys
import traceback
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# 测试结果收集
results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "details": [],
    "start_time": datetime.now().isoformat(),
}

# 全局 token 存储
tokens = {"admin": None, "analyst": None, "decider": None}
created_resources = {"raw_data_ids": [], "rule_ids": [], "user_ids": [], "request_ids": []}


def log(level, module, test_name, message=""):
    """统一日志输出"""
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "○", "INFO": "→"}
    print(f"  {icon.get(level, '?')} [{module}] {test_name}: {message}")


def assert_status(resp, expected, module, test_name):
    """断言 HTTP 状态码"""
    if resp.status_code == expected:
        results["passed"] += 1
        results["details"].append({"module": module, "test": test_name, "status": "PASS", "code": resp.status_code})
        log("PASS", module, test_name, f"HTTP {resp.status_code}")
        return True
    else:
        results["failed"] += 1
        detail = ""
        try:
            detail = resp.json()
        except:
            detail = resp.text[:200]
        msg = f"expected {expected}, got {resp.status_code}. Body: {detail}"
        results["details"].append({"module": module, "test": test_name, "status": "FAIL", "code": resp.status_code, "error": msg})
        log("FAIL", module, test_name, msg)
        return False


def assert_json_structure(resp, required_keys, module, test_name):
    """断言响应 JSON 结构"""
    try:
        data = resp.json()
        if isinstance(data, dict):
            # 检查顶层结构
            if "code" in required_keys:
                assert data.get("code") == "OK", f"code should be OK, got {data.get('code')}"
            if "data" in required_keys:
                assert "data" in data, "response missing 'data' field"
            if "total" in required_keys:
                assert "total" in data, "response missing 'total' field"
                assert "page" in data, "response missing 'page' field"
                assert "page_size" in data, "response missing 'page_size' field"
        results["passed"] += 1
        results["details"].append({"module": module, "test": test_name, "status": "PASS"})
        log("PASS", module, test_name, "JSON structure valid")
        return True
    except Exception as e:
        results["failed"] += 1
        results["details"].append({"module": module, "test": test_name, "status": "FAIL", "error": str(e)})
        log("FAIL", module, test_name, str(e))
        return False


def assert_contains(resp, key, expected_value, module, test_name):
    """断言响应中包含指定键值"""
    try:
        data = resp.json()
        val = data
        for k in key.split("."):
            val = val.get(k, {}) if isinstance(val, dict) else None
        if val == expected_value:
            results["passed"] += 1
            log("PASS", module, test_name, f"{key}={expected_value}")
            return True
        else:
            results["failed"] += 1
            log("FAIL", module, test_name, f"expected {key}={expected_value}, got {val}")
            return False
    except Exception as e:
        results["failed"] += 1
        log("FAIL", module, test_name, str(e))
        return False


def auth_header(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


# ============================================================
# 1. 健康检查模块
# ============================================================
def test_health():
    module = "Health"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    # 1.1 存活探针
    r = requests.get(f"{BASE_URL}/health/live")
    assert_status(r, 200, module, "存活探针 GET /health/live")
    if r.status_code == 200:
        data = r.json()
        if data.get("status") == "ok":
            results["passed"] += 1
            log("PASS", module, "存活探针响应结构", "status=ok")
        else:
            results["failed"] += 1
            log("FAIL", module, "存活探针响应结构", f"expected status=ok, got {data}")

    # 1.2 就绪探针
    r = requests.get(f"{BASE_URL}/health/ready")
    assert_status(r, 200, module, "就绪探针 GET /health/ready")
    if r.status_code == 200:
        data = r.json()
        if data.get("status") in ("ok", "degraded"):
            results["passed"] += 1
            log("PASS", module, "就绪探针响应结构", f"status={data.get('status')}")
        else:
            results["failed"] += 1
            log("FAIL", module, "就绪探针响应结构", f"unexpected status: {data}")


# ============================================================
# 2. 认证模块
# ============================================================
def test_auth():
    module = "Auth"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    # 2.1 正常登录 (admin)
    r = requests.post(f"{API_V1}/auth/login", json={"username": "admin", "password": "admin123"})
    if assert_status(r, 200, module, "admin登录 POST /auth/login"):
        tokens["admin"] = r.json()["data"]["access_token"]
        assert_json_structure(r, ["data"], module, "登录响应结构")
        assert_contains(r, "data.user.role", "admin", module, "admin角色验证")
        assert_contains(r, "data.token_type", "bearer", module, "token类型验证")

    # 2.2 错误密码登录
    r = requests.post(f"{API_V1}/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert_status(r, 401, module, "错误密码登录 → 401")

    # 2.3 空用户名登录
    r = requests.post(f"{API_V1}/auth/login", json={"username": "", "password": "admin123"})
    assert_status(r, 422, module, "空用户名登录 → 422 参数校验")

    # 2.4 缺少字段登录
    r = requests.post(f"{API_V1}/auth/login", json={"username": "admin"})
    assert_status(r, 422, module, "缺少password字段 → 422")

    # 2.5 获取当前用户信息
    if tokens["admin"]:
        r = requests.get(f"{API_V1}/auth/me", headers=auth_header(tokens["admin"]))
        assert_status(r, 200, module, "获取当前用户 GET /auth/me")
        assert_contains(r, "data.username", "admin", module, "当前用户信息验证")

    # 2.6 无token访问 /me
    r = requests.get(f"{API_V1}/auth/me")
    assert_status(r, 401, module, "无token访问 /me → 401")

    # 2.7 无效token访问 /me
    r = requests.get(f"{API_V1}/auth/me", headers=auth_header("invalid_token"))
    assert_status(r, 401, module, "无效token访问 /me → 401")

    # 2.8 注册新用户 (边界测试)
    test_user = f"test_user_{int(time.time())}"
    r = requests.post(f"{API_V1}/auth/register", json={
        "username": test_user,
        "email": f"{test_user}@test.com",
        "password": "test123456",
        "role": "analyst"
    })
    if assert_status(r, 200, module, "注册新用户 POST /auth/register"):
        data = r.json()["data"]
        if "id" in data:
            created_resources["user_ids"].append(data["id"])
        tokens["analyst"] = requests.post(f"{API_V1}/auth/login",
            json={"username": test_user, "password": "test123456"}).json()["data"]["access_token"]

    # 2.9 重复用户名注册
    r = requests.post(f"{API_V1}/auth/register", json={
        "username": test_user,
        "email": "another@test.com",
        "password": "test123456"
    })
    assert_status(r, 409, module, "重复用户名注册 → 409")

    # 2.10 无效邮箱格式
    r = requests.post(f"{API_V1}/auth/register", json={
        "username": "invalid_email_user",
        "email": "not-an-email",
        "password": "test123456"
    })
    assert_status(r, 422, module, "无效邮箱格式 → 422")

    # 2.11 超短密码
    r = requests.post(f"{API_V1}/auth/register", json={
        "username": "shortpw",
        "email": "short@test.com",
        "password": "12"
    })
    assert_status(r, 422, module, "密码过短 → 422")

    # 2.12 无效角色注册
    r = requests.post(f"{API_V1}/auth/register", json={
        "username": "badrole",
        "email": "badrole@test.com",
        "password": "test123456",
        "role": "superadmin"
    })
    assert_status(r, 400, module, "无效角色注册 → 400")


# ============================================================
# 3. 规则引擎模块
# ============================================================
def test_rules():
    module = "Rules"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    admin_token = tokens["admin"]

    # 3.1 获取规则列表（无认证）
    r = requests.get(f"{API_V1}/rules", params={"page": 1, "page_size": 10})
    assert_status(r, 200, module, "获取规则列表 GET /rules")
    assert_json_structure(r, ["total", "data"], module, "规则列表分页结构")

    # 3.2 获取规则树
    r = requests.get(f"{API_V1}/rules/tree")
    assert_status(r, 200, module, "获取规则树 GET /rules/tree")
    assert_json_structure(r, ["data"], module, "规则树响应结构")

    # 3.3 创建规则 (需要 admin)
    rule_data = {
        "rule_name": f"测试规则_{int(time.time())}",
        "rule_type": "condition",
        "field_name": "risk_score",
        "operator": "gt",
        "threshold_value": "0.7",
        "logic_op": "AND",
        "weight": 1.5,
        "priority": 10,
        "description": "自动化测试规则"
    }
    r = requests.post(f"{API_V1}/rules", json=rule_data, headers=auth_header(admin_token))
    if assert_status(r, 201, module, "创建规则 POST /rules"):
        rule_id = r.json()["data"]["id"]
        created_resources["rule_ids"].append(rule_id)
        assert_contains(r, "data.rule_name", rule_data["rule_name"], module, "规则名称验证")
        assert_contains(r, "data.rule_type", "condition", module, "规则类型验证")
        assert_contains(r, "data.is_active", True, module, "规则默认启用")

    # 3.4 无权限创建规则 (analyst)
    if tokens["analyst"]:
        r = requests.post(f"{API_V1}/rules", json=rule_data, headers=auth_header(tokens["analyst"]))
        assert_status(r, 403, module, "analyst创建规则 → 403")

    # 3.5 缺少必填字段创建规则
    r = requests.post(f"{API_V1}/rules", json={"rule_type": "condition"}, headers=auth_header(admin_token))
    assert_status(r, 422, module, "缺少rule_name → 422")

    # 3.6 无效规则类型
    r = requests.post(f"{API_V1}/rules", json={
        "rule_name": "bad_type", "rule_type": "invalid"
    }, headers=auth_header(admin_token))
    assert_status(r, 422, module, "无效规则类型 → 422")

    # 3.7 更新规则
    if created_resources["rule_ids"]:
        rid = created_resources["rule_ids"][0]
        r = requests.put(f"{API_V1}/rules/{rid}", json={
            "rule_name": "更新后的规则",
            "rule_type": "condition",
            "weight": 2.0,
            "priority": 20
        }, headers=auth_header(admin_token))
        assert_status(r, 200, module, "更新规则 PUT /rules/{id}")
        assert_contains(r, "data.rule_name", "更新后的规则", module, "更新后规则名称验证")

    # 3.8 更新不存在的规则
    r = requests.put(f"{API_V1}/rules/nonexistent-id", json={
        "rule_name": "x", "rule_type": "condition"
    }, headers=auth_header(admin_token))
    assert_status(r, 404, module, "更新不存在的规则 → 404")

    # 3.9 切换规则状态
    if created_resources["rule_ids"]:
        rid = created_resources["rule_ids"][0]
        r = requests.post(f"{API_V1}/rules/{rid}/toggle", json={"is_active": False},
                          headers=auth_header(admin_token))
        assert_status(r, 200, module, "禁用规则 POST /rules/{id}/toggle")
        assert_contains(r, "data.is_active", False, module, "规则已禁用")

        r = requests.post(f"{API_V1}/rules/{rid}/toggle", json={"is_active": True},
                          headers=auth_header(admin_token))
        assert_status(r, 200, module, "启用规则 POST /rules/{id}/toggle")

    # 3.10 获取规则版本历史
    if created_resources["rule_ids"]:
        rid = created_resources["rule_ids"][0]
        r = requests.get(f"{API_V1}/rules/{rid}/versions")
        assert_status(r, 200, module, "获取版本历史 GET /rules/{id}/versions")
        assert_json_structure(r, ["data"], module, "版本历史响应结构")

    # 3.11 分页边界测试
    r = requests.get(f"{API_V1}/rules", params={"page": 0, "page_size": 10})
    assert_status(r, 422, module, "page=0 → 422")

    r = requests.get(f"{API_V1}/rules", params={"page": 1, "page_size": 200})
    assert_status(r, 422, module, "page_size=200 → 422")


# ============================================================
# 4. 原始数据模块
# ============================================================
def test_raw_data():
    module = "RawData"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    # 4.1 获取原始数据列表
    r = requests.get(f"{API_V1}/raw-data", params={"page": 1, "page_size": 10})
    assert_status(r, 200, module, "获取原始数据列表 GET /raw-data")
    assert_json_structure(r, ["total", "data"], module, "原始数据列表分页结构")

    # 4.2 创建原始数据
    raw_data = {
        "source_type": "api_test",
        "source_id": f"test_{int(time.time())}",
        "payload": {
            "supplier_name": "测试供应商",
            "risk_score": 0.75,
            "country": "CN",
            "transaction_amount": 500000,
            "items": ["电子元件", "芯片"],
            "metadata": {"verified": True, "level": "A"}
        }
    }
    r = requests.post(f"{API_V1}/raw-data", json=raw_data)
    if assert_status(r, 201, module, "创建原始数据 POST /raw-data"):
        raw_id = r.json()["data"]["id"]
        created_resources["raw_data_ids"].append(raw_id)
        assert_contains(r, "data.source_type", "api_test", module, "source_type验证")
        assert_contains(r, "data.status", "pending", module, "初始状态pending")

    # 4.3 获取原始数据详情
    if created_resources["raw_data_ids"]:
        rid = created_resources["raw_data_ids"][0]
        r = requests.get(f"{API_V1}/raw-data/{rid}")
        assert_status(r, 200, module, "获取原始数据详情 GET /raw-data/{id}")
        assert_contains(r, "data.id", rid, module, "数据ID匹配")

    # 4.4 获取不存在的原始数据
    r = requests.get(f"{API_V1}/raw-data/nonexistent")
    assert_status(r, 404, module, "获取不存在的数据 → 404")

    # 4.5 按状态筛选 (边界)
    r = requests.get(f"{API_V1}/raw-data", params={"status": "pending"})
    assert_status(r, 200, module, "按status筛选 pending")
    assert_json_structure(r, ["total"], module, "筛选结果分页结构")

    # 4.6 按来源筛选
    r = requests.get(f"{API_V1}/raw-data", params={"source": "api_test"})
    assert_status(r, 200, module, "按source筛选")
    assert_json_structure(r, ["total"], module, "source筛选结果结构")

    # 4.7 搜索
    r = requests.get(f"{API_V1}/raw-data", params={"search": "test"})
    assert_status(r, 200, module, "关键词搜索")

    # 4.8 空payload创建
    r = requests.post(f"{API_V1}/raw-data", json={"source_type": "empty_test", "source_id": "empty"})
    assert_status(r, 201, module, "空payload创建 → 201")
    if r.status_code == 201:
        created_resources["raw_data_ids"].append(r.json()["data"]["id"])

    # 4.9 超大数据payload (边界)
    large_payload = {
        "source_type": "large_test",
        "source_id": "large",
        "payload": {"data": "x" * 10000}
    }
    r = requests.post(f"{API_V1}/raw-data", json=large_payload)
    assert_status(r, 201, module, "大数据payload创建")
    if r.status_code == 201:
        created_resources["raw_data_ids"].append(r.json()["data"]["id"])


# ============================================================
# 5. 风险评估模块
# ============================================================
def test_risk():
    module = "Risk"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    # 5.1 获取分析结果列表
    r = requests.get(f"{API_V1}/risk/analyze", params={"page": 1, "page_size": 10})
    assert_status(r, 200, module, "获取分析结果列表 GET /risk/analyze")
    assert_json_structure(r, ["total", "data"], module, "分析列表分页结构")

    # 5.2 提交风险评估（LLM Agent 依赖，设置超时）
    if created_resources["raw_data_ids"]:
        rid = created_resources["raw_data_ids"][0]
        try:
            r = requests.post(f"{API_V1}/risk/analyze", json={
                "raw_data_id": rid,
                "force_reanalyze": False
            }, timeout=10)
            if r.status_code == 500:
                detail = r.json().get("detail", {})
                if "Agent" in str(detail) or "LLM" in str(detail):
                    results["skipped"] += 1
                    log("SKIP", module, "提交风险评估", "Agent/LLM未配置，跳过")
                else:
                    assert_status(r, 200, module, "提交风险评估 POST /risk/analyze")
            else:
                assert_status(r, 200, module, "提交风险评估 POST /risk/analyze")
                if r.status_code == 200:
                    req_id = r.json().get("data", {}).get("request_id", "")
                    if req_id:
                        created_resources["request_ids"].append(req_id)
        except requests.Timeout:
            results["skipped"] += 1
            log("SKIP", module, "提交风险评估", "请求超时(Agent初始化)，跳过")

    # 5.3 使用不存在的raw_data_id
    r = requests.post(f"{API_V1}/risk/analyze", json={
        "raw_data_id": "nonexistent-id",
        "force_reanalyze": False
    })
    assert_status(r, 404, module, "不存在raw_data_id → 404")

    # 5.4 缺少必填字段
    r = requests.post(f"{API_V1}/risk/analyze", json={"force_reanalyze": False})
    assert_status(r, 422, module, "缺少raw_data_id → 422")

    # 5.5 查询分析结果
    if created_resources["request_ids"]:
        req_id = created_resources["request_ids"][0]
        r = requests.get(f"{API_V1}/risk/analyze/{req_id}")
        # 可能返回200或404（取决于处理状态）
        log("INFO", module, "查询分析结果", f"GET /risk/analyze/{req_id} → {r.status_code}")

    # 5.6 查询不存在的分析结果
    r = requests.get(f"{API_V1}/risk/analyze/nonexistent-req")
    assert_status(r, 404, module, "查询不存在分析结果 → 404")

    # 5.7 批量分析 (边界，LLM Agent 依赖)
    if len(created_resources["raw_data_ids"]) >= 2:
        try:
            r = requests.post(f"{API_V1}/risk/analyze/batch", json={
                "raw_data_ids": created_resources["raw_data_ids"][:2]
            }, timeout=10)
            if r.status_code == 500:
                detail = r.json().get("detail", {})
                if "Agent" in str(detail) or "LLM" in str(detail):
                    results["skipped"] += 1
                    log("SKIP", module, "批量风险评估", "Agent/LLM未配置，跳过")
                else:
                    assert_status(r, 200, module, "批量风险评估 POST /risk/analyze/batch")
            else:
                assert_status(r, 200, module, "批量风险评估 POST /risk/analyze/batch")
        except requests.Timeout:
            results["skipped"] += 1
            log("SKIP", module, "批量风险评估", "请求超时(Agent初始化)，跳过")

    # 5.8 空批量
    r = requests.post(f"{API_V1}/risk/analyze/batch", json={"raw_data_ids": []})
    assert_status(r, 422, module, "空批量ID列表 → 422")

    # 5.9 分页边界
    r = requests.get(f"{API_V1}/risk/analyze", params={"page": 0, "page_size": 10})
    assert_status(r, 422, module, "page=0 → 422")


# ============================================================
# 6. 决策模块
# ============================================================
def test_decision():
    module = "Decision"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    # 6.1 获取决策列表
    r = requests.get(f"{API_V1}/decision", params={"page": 1, "page_size": 10})
    assert_status(r, 200, module, "获取决策列表 GET /decision")
    assert_json_structure(r, ["total", "data"], module, "决策列表分页结构")

    # 6.2 提交决策 (使用已存在的request_id)
    if created_resources["request_ids"]:
        req_id = created_resources["request_ids"][0]
        r = requests.post(f"{API_V1}/decision/make", json={"request_id": req_id})
        log("INFO", module, "提交决策", f"POST /decision/make → {r.status_code}")

    # 6.3 不存在的request_id决策
    r = requests.post(f"{API_V1}/decision/make", json={"request_id": "nonexistent"})
    assert_status(r, 404, module, "不存在request_id决策 → 404")

    # 6.4 缺少request_id
    r = requests.post(f"{API_V1}/decision/make", json={})
    assert_status(r, 422, module, "缺少request_id → 422")

    # 6.5 查询决策结果
    if created_resources["request_ids"]:
        req_id = created_resources["request_ids"][0]
        r = requests.get(f"{API_V1}/decision/{req_id}")
        log("INFO", module, "查询决策结果", f"GET /decision/{req_id} → {r.status_code}")

    # 6.6 查询不存在的决策
    r = requests.get(f"{API_V1}/decision/nonexistent")
    assert_status(r, 404, module, "查询不存在决策 → 404")

    # 6.7 获取决策链路追踪
    if created_resources["request_ids"]:
        req_id = created_resources["request_ids"][0]
        r = requests.get(f"{API_V1}/decision/{req_id}/trace")
        assert_status(r, 200, module, "获取决策链路追踪")
        assert_json_structure(r, ["data"], module, "链路追踪响应结构")


# ============================================================
# 7. 审核模块
# ============================================================
def test_review():
    module = "Review"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    admin_token = tokens["admin"]

    # 7.1 获取待审核列表
    r = requests.get(f"{API_V1}/review/pending", params={"page": 1, "page_size": 10})
    assert_status(r, 200, module, "获取待审核列表 GET /review/pending")
    assert_json_structure(r, ["total", "data"], module, "待审核列表分页结构")

    # 7.2 审核通过（无认证）
    r = requests.post(f"{API_V1}/review/test-id/approve", json={"action": "approve"})
    assert_status(r, 401, module, "无认证审核 → 401")

    # 7.3 审核通过（有认证，不存在ID）
    r = requests.post(f"{API_V1}/review/nonexistent/approve", json={
        "action": "approve", "comment": "test"
    }, headers=auth_header(admin_token))
    assert_status(r, 404, module, "审核不存在ID → 404")

    # 7.4 审核驳回（缺少action）
    r = requests.post(f"{API_V1}/review/test-id/reject", json={"comment": "test"},
                      headers=auth_header(admin_token))
    assert_status(r, 422, module, "审核缺少action → 422")

    # 7.5 无效action
    r = requests.post(f"{API_V1}/review/test-id/approve", json={
        "action": "invalid_action"
    }, headers=auth_header(admin_token))
    assert_status(r, 422, module, "无效action → 422")

    # 7.6 人工覆盖
    r = requests.post(f"{API_V1}/review/nonexistent/override", json={
        "action": "override",
        "comment": "manual override",
        "override_decision": "approve"
    }, headers=auth_header(admin_token))
    assert_status(r, 404, module, "覆盖不存在ID → 404")


# ============================================================
# 8. 仪表盘模块
# ============================================================
def test_dashboard():
    module = "Dashboard"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    # 8.1 汇总统计
    r = requests.get(f"{API_V1}/dashboard/summary")
    assert_status(r, 200, module, "汇总统计 GET /dashboard/summary")
    assert_json_structure(r, ["data"], module, "汇总统计响应结构")
    assert_contains(r, "data.total_risks", 0, module, "默认total_risks=0")

    # 8.2 趋势数据
    r = requests.get(f"{API_V1}/dashboard/trends", params={"days": 7})
    assert_status(r, 200, module, "趋势数据 GET /dashboard/trends?days=7")
    assert_json_structure(r, ["data"], module, "趋势数据响应结构")

    # 8.3 趋势数据边界 (days=0)
    r = requests.get(f"{API_V1}/dashboard/trends", params={"days": 0})
    assert_status(r, 200, module, "趋势数据 days=0 边界")

    # 8.4 趋势数据边界 (days=365)
    r = requests.get(f"{API_V1}/dashboard/trends", params={"days": 365})
    assert_status(r, 200, module, "趋势数据 days=365 边界")

    # 8.5 告警列表
    r = requests.get(f"{API_V1}/dashboard/alerts", params={"limit": 10})
    assert_status(r, 200, module, "告警列表 GET /dashboard/alerts?limit=10")
    assert_json_structure(r, ["data"], module, "告警列表响应结构")

    # 8.6 告警列表边界 (limit=0)
    r = requests.get(f"{API_V1}/dashboard/alerts", params={"limit": 0})
    assert_status(r, 200, module, "告警列表 limit=0 边界")

    # 8.7 告警列表边界 (limit=1000)
    r = requests.get(f"{API_V1}/dashboard/alerts", params={"limit": 1000})
    assert_status(r, 200, module, "告警列表 limit=1000 边界")


# ============================================================
# 9. 用户管理模块
# ============================================================
def test_user_management():
    module = "UserMgmt"
    print(f"\n{'='*60}")
    print(f"  {module} 模块测试")
    print(f"{'='*60}")

    admin_token = tokens["admin"]

    # 9.1 获取用户列表 (admin)
    r = requests.get(f"{API_V1}/users", params={"page": 1, "page_size": 10},
                     headers=auth_header(admin_token))
    assert_status(r, 200, module, "获取用户列表 GET /users")
    assert_json_structure(r, ["total", "data"], module, "用户列表分页结构")

    # 9.2 无权限获取用户列表 (analyst)
    if tokens["analyst"]:
        r = requests.get(f"{API_V1}/users", headers=auth_header(tokens["analyst"]))
        assert_status(r, 403, module, "analyst获取用户列表 → 403")

    # 9.3 无认证获取用户列表
    r = requests.get(f"{API_V1}/users")
    assert_status(r, 401, module, "无认证获取用户列表 → 401")

    # 9.4 按角色筛选
    r = requests.get(f"{API_V1}/users", params={"role": "admin"},
                     headers=auth_header(admin_token))
    assert_status(r, 200, module, "按role=admin筛选")
    assert_json_structure(r, ["total"], module, "角色筛选结果结构")

    # 9.5 搜索用户
    r = requests.get(f"{API_V1}/users", params={"search": "admin"},
                     headers=auth_header(admin_token))
    assert_status(r, 200, module, "搜索用户 admin")

    # 9.6 创建用户 (admin)
    new_user = f"mgmt_test_{int(time.time())}"
    r = requests.post(f"{API_V1}/users", params={
        "username": new_user,
        "email": f"{new_user}@test.com",
        "password": "test123456",
        "role": "decider"
    }, headers=auth_header(admin_token))
    if assert_status(r, 201, module, "创建用户 POST /users"):
        user_id = r.json()["data"]["id"]
        created_resources["user_ids"].append(user_id)
        assert_contains(r, "data.role", "decider", module, "创建用户角色验证")

    # 9.7 重复用户名创建
    r = requests.post(f"{API_V1}/users", params={
        "username": new_user,
        "email": "different@test.com",
        "password": "test123456"
    }, headers=auth_header(admin_token))
    assert_status(r, 409, module, "重复用户名创建 → 409")

    # 9.8 无效角色创建
    r = requests.post(f"{API_V1}/users", params={
        "username": "badrole2",
        "email": "badrole2@test.com",
        "password": "test123456",
        "role": "superadmin"
    }, headers=auth_header(admin_token))
    assert_status(r, 400, module, "无效角色创建 → 400")

    # 9.9 更新用户
    if created_resources["user_ids"]:
        uid = created_resources["user_ids"][-1]
        r = requests.put(f"{API_V1}/users/{uid}", params={
            "role": "analyst", "is_active": False
        }, headers=auth_header(admin_token))
        assert_status(r, 200, module, "更新用户 PUT /users/{id}")
        assert_contains(r, "data.is_active", False, module, "用户已禁用")

    # 9.10 更新不存在的用户
    r = requests.put(f"{API_V1}/users/nonexistent", params={"role": "admin"},
                     headers=auth_header(admin_token))
    assert_status(r, 404, module, "更新不存在用户 → 404")


# ============================================================
# 10. 性能测试
# ============================================================
def test_performance():
    module = "Perf"
    print(f"\n{'='*60}")
    print(f"  {module} 性能测试")
    print(f"{'='*60}")

    endpoints = [
        ("GET", f"{BASE_URL}/health/live", None),
        ("GET", f"{API_V1}/dashboard/summary", None),
        ("GET", f"{API_V1}/rules/tree", None),
        ("GET", f"{API_V1}/raw-data?page=1&page_size=5", None),
    ]

    for method, url, _ in endpoints:
        times_list = []
        for i in range(5):
            start = time.time()
            if method == "GET":
                r = requests.get(url)
            elapsed = (time.time() - start) * 1000
            times_list.append(elapsed)

        avg_time = sum(times_list) / len(times_list)
        max_time = max(times_list)
        status = "PASS" if avg_time < 5000 else "FAIL"
        msg = f"avg={avg_time:.1f}ms, max={max_time:.1f}ms [5次采样]"
        results["details"].append({
            "module": module, "test": f"{method} {url}", "status": status,
            "avg_ms": round(avg_time, 1), "max_ms": round(max_time, 1)
        })
        if status == "PASS":
            results["passed"] += 1
        else:
            results["failed"] += 1
        log(status, module, f"{method} {url}", msg)


# ============================================================
# 11. 清理资源
# ============================================================
def test_cleanup():
    module = "Cleanup"
    print(f"\n{'='*60}")
    print(f"  {module} 清理测试资源")
    print(f"{'='*60}")

    admin_token = tokens["admin"]

    # 删除规则
    for rid in created_resources["rule_ids"]:
        r = requests.delete(f"{API_V1}/rules/{rid}", headers=auth_header(admin_token))
        log("INFO", module, f"删除规则 {rid}", f"→ {r.status_code}")

    # 删除原始数据
    for rid in created_resources["raw_data_ids"]:
        r = requests.delete(f"{API_V1}/raw-data/{rid}")
        log("INFO", module, f"删除原始数据 {rid}", f"→ {r.status_code}")

    # 删除测试用户
    for uid in created_resources["user_ids"]:
        r = requests.delete(f"{API_V1}/users/{uid}", headers=auth_header(admin_token))
        log("INFO", module, f"删除用户 {uid}", f"→ {r.status_code}")


# ============================================================
# 主入口
# ============================================================
def main():
    print("=" * 60)
    print("  供应链风险控制系统 - 全模块综合测试")
    print(f"  目标: {BASE_URL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        # 1. 健康检查
        test_health()

        # 2. 认证模块
        test_auth()

        # 3. 规则引擎
        test_rules()

        # 4. 原始数据
        test_raw_data()

        # 5. 风险评估
        test_risk()

        # 6. 决策
        test_decision()

        # 7. 审核
        test_review()

        # 8. 仪表盘
        test_dashboard()

        # 9. 用户管理
        test_user_management()

        # 10. 性能测试
        test_performance()

        # 11. 清理
        test_cleanup()

    except requests.exceptions.ConnectionError:
        print("\n  ✗ 无法连接到后端服务，请确认服务已启动!")
        print(f"    请运行: cd d:\\work_file\\skill\\Supply Chain Risk Control System && python -m app.main")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ✗ 测试异常: {e}")
        traceback.print_exc()

    # ============================================================
    # 汇总报告
    # ============================================================
    total = results["passed"] + results["failed"] + results["skipped"]
    pass_rate = (results["passed"] / total * 100) if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"  测试汇总报告")
    print(f"{'='*60}")
    print(f"  总计: {total} 项")
    print(f"  通过: {results['passed']} 项 ({pass_rate:.1f}%)")
    print(f"  失败: {results['failed']} 项")
    print(f"  跳过: {results['skipped']} 项")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 列出失败项
    failures = [d for d in results["details"] if d["status"] == "FAIL"]
    if failures:
        print(f"\n  --- 失败详情 ---")
        for f in failures:
            print(f"  [{f['module']}] {f['test']}")
            if "error" in f:
                print(f"        错误: {f['error']}")

    # 保存结果到文件
    results["end_time"] = datetime.now().isoformat()
    results["pass_rate"] = f"{pass_rate:.1f}%"
    results["total"] = total
    with open("tests/test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  详细结果已保存至: tests/test_results.json")

    return results["failed"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)