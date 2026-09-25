"""基于公开报道的真实供应链事件构造 Demo 种子数据。

每条数据都对应一个 2020-2024 年公开新闻报道过的真实供应链事件，
不是凭空编造的公司名。可在 README 里标注"基于公开历史事件构造演示数据"。

用法：
    python -m scripts.seed_demo_data
    # 或
    python scripts/seed_demo_data.py

幂等：按 source_id 去重。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

# 允许直接 `python scripts/seed_demo_data.py` 跑：把项目根目录加到 sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import structlog  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory  # noqa: E402
from app.models.raw_data import RawData, RawDataStatus  # noqa: E402

logger = structlog.get_logger(__name__)


# ── 基于公开新闻事件构造的 10 条样例 ──
# 字段映射：
#   delay_days / price_deviation / supplier_rating / historical_incidents
#   是根据公开报道中该事件的影响程度估算的演示值，不是精确财报数字。
DEMO_CASES = [
    {
        "source_id": "EVENT-2021-SUEZ-001",
        "supplier_name": "长荣海运（Evergreen）— 长赐号",
        "order_id": "PO-2021-SUEZ-001",
        "amount": 54000000.00,  # 单次堵塞约 96 小时损失约 4 亿美元货物（公开报道估算）
        "delay_days": 6,
        "price_deviation": 22.0,  # 绕航好望角增加运费
        "supplier_rating": 3.8,
        "historical_incidents": 1,
        "supplier_lat": 30.59,
        "supplier_lon": 32.27,  # 苏伊士运河
        "_note": "2021.03 长赐号堵船 6 天，全球约 12% 贸易受阻",
    },
    {
        "source_id": "EVENT-2024-TAIWAN-002",
        "supplier_name": "台积电（TSMC）新竹厂区",
        "order_id": "PO-2024-TW-002",
        "amount": 82000000.00,
        "delay_days": 3,
        "price_deviation": 8.5,
        "supplier_rating": 4.7,
        "historical_incidents": 0,
        "supplier_lat": 24.02,
        "supplier_lon": 120.61,  # 新竹科学园区
        "_note": "2024.04 花莲 7.2 级地震，台积电部分工厂预防性停机检查",
    },
    {
        "source_id": "EVENT-2022-SHANGHAI-003",
        "supplier_name": "特斯拉上海超级工厂",
        "order_id": "PO-2022-SH-003",
        "amount": 31000000.00,
        "delay_days": 22,
        "price_deviation": 15.0,
        "supplier_rating": 4.2,
        "historical_incidents": 1,
        "supplier_lat": 30.90,
        "supplier_lon": 121.70,
        "_note": "2022.03-04 上海疫情封控，特斯拉停产 22 天",
    },
    {
        "source_id": "EVENT-2021-TOYOTA-004",
        "supplier_name": "丰田汽车（Toyota）全球供应链",
        "order_id": "PO-2021-TOY-004",
        "amount": 120000000.00,
        "delay_days": 30,
        "price_deviation": 12.0,
        "supplier_rating": 4.0,
        "historical_incidents": 2,
        "supplier_lat": 35.01,
        "supplier_lon": 137.02,  # 丰田总部爱知县
        "_note": "2021.09 全球芯片短缺，丰田 14 家工厂减产约 40%",
    },
    {
        "source_id": "EVENT-2023-REDShips-005",
        "supplier_name": "地中海航运（MSC）— 红海航线",
        "order_id": "PO-2023-RS-005",
        "amount": 47000000.00,
        "delay_days": 18,
        "price_deviation": 35.0,  # 战争险保费飙升 + 绕航好望角
        "supplier_rating": 3.2,
        "historical_incidents": 3,
        "supplier_lat": 19.50,
        "supplier_lon": 37.00,  # 红海曼德海峡
        "_note": "2023.12 起胡塞武装袭击红海商船，运费翻倍、绕航好望角",
    },
    {
        "source_id": "EVENT-2020-FOXCONN-006",
        "supplier_name": "富士康（Foxconn）越南北江厂区",
        "order_id": "PO-2020-VN-006",
        "amount": 18000000.00,
        "delay_days": 14,
        "price_deviation": 10.0,
        "supplier_rating": 3.5,
        "historical_incidents": 1,
        "supplier_lat": 21.32,
        "supplier_lon": 106.10,  # 越南北江
        "_note": "2020/2021 越南疫情反复，iPhone 装配线一度限流",
    },
    {
        "source_id": "EVENT-2023-CATL-007",
        "supplier_name": "宁德时代（CATL）德国图林根工厂",
        "order_id": "PO-2023-CATL-007",
        "amount": 25000000.00,
        "delay_days": 0,
        "price_deviation": 0.8,
        "supplier_rating": 4.6,
        "historical_incidents": 0,
        "supplier_lat": 50.98,
        "supplier_lon": 11.03,  # 图林根
        "_note": "对照组：欧洲扩产顺利，低风险",
    },
    {
        "source_id": "EVENT-2022-CHIPSHORT-008",
        "supplier_name": "恩智浦半导体（NXP）荷兰厂",
        "order_id": "PO-2022-NXP-008",
        "amount": 63000000.00,
        "delay_days": 45,
        "price_deviation": 28.0,
        "supplier_rating": 3.0,
        "historical_incidents": 4,
        "supplier_lat": 51.44,
        "supplier_lon": 5.47,  # 埃因霍温
        "_note": "2021-2022 全球汽车芯片短缺，NXP 交期一度拉长到 52 周",
    },
    {
        "source_id": "EVENT-2023-UNKNOWN-009",
        "supplier_name": "某未登记供应商（数据缺失）",
        "order_id": "PO-2023-UNK-009",
        # 故意缺 amount / expected_delivery / actual_delivery
        "delay_days": None,
        "price_deviation": None,
        "supplier_rating": None,
        "historical_incidents": None,
        "_no_dates": True,
        "_note": "数据质量差：Scout 质量分 < 0.5，直接转人工补录",
    },
    {
        "source_id": "EVENT-2024-JAPAN-010",
        "supplier_name": "丰田自动织机（Toyota Industries）静冈工厂",
        "order_id": "PO-2024-JP-010",
        "amount": 14000000.00,
        "delay_days": 5,
        "price_deviation": 4.0,
        "supplier_rating": 4.3,
        "historical_incidents": 0,
        "supplier_lat": 34.98,
        "supplier_lon": 138.38,  # 静冈
        "_note": "2024.01 能登半岛 7.6 级地震，日本中部供应链短期受扰（可触发 USGS 外部情报）",
    },
]


def _make_payload(case: dict) -> dict:
    payload = {
        "order_id": case["order_id"],
        "supplier_id": case["source_id"],
        "supplier_name": case.get("supplier_name"),
        "amount": case.get("amount"),
        "delay_days": case.get("delay_days"),
        "price_deviation": case.get("price_deviation"),
        "supplier_rating": case.get("supplier_rating"),
        "historical_incidents": case.get("historical_incidents"),
        "supplier_lat": case.get("supplier_lat"),
        "supplier_lon": case.get("supplier_lon"),
    }
    if not case.get("_no_dates"):
        expected = datetime.now() - timedelta(days=max(case.get("delay_days") or 0, 0) + 2)
        actual = expected + timedelta(days=case.get("delay_days") or 0)
        payload["expected_delivery"] = expected.date().isoformat()
        payload["actual_delivery"] = actual.date().isoformat()
    return {k: v for k, v in payload.items() if v is not None}


async def seed() -> None:
    factory = get_session_factory()
    inserted = 0
    skipped = 0
    async with factory() as session:
        for case in DEMO_CASES:
            existing = await session.execute(
                select(RawData).where(RawData.source_id == case["source_id"])
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            payload = _make_payload(case)
            payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            data_hash = hashlib.sha256(payload_str.encode()).hexdigest()

            row = RawData(
                source_type="public_event_seed",
                source_id=case["source_id"],
                payload=payload,
                data_hash=data_hash,
                status=RawDataStatus.PENDING,
                quality_score=None,
            )
            session.add(row)
            inserted += 1
            logger.info("seed.inserted", source_id=case["source_id"], note=case.get("_note"))

        await session.commit()

    print(f"✅ 真实事件种子数据写入完成：新增 {inserted} 条，跳过已存在 {skipped} 条。")
    print("   数据来源：2020-2024 年公开新闻报道的供应链事件（仅作演示，金额为公开报道估算值）。")
    print("   触发分析：POST /api/v1/risk/analyze，body 传 raw_data_id 或 source_id。")


if __name__ == "__main__":
    asyncio.run(seed())
