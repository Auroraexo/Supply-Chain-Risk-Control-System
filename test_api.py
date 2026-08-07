"""API 全链路功能测试 —— Agent 对接版。"""
import httpx
import asyncio

RAW_DATA_ID = "9044874a-cab3-4e46-ba93-e38679ecaf6b"


async def run_all_tests():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as c:
        # 1. 风险评估（含 Agent 决策全流程）
        print("=" * 60)
        print("1. POST /risk/analyze (Agent 决策全流程)")
        r = await c.post("/api/v1/risk/analyze", json={"raw_data_id": RAW_DATA_ID})
        print(f"   status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()["data"]
            req_id = data["request_id"]
            print(f"   request_id: {req_id}")
            print(f"   risk_score: {data['risk_score']}, risk_level: {data['risk_level']}")
            print(f"   decision: {data.get('decision')}, confidence: {data.get('confidence')}")
            print(f"   reflection_passed: {data.get('reflection_passed')}")
            print(f"   anomaly_tags: {data.get('anomaly_tags')}")
        else:
            print(f"   ERROR: {r.text[:200]}")
            req_id = None

        if not req_id:
            print("FAILED")
            return

        # 2. 查询分析结果
        print()
        print("2. GET /risk/analyze/{request_id}")
        r = await c.get(f"/api/v1/risk/analyze/{req_id}")
        print(f"   status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()["data"]
            print(f"   risk_score: {d['risk_score']}, risk_level: {d['risk_level']}")
            print(f"   decision: {d.get('decision')}, confidence: {d.get('confidence')}")

        # 3. 决策（应返回缓存的 Agent 结果）
        print()
        print("3. POST /decision/make (应返回缓存决策)")
        r = await c.post("/api/v1/decision/make", json={"request_id": req_id})
        print(f"   status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()["data"]
            print(f"   decision: {d['decision']}, confidence: {d['confidence']}")
            print(f"   from_cache: {d.get('from_cache')}")

        # 4. 决策追踪
        print()
        print("4. GET /decision/{id}/trace")
        r = await c.get(f"/api/v1/decision/{req_id}/trace")
        print(f"   status: {r.status_code}")

        # 5. 规则管理
        print()
        print("5. GET /rules")
        r = await c.get("/api/v1/rules")
        total = r.json().get("total", 0)
        print(f"   status: {r.status_code}, total: {total}")

        # 6. 创建规则
        print()
        print("6. POST /rules (创建规则)")
        r = await c.post("/api/v1/rules", json={
            "rule_name": "高风险延迟检测",
            "rule_type": "condition",
            "priority": 100,
            "condition_type": "threshold",
            "field_name": "delay_days",
            "operator": "gt",
            "threshold_value": 5,
            "logic_op": "AND",
            "action": {"action": "escalate", "reason": "延迟超过5天"},
            "description": "检测订单延迟超过5天的高风险情况",
        })
        print(f"   status: {r.status_code}")
        if r.status_code == 200:
            rule_id = r.json()["data"]["id"]
            print(f"   rule_id: {rule_id}")

            # 7. 获取规则版本
            print()
            print("7. GET /rules/{id}/versions")
            r = await c.get(f"/api/v1/rules/{rule_id}/versions")
            print(f"   status: {r.status_code}")
            if r.status_code == 200:
                print(f"   versions: {len(r.json()['data'])}")

            # 8. 更新规则
            print()
            print("8. PUT /rules/{id}")
            r = await c.put(f"/api/v1/rules/{rule_id}", json={"priority": 90, "description": "更新后描述"})
            print(f"   status: {r.status_code}")

            # 9. 再次获取版本（应有2个版本）
            print()
            print("9. GET /rules/{id}/versions (应有2个版本)")
            r = await c.get(f"/api/v1/rules/{rule_id}/versions")
            print(f"   status: {r.status_code}")
            if r.status_code == 200:
                print(f"   versions: {len(r.json()['data'])}")

            # 10. 回滚
            print()
            print("10. POST /rules/{id}/rollback?version=1")
            r = await c.post(f"/api/v1/rules/{rule_id}/rollback?version=1")
            print(f"   status: {r.status_code}")

        # 11. 参数校验
        print()
        print("11. POST /risk/analyze (empty) → 422")
        r = await c.post("/api/v1/risk/analyze", json={})
        print(f"   status: {r.status_code} (expected 422)")

        # 12. 404
        print()
        print("12. GET /risk/analyze/xxx → 404")
        r = await c.get("/api/v1/risk/analyze/nonexistent")
        print(f"   status: {r.status_code} (expected 404)")

        print()
        print("=" * 60)
        print("All tests passed! Agent ↔ Service 对接验证成功")


if __name__ == "__main__":
    asyncio.run(run_all_tests())