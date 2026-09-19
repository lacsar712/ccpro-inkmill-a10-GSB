# InkMill-01 · 油墨研磨台账

面向印刷油墨研磨车间的**研磨机状态、粘度取样与研磨遍次**台账系统。  
**不是**库存、电商或 CMS 场景。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11、Flask、SQLAlchemy、PyMySQL、Flask-JWT-Extended、passlib/bcrypt、gunicorn |
| 前端 | Svelte 4、Vite、TypeScript |
| 数据库 | MySQL 8 |

## 端口与数据库

| 服务 | 宿主机端口 |
|------|------------|
| 统一入口 (Nginx) | **4200** |
| 后端 API | **9200** |
| MySQL | **3312** |

MySQL 连接：`inkmill` / `inkmill` / `inkmill`（库名/用户/密码）

## 演示账号

密码均为 **123456**：

- `admin` — 管理员
- `grinder` — 研磨工

## 领域实体（JSON 驼峰）

1. **Workshop**：`name`, `site`, `notes`
2. **Mill**：`workshopId`, `millCode`（同车间唯一）, `pigmentBase`, `bowlLiters`, `status`（`grinding` \| `idle` \| `wash`）
3. **ViscositySample**：`millId`, `sampledAt`, `viscosityPaS`（须 &gt; 0，否则 HTTP 400）, `tempC`, `notes`
4. **GrindPass**：`millId`, `startedAt`, `passNo`（≥ 1）, `durationMin`（&gt; 0）, `mediaType`, `operatorName`
5. **Dashboard**：`workshopTotal`, `grindingMillCount`, `samplesLast24h`, `passesLast7d`
6. **Utilization**：`days`, `windowStart`, `windowEnd`, `shiftHoursPerDay`, `fullLoadMinutesPerMill`, `items[]`（`millId`, `millCode`, `workshopId`, `passCount`, `totalMinutes`, `utilizationRatio`）

## 利用率看板（GET /api/utilization）

按 `GrindPass.durationMin` 在数据库内聚合（`SUM` / `COUNT`），前端只渲染接口结果，不自行估算分钟数。

**查询参数**

| 参数 | 默认 | 说明 |
|------|------|------|
| `days` | `7` | 统计窗口天数，整数，范围 1~90，越界返回 400 |
| `millId` | （空） | 可选，只统计指定研磨机 |

**口径**

- 窗口：`startedAt ≥ now - days 天`（含边界），响应中的 `windowStart` / `windowEnd` 为实际窗口。
- `totalMinutes`：窗口内该机全部遍次 `durationMin` 之和（数据库 `SUM`，无遍次为 0）。
- `passCount`：窗口内遍次数（数据库 `COUNT`）。
- 理论满负荷简化为**每机每天 1 班 × 8 小时**：`fullLoadMinutesPerMill = days × 8 × 60`。
- `utilizationRatio = min(1, totalMinutes / fullLoadMinutesPerMill)`，保留 4 位小数，封顶 1（即 100%）。
- 无遍次的机台也会出现在 `items` 中（`totalMinutes = 0`，`utilizationRatio = 0`）。

示例：`GET /api/utilization?days=14&millId=2`

前端「利用率」页提供近 7 / 14 / 30 天窗口切换与单机筛选，表格 + 条形展示。

## 快速启动（Docker）

```bash
cd InkMill-01
docker compose up --build -d
```

浏览器访问：**http://localhost:4200**  
前端 Nginx 将 `/api/` 反向代理到后端 `9200`。

后端容器启动流程：

1. 等待 MySQL 就绪（`DB_HOST=mysql`）
2. SQLAlchemy `create_all` 建表
3. `SEED_ON_START=true` 时写入演示数据（含近 7 日各机台研磨遍次，供利用率看板聚合）
4. gunicorn 监听 `0.0.0.0:9200`

健康检查：`GET /api/health` → `{"status":"ok","service":"InkMill"}`

## 本地开发（可选）

**后端**（需本机 MySQL 或连 Docker 的 3312 端口）：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set DB_HOST=127.0.0.1
set DB_PORT=3312
set DB_USER=inkmill
set DB_PASSWORD=inkmill
set DB_NAME=inkmill
set JWT_SECRET=inkmill-jwt-secret-change-me
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
gunicorn wsgi:app --bind 127.0.0.1:9200 --reload
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

Vite 开发服务器端口 **4200**，`/api` 代理到 `127.0.0.1:9200`。

## 目录结构

```
InkMill-01/
├── docker-compose.yml
├── nginx/nginx.conf          # 4200 统一入口，/api → backend
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── wsgi.py
│   └── app/                  # Flask 路由、模型与种子数据
└── frontend/
    ├── Dockerfile
    ├── vite.config.ts
    └── src/routes/           # Login / Dashboard / CRUD 页面
```

## UI 主题

墨黑底 + 朱砂强调色，无紫色光晕风格。
