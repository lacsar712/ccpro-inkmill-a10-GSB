from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import and_, func

from app.database import SessionLocal
from app.models.grind_pass import GrindPass
from app.models.mill import Mill
from app.utils import dt_to_json, error

bp = Blueprint("utilization", __name__, url_prefix="/api/utilization")

# 理论满负荷简化口径:每台研磨机每天 1 班 × 8 小时
SHIFT_HOURS_PER_DAY = 8
MIN_DAYS, MAX_DAYS, DEFAULT_DAYS = 1, 90, 7


def _parse_days(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return DEFAULT_DAYS
    try:
        days = int(raw)
    except ValueError:
        return None
    if not MIN_DAYS <= days <= MAX_DAYS:
        return None
    return days


def _parse_mill_id(raw: str | None) -> int | None:
    """返回 None 表示不过滤;-1 表示参数非法。"""
    if raw is None or raw == "":
        return None
    try:
        mill_id = int(raw)
    except ValueError:
        return -1
    return mill_id if mill_id > 0 else -1


@bp.get("")
@jwt_required()
def utilization():
    days = _parse_days(request.args.get("days"))
    if days is None:
        return error(f"days 必须是 {MIN_DAYS}~{MAX_DAYS} 之间的整数", 400)

    mill_id = _parse_mill_id(request.args.get("millId"))
    if mill_id == -1:
        return error("millId 必须是正整数", 400)

    now = datetime.now()
    since = now - timedelta(days=days)
    full_load_minutes = days * SHIFT_HOURS_PER_DAY * 60

    db = SessionLocal()
    try:
        q = (
            db.query(
                Mill.id,
                Mill.mill_code,
                Mill.workshop_id,
                func.count(GrindPass.id),
                func.coalesce(func.sum(GrindPass.duration_min), 0),
            )
            .outerjoin(
                GrindPass,
                and_(
                    GrindPass.mill_id == Mill.id,
                    GrindPass.started_at >= since,
                ),
            )
            .group_by(Mill.id, Mill.mill_code, Mill.workshop_id)
            .order_by(Mill.id)
        )
        if mill_id is not None:
            q = q.filter(Mill.id == mill_id)

        items = []
        for row_id, mill_code, workshop_id, pass_count, total_minutes in q.all():
            total = round(float(total_minutes), 2)
            ratio = min(1.0, total / full_load_minutes) if full_load_minutes else 0.0
            items.append(
                {
                    "millId": row_id,
                    "millCode": mill_code,
                    "workshopId": workshop_id,
                    "passCount": int(pass_count),
                    "totalMinutes": total,
                    "utilizationRatio": round(ratio, 4),
                }
            )

        return jsonify(
            {
                "days": days,
                "windowStart": dt_to_json(since),
                "windowEnd": dt_to_json(now),
                "shiftHoursPerDay": SHIFT_HOURS_PER_DAY,
                "fullLoadMinutesPerMill": full_load_minutes,
                "items": items,
            }
        )
    finally:
        db.close()
