from datetime import datetime, timedelta
from decimal import Decimal

from app.auth import hash_password
from app.database import SessionLocal
from app.models.grind_pass import GrindPass
from app.models.mill import Mill
from app.models.user import User
from app.models.viscosity_sample import ViscositySample
from app.models.workshop import Workshop


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

        if db.query(Workshop).count() == 0:
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

            now = datetime.now()
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

            # 近 7 日研磨遍次:每台机都有数据,利用率看板可直接聚合
            pass_specs = [
                # (mill, 几天前, 再提前几小时, 遍次, 分钟, 介质, 操作员)
                (m1, 0, 3, 1, "45.00", "0.8mm 锆珠", "张研磨"),
                (m1, 0, 2, 2, "38.00", "0.8mm 锆珠", "张研磨"),
                (m1, 1, 5, 1, "52.00", "0.8mm 锆珠", "张研磨"),
                (m1, 1, 4, 2, "47.50", "0.8mm 锆珠", "李工"),
                (m1, 2, 6, 1, "60.00", "0.6mm 锆珠", "张研磨"),
                (m1, 3, 3, 1, "41.00", "0.8mm 锆珠", "王师傅"),
                (m1, 4, 5, 1, "55.00", "0.8mm 锆珠", "张研磨"),
                (m1, 6, 4, 1, "36.00", "1.0mm 锆珠", "李工"),
                (m2, 1, 4, 1, "60.00", "1.0mm 玻璃珠", "李工"),
                (m2, 2, 3, 1, "75.00", "1.0mm 玻璃珠", "李工"),
                (m2, 4, 6, 1, "30.00", "0.8mm 玻璃珠", "王师傅"),
                (m2, 5, 2, 1, "60.00", "1.0mm 玻璃珠", "李工"),
                (m2, 6, 5, 1, "48.00", "1.0mm 玻璃珠", "张研磨"),
                (m3, 2, 4, 1, "25.00", "0.6mm 锆珠", "王师傅"),
                (m3, 5, 3, 1, "30.00", "0.6mm 锆珠", "王师傅"),
            ]
            db.add_all(
                [
                    GrindPass(
                        mill_id=mill.id,
                        started_at=now - timedelta(days=days_ago, hours=hours_ago),
                        pass_no=pass_no,
                        duration_min=Decimal(minutes),
                        media_type=media,
                        operator_name=operator,
                    )
                    for mill, days_ago, hours_ago, pass_no, minutes, media, operator in pass_specs
                ]
            )
            db.commit()
            print("Seed data inserted.")
        else:
            print("Seed skipped (workshops exist).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
