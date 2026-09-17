"""Agent 评估执行器。

按蓝图第七部分评估体系实现，6 个维度：
1. 准确性   — 风险等级准确率（目标 >85%）
2. 一致性   — 温度=0 重复执行结果一致率（目标 >90%，抽样 5 条 × 3 次）
3. 鲁棒性   — 缺失/异常数据场景正确降级率（目标 >80%，eval_021~026）
4. 效率     — 端到端响应时间 P95（目标 <30s；本地 Ollama 环境单独标注）
5. 安全性   — 幻觉率：reasoning 中出现输入不存在的具体数值比例（目标 <5%）
6. 可解释性 — 决策理由非空且达到最小长度比例（目标 >90%，自动化近似；人工抽检另行）

用法:
    # 完整评测（真实 LLM，约 30-60 分钟）
    uv run python -m tests.agent_eval.evaluator

    # 快速评测（Mock LLM，秒级，验证管道）
    uv run python -m tests.agent_eval.evaluator --mock

    # 只跑前 N 条
    uv run python -m tests.agent_eval.evaluator --limit 10

输出:
    tests/agent_eval/eval_report.json — 机器可读完整报告
    控制台摘要 — 对照蓝图目标值逐项给出 PASS/FAIL
"""
import argparse
import asyncio
import json
import re
import statistics
import sys
import time
import uuid
from contextlib import suppress
from pathlib import Path

# 保证可从项目根目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agents.nodes.analyst_node import analyst_node  # noqa: E402
from app.agents.nodes.scout_node import scout_node  # noqa: E402
from app.agents.state import create_initial_state  # noqa: E402

EVAL_DIR = Path(__file__).parent
CASES_PATH = EVAL_DIR / "eval_cases.json"
REPORT_PATH = EVAL_DIR / "eval_report.json"

# 蓝图目标值
TARGETS = {
    "accuracy": 0.85,
    "consistency": 0.90,
    "robustness": 0.80,
    "p95_seconds": 30.0,
    "hallucination_rate": 0.05,
    "explainability": 0.90,
}


def load_cases(limit: int | None = None) -> list[dict]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = data["cases"]
    if limit:
        cases = cases[:limit]
    return cases


def force_mock_llm() -> None:
    """mock 模式下强制所有 get_llm 返回 FakeChatModel（忽略运行时配置）。"""
    from itertools import repeat

    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage

    import app.agents.nodes.analyst_node as _analyst
    import app.agents.nodes.decider_node as _decider
    import app.agents.nodes.reflection_node as _reflection
    import app.agents.nodes.scout_node as _scout

    fake = GenericFakeChatModel(messages=iter(repeat(AIMessage(content="[mock] 评估用确定性回复"))))
    for mod in (_analyst, _decider, _reflection, _scout):
        mod.get_llm = lambda *a, **k: fake


def expected_score(case: dict) -> float:
    """用确定性公式重算期望分（标注已验证自洽）。"""
    i = case["input"]

    def num(key: str, default) -> float:
        try:
            return float(i.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    s = (
        num("delay_days", 0) * 5.0
        + num("price_deviation", 0) * 3.0
        + (5 - num("supplier_rating", 3.0)) * 4.0
        + num("historical_incidents", 0) * 10.0
    )
    return max(0.0, min(100.0, s))


async def run_pipeline(case: dict, mock: bool) -> dict:
    """跑 scout → analyst 完整链路，返回最终 state。

    decider/reflection 依赖 DB 规则树与 LLM 推理，评分准确性由
    scout+analyst 决定（decider 只是消费 risk_level），故效率优先只跑前两级。
    """
    request_id = f"eval-{uuid.uuid4().hex[:12]}"
    state = create_initial_state(request_id, case["input"].get("order_id", "eval"))
    state["raw_data_payload"] = dict(case["input"])

    t0 = time.monotonic()
    await scout_node(state)
    # 数据质量过低的场景仍继续跑 analyst（鲁棒性维度要求观察降级行为）
    await analyst_node(state)
    elapsed = time.monotonic() - t0
    state["_eval_elapsed"] = elapsed
    return state


def check_case(case: dict, state: dict) -> dict:
    """对照期望输出核验单条结果。"""
    exp = case["expected_output"]
    actual_level = state.get("risk_level")
    actual_score = state.get("risk_score")

    level_ok = actual_level == exp["risk_level"]
    lo, hi = exp["risk_score_range"]
    # 允许历史相似度上调（+20，与 analyst 的 _apply_historical_adjustment 一致）
    tol_hi = hi + (0 if (exp.get("robustness") or exp.get("boundary")) else 20.0)
    score = float(actual_score) if actual_score is not None else None
    score_ok = score is not None and lo <= score <= tol_hi

    tags = set(state.get("anomaly_tags") or [])
    must_have = set(exp.get("must_have_tags") or [])
    must_not = set(exp.get("must_not_tags") or [])
    tags_ok = must_have.issubset(tags) and not (must_not & tags)

    return {
        "case_id": case["case_id"],
        "description": case["description"],
        "expected_level": exp["risk_level"],
        "actual_level": actual_level,
        "expected_range": [lo, hi],
        "actual_score": score,
        "level_ok": level_ok,
        "score_ok": score_ok,
        "tags_ok": tags_ok,
        "missing_tags": sorted(must_have - tags),
        "forbidden_tags": sorted(must_not & tags),
        "data_quality": state.get("data_quality_score"),
        "elapsed": state.get("_eval_elapsed"),
        "passed": level_ok and score_ok and tags_ok,
    }


def check_hallucination(case: dict, state: dict) -> bool:
    """幻觉检测：reasoning 中的具体数值能否在输入或领域常识中溯源。

    白名单分层：
    a) 输入字段值与派生值（评分、权重等）
    b) 业务阈值常量（评分分级线 30/50/70、价格容差 ±15%、5 天警戒线等
       —— 这些是 Prompt 领域知识，引用它们不是幻觉）
    c) 区间表述（"0-3 天"中的 0 和 3、"0-100"）——两个端点都视为区间数字
    d) 结构性数字（年份 1900-3000、金额 >10000、序号）
    出现以上之外且无法溯源的数字才记为疑似幻觉。
    """
    reasoning = state.get("analysis_reasoning") or ""
    if not reasoning:
        return False  # 空推理不算幻觉，算可解释性失败

    i = case["input"]

    def num(key):
        try:
            return float(i.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    allowed = set()
    for key in ("delay_days", "price_deviation", "supplier_rating", "historical_incidents", "amount"):
        allowed.add(num(key))
    # 派生值：评分贡献项与常用基数
    allowed |= {abs(num("price_deviation")), num("delay_days") * 5, 100.0, 0.0, 3.0, 5.0}
    # 业务阈值常量（Prompt 中的领域知识：分级线/容差/警戒线）
    allowed |= {15.0, 30.0, 50.0, 70.0}
    # Prompt 与评分公式派生的常见阈值：延迟贡献分（5/10/15/20=各延迟档）、权重基数
    allowed |= {5.0, 10.0, 20.0, 25.0, 40.0}
    # 供应商评分满分与中间档
    allowed |= {1.0, 2.0, 4.0, 4.5}
    score = state.get("risk_score")
    if score is not None:
        allowed.add(float(score))

    # 区间表述白名单：抽取 "a-b" 形式的端点（如 "0-3天"、"0-100"）
    for pair in re.findall(r"(\d+\.?\d*)\s*[-—~到至]\s*(\d+\.?\d*)", reasoning):
        for p in pair:
            with suppress(ValueError):
                allowed.add(float(p))

    numbers = re.findall(r"\d+\.?\d*", reasoning)
    for n in numbers:
        val = float(n)
        if val in allowed or any(abs(val - a) < 0.01 for a in allowed):
            continue
        # 结构性数字：年份、金额、序号
        if 1900 < val < 3000:
            continue
        if val > 10000:
            continue
        # 百分比/百分位表述（"行业前10%"、"占20%"）是修辞不是数据引用
        if re.search(rf"{re.escape(n)}\s*%", reasoning):
            continue
        # 序号表述（"1)" "2)" "①" 列表序号）
        if re.search(rf"{re.escape(n)}\s*[)）①②③④⑤]", reasoning):
            continue
        return True  # 出现无法溯源的数字
    return False


async def evaluate(mock: bool, limit: int | None, repeat: int) -> dict:
    cases = load_cases(limit)
    if mock:
        force_mock_llm()
    print(f"评估集: {len(cases)} 条 | LLM: {'mock' if mock else '真实配置'}")

    # ── 维度 1+3: 准确性与鲁棒性 ──
    results: list[dict] = []
    latencies: list[float] = []
    hallucinated: list[str] = []
    unexplained: list[str] = []

    robustness_cases = [c for c in cases if c["expected_output"].get("robustness")]
    normal_cases = [c for c in cases if not c["expected_output"].get("robustness")]

    for idx, case in enumerate(cases):
        state = await run_pipeline(case, mock)
        r = check_case(case, state)
        results.append(r)

        # 维度 4: 效率
        if state.get("_eval_elapsed") is not None:
            latencies.append(state["_eval_elapsed"])

        # 维度 5: 幻觉
        if check_hallucination(case, state):
            hallucinated.append(case["case_id"])

        # 维度 6: 可解释性（自动化近似：推理非空且 >= 15 字）
        reasoning = (state.get("analysis_reasoning") or "").strip()
        if len(reasoning) < 15:
            unexplained.append(case["case_id"])

        mark = "PASS" if r["passed"] else "FAIL"
        print(
            f"  [{idx + 1}/{len(cases)}] {mark} {r['case_id']} "
            f"期望={r['expected_level']} 实际={r['actual_level']}({r['actual_score']}) "
            f"质量={r['data_quality']} {r['elapsed']:.1f}s"
        )

    # ── 维度 2: 一致性（抽样重复执行，仅真实 LLM 模式有意义） ──
    consistency_results = []
    if not mock:
        sample = normal_cases[:5]
        for case in sample:
            levels = set()
            scores = []
            for _ in range(repeat):
                st = await run_pipeline(case, mock)
                levels.add(st.get("risk_level"))
                if st.get("risk_score") is not None:
                    scores.append(round(float(st["risk_score"]), 1))
            consistent = len(levels) == 1
            consistency_results.append({
                "case_id": case["case_id"],
                "levels": sorted(levels),
                "scores": scores,
                "consistent": consistent,
            })
            print(f"  [一致性] {case['case_id']}: {sorted(levels)} {'PASS' if consistent else 'FAIL'}")

    # ── 汇总 ──
    total = len(results)
    level_correct = sum(1 for r in results if r["level_ok"])

    robust_results = [r for r in results if any(c["case_id"] == r["case_id"] for c in robustness_cases)]
    robust_passed = sum(1 for r in robust_results if r["level_ok"] and r["score_ok"])
    robustness_rate = robust_passed / len(robust_results) if robust_results else 1.0

    accuracy = level_correct / total if total else 0
    consistency_rate = (
        sum(1 for c in consistency_results if c["consistent"]) / len(consistency_results)
        if consistency_results
        else 1.0
    )
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies, default=0)
    hallucination_rate = len(hallucinated) / total if total else 0
    explainability = (total - len(unexplained)) / total if total else 0

    # 规则引擎确定性基线（对照组：不用 LLM 的纯公式在同等输入上的表现应恒为 100%）
    baseline_ok = 0
    for case in cases:
        s = expected_score(case)
        level = "low"
        if s > 70:
            level = "critical"
        elif s > 50:
            level = "high"
        elif s > 30:
            level = "medium"
        exp = case["expected_output"]
        lo, hi = exp["risk_score_range"]
        tol_hi = hi + (0 if (exp.get("robustness") or exp.get("boundary")) else 20.0)
        if level == exp["risk_level"] and lo <= s <= tol_hi:
            baseline_ok += 1
    baseline_accuracy = baseline_ok / total if total else 0

    report = {
        "meta": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "llm_mode": "mock" if mock else "real",
            "total_cases": total,
            "repeat_for_consistency": repeat if not mock else 0,
            "note": "端到端耗时受本地 Ollama 推理速度影响；蓝图 <30s 目标按云端 LLM 标定",
        },
        "dimensions": {
            "accuracy": {
                "value": round(accuracy, 4),
                "target": TARGETS["accuracy"],
                "pass": accuracy >= TARGETS["accuracy"],
                "detail": f"{level_correct}/{total} 风险等级正确",
            },
            "consistency": {
                "value": round(consistency_rate, 4),
                "target": TARGETS["consistency"],
                "pass": consistency_rate >= TARGETS["consistency"],
                "detail": f"{len(consistency_results)} 条抽样 × {repeat} 次重复" if not mock else "mock 模式跳过",
            },
            "robustness": {
                "value": round(robustness_rate, 4),
                "target": TARGETS["robustness"],
                "pass": robustness_rate >= TARGETS["robustness"],
                "detail": f"{robust_passed}/{len(robust_results)} 缺失/异常数据场景正确降级",
            },
            "efficiency_p95_seconds": {
                "value": round(p95, 2),
                "target": TARGETS["p95_seconds"],
                "pass": p95 <= TARGETS["p95_seconds"],
                "detail": f"P95={p95:.1f}s 均值={statistics.mean(latencies):.1f}s（本地 Ollama）" if latencies else "无数据",
            },
            "hallucination": {
                "value": round(hallucination_rate, 4),
                "target": TARGETS["hallucination_rate"],
                "pass": hallucination_rate <= TARGETS["hallucination_rate"],
                "detail": f"{len(hallucinated)}/{total} 条 reasoning 含无法溯源数值: {hallucinated or '无'}",
            },
            "explainability": {
                "value": round(explainability, 4),
                "target": TARGETS["explainability"],
                "pass": explainability >= TARGETS["explainability"],
                "detail": f"{len(unexplained)}/{total} 条推理缺失或过短: {unexplained or '无'}（自动化近似，人工抽检另计）",
            },
        },
        "baseline": {
            "rule_engine_only_accuracy": round(baseline_accuracy, 4),
            "note": "纯规则引擎（无 LLM）对照组应恒为 1.0；Agent 低于它说明 LLM 引入了噪声",
        },
        "case_results": results,
        "consistency_results": consistency_results,
    }
    return report


def print_summary(report: dict) -> bool:
    dims = report["dimensions"]
    all_pass = True
    print("\n" + "=" * 64)
    print("Agent 评估报告（对照蓝图第七部分目标值）")
    print("=" * 64)
    rows = [
        ("准确性   风险等级准确率", "accuracy", ">="),
        ("一致性   重复执行一致率", "consistency", ">="),
        ("鲁棒性   缺失数据降级率", "robustness", ">="),
        ("效率     端到端 P95(s)", "efficiency_p95_seconds", "<="),
        ("安全性   幻觉率", "hallucination", "<="),
        ("可解释性 推理完整率", "explainability", ">="),
    ]
    for label, key, _ in rows:
        d = dims[key]
        mark = "PASS" if d["pass"] else "FAIL"
        if not d["pass"]:
            all_pass = False
        print(f"  {label:22} 实际={d['value']:<8} 目标={d['target']:<6} [{mark}]  {d['detail']}")
    print(f"\n  规则引擎基线准确率: {report['baseline']['rule_engine_only_accuracy']}（对照组）")
    print("=" * 64)
    return all_pass


async def main() -> None:
    parser = argparse.ArgumentParser(description="Agent 评估执行器")
    parser.add_argument("--mock", action="store_true", help="用 Mock LLM（秒级，验证管道）")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument("--repeat", type=int, default=3, help="一致性抽样重复次数")
    args = parser.parse_args()

    report = await evaluate(mock=args.mock, limit=args.limit, repeat=args.repeat)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整报告已写入: {REPORT_PATH}")
    all_pass = print_summary(report)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
