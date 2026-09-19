from datetime import datetime, timedelta
from decimal import Decimal

from app.auth import hash_password
from app.database import SessionLocal
from app.models.grind_pass import GrindPass
from app.models.mill import Mill
from app.models.user import User
from app.models.viscosity_sample import ViscositySample
from app.models.workshop import Workshop


def _pass(now, mill_id, days_ago, hours_ago, pass_no, duration, media, operator):
    return GrindPass(
        mill_id=mill_id,
        started_at=now - timedelta(days=days_ago, hours=hours_ago),
        pass_no=pass_no,
        duration_min=Decimal(str(duration)),
        media_type=media,
        operator_name=operator,
    )


def _recent_passes(now, mills):
    """构造近 7 日研磨遍次：按天铺开，保证利用率看板有足够数据读库聚合。"""
    by_code = {m.mill_code: m.id for m in mills}
    m1, m2, m3 = by_code["M-01"], by_code["M-02"], by_code["M-A1"]

    passes = []

    # M-01：满负荷主力线，每天 2 遍
    m1_durations = [
        (75, 50),
        (95, 70),
        (120, 90),
        (60, 45),
        (140, 80),
        (85, 65),
        (110, 75),
    ]
    pn = 0
    for days_ago, (d1, d2) in enumerate(m1_durations):
        pn += 1
        passes.append(_pass(now, m1, days_ago, 9, pn, d1, "0.8mm 锆珠", "张研磨"))
        pn += 1
        passes.append(_pass(now, m1, days_ago, 4, pn, d2, "0.8mm 锆珠", "张研磨"))

    # M-02：间歇生产，隔日 1 遍
    for i, (days_ago, hours_ago, dur) in enumerate(
        [(1, 4, 90), (3, 6, 120), (5, 5, 75)], start=1
    ):
        passes.append(_pass(now, m2, days_ago, hours_ago, i, dur, "1.0mm 玻璃珠", "李工"))

    # M-A1：少量试产
    for i, (days_ago, hours_ago, dur) in enumerate(
        [(2, 3, 60), (6, 7, 45)], start=1
    ):
        passes.append(_pass(now, m3, days_ago, hours_ago, i, dur, "1.2mm 锆珠", "赵工"))

    return passes


def seed() -> None:
    db = SessionLocal()
    try:
        for username, display_name, role in [
            ("admin", "系统管理员", "admin"),
            ("grinder", "研磨工", "grinder"),
        ]:
            if not db.query(User).filter(User.username == username).first():
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password("123456"),
                        display_name=display_name,
                        role=role,
                    )
                )
        db.commit()

        fresh = db.query(Workshop).count() == 0
        now = datetime.now()

        if fresh:
            w1 = Workshop(name="一号油墨车间", site="厂区 A 栋", notes="高固含色浆线")
            w2 = Workshop(name="调墨中心", site="厂区 B 栋", notes="小批量专色")
            db.add_all([w1, w2])
            db.flush()

            m1 = Mill(
                workshop_id=w1.id,
                mill_code="M-01",
                pigment_base="酞菁蓝载体",
                bowl_liters=Decimal("25.00"),
                status="grinding",
            )
            m2 = Mill(
                workshop_id=w1.id,
                mill_code="M-02",
                pigment_base="炭黑载体",
                bowl_liters=Decimal("18.50"),
                status="idle",
            )
            m3 = Mill(
                workshop_id=w2.id,
                mill_code="M-A1",
                pigment_base="专色红载体",
                bowl_liters=Decimal("12.00"),
                status="wash",
            )
            db.add_all([m1, m2, m3])
            db.flush()

            db.add_all(
                [
                    ViscositySample(
                        mill_id=m1.id,
                        sampled_at=now - timedelta(hours=2),
                        viscosity_pa_s=Decimal("12.5000"),
                        temp_c=Decimal("28.50"),
                        notes="首检合格",
                    ),
                    ViscositySample(
                        mill_id=m1.id,
                        sampled_at=now - timedelta(minutes=30),
                        viscosity_pa_s=Decimal("9.8000"),
                        temp_c=Decimal("29.00"),
                        notes="二检微调",
                    ),
                    ViscositySample(
                        mill_id=m2.id,
                        sampled_at=now - timedelta(days=1),
                        viscosity_pa_s=Decimal("15.2000"),
                        temp_c=Decimal("27.00"),
                        notes=None,
                    ),
                ]
            )
            print("Seed workshops / mills / samples inserted.")

        # 近 7 日遍次幂等补齐：仅当窗口内完全没有遍次时写入，
        # 这样旧库重新 seed 也能保证利用率看板有数据，且不重复造数。
        mills = db.query(Mill).order_by(Mill.id).all()
        week_ago = now - timedelta(days=7)
        recent_count = (
            db.query(GrindPass)
            .filter(GrindPass.started_at >= week_ago)
            .count()
        )
        if mills and recent_count == 0:
            db.add_all(_recent_passes(now, mills))
            print("Recent 7-day grind passes inserted.")

        db.commit()
        if not fresh and recent_count != 0:
            print("Seed skipped (data already present).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
