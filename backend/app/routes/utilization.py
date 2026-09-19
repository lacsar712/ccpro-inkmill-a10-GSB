from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.grind_pass import GrindPass
from app.models.mill import Mill
from app.utils import error

bp = Blueprint("utilization", __name__, url_prefix="/api")

# 理论满负荷口径：每机每个工作日 8 小时
WORK_HOURS_PER_DAY = 8
THEORETICAL_MINUTES_PER_DAY = WORK_HOURS_PER_DAY * 60


@bp.get("/utilization")
@jwt_required()
def utilization():
    # 窗口天数：默认 7，限定 1~365
    try:
        days = int(request.args.get("days", 7))
    except (TypeError, ValueError):
        return error("days 必须是 1~365 之间的整数", 400)
    if not 1 <= days <= 365:
        return error("days 必须是 1~365 之间的整数", 400)

    # 可选 millId 过滤
    mill_id = None
    raw_mill = request.args.get("millId")
    if raw_mill not in (None, ""):
        try:
            mill_id = int(raw_mill)
        except (TypeError, ValueError):
            return error("millId 无效", 400)
        if mill_id <= 0:
            return error("millId 无效", 400)

    db = SessionLocal()
    try:
        if mill_id is not None and not db.get(Mill, mill_id):
            return error("研磨机不存在", 404)

        since = datetime.now() - timedelta(days=days)
        theoretical = float(days * THEORETICAL_MINUTES_PER_DAY)

        # 窗口内按机台聚合研磨遍次（读库聚合，不在前端造数）
        agg = (
            select(
                GrindPass.mill_id.label("mill_id"),
                func.coalesce(func.sum(GrindPass.duration_min), 0).label("total_min"),
                func.count(GrindPass.id).label("pass_count"),
            )
            .where(GrindPass.started_at >= since)
            .group_by(GrindPass.mill_id)
        )
        if mill_id is not None:
            agg = agg.where(GrindPass.mill_id == mill_id)
        agg_subq = agg.subquery()

        stmt = select(
            Mill,
            func.coalesce(agg_subq.c.total_min, 0),
            func.coalesce(agg_subq.c.pass_count, 0),
        ).outerjoin(agg_subq, Mill.id == agg_subq.c.mill_id)
        if mill_id is not None:
            stmt = stmt.where(Mill.id == mill_id)
        stmt = stmt.order_by(Mill.id)

        rows = db.execute(stmt).all()

        items = []
        for mill, total_min, pass_count in rows:
            total_minutes = float(total_min or Decimal("0"))
            ratio = total_minutes / theoretical if theoretical > 0 else 0.0
            items.append(
                {
                    "millId": mill.id,
                    "millCode": mill.mill_code,
                    "workshopId": mill.workshop_id,
                    "totalMinutes": round(total_minutes, 2),
                    "passCount": int(pass_count or 0),
                    "utilizationRatio": round(min(1.0, ratio), 4),
                }
            )

        return jsonify(
            {
                "days": days,
                "theoreticalMinutesPerMill": theoretical,
                "items": items,
            }
        )
    finally:
        db.close()
