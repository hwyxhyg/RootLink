# RootLink

RootLink 是一个面向海外华人的智能寻根项目。用户可以用中文或英文描述姓氏、
祖籍、方言、迁徙路线和家族线索，系统通过 LangChain / LangGraph Agent 整理
信息、生成寻根行动清单，并结合公开资料与中间人数据提供下一步建议。

## 系统架构

```text
Browser
   |
   v
Static frontend (getrootlink.com)
   |
   v
FastAPI backend (api.getrootlink.com)
   |
   +--> LangChain / LangGraph
   |        |
   |        v
   |    Volcengine Ark API
   |
   +--> Supabase Auth / archives / PostgreSQL memory
```

前端与 Agent 后端已经完全脱离 Coze，可部署到普通 Linux 服务器。

## 仓库结构

```text
rootlink/
├── frontend/
│   ├── public/          # index.html、agent.html、图片资源
│   ├── api/             # Vercel 兼容代理
│   └── vercel.json
├── backend/
│   ├── assets/          # 中间人等本地数据
│   ├── config/          # 中英文 Agent 配置
│   ├── docs/            # SSE 接入说明
│   ├── scripts/         # 安装和启动脚本
│   ├── src/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── storage/
│   │   ├── tools/
│   │   └── utils/
│   ├── tests/
│   ├── .env.example
│   ├── DEPLOY.md
│   └── requirements.txt
├── .gitignore
└── README.md
```

## 主要功能

- 中文、英文双语寻根 Agent
- SSE 流式回复与结构化 JSON 输出
- 中英文独立会话记忆，避免语言串线
- Supabase 登录、云端存档和读取
- PostgreSQL 持久化 LangGraph memory
- 祖籍地资料搜索、权威资料检索和中间人匹配
- 前端档案导入、导出与行动清单

## 快速开始

推荐使用 Python 3.11 或 3.12。

```bash
cd backend
python3 -m venv .venv
```

Linux / macOS：

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `backend/.env`，至少配置：

```dotenv
VOLCENGINE_API_KEY=
VOLCENGINE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
PGDATABASE_URL=
FRONTEND_ORIGINS=http://localhost:5500
```

启动后端：

```bash
uvicorn src.api.chat_sse:app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://localhost:8000/health
```

启动前端静态服务器：

```bash
cd ../frontend
python -m http.server 5500 -d public
```

浏览器打开 `http://localhost:5500`。

## API

流式聊天：

```http
POST /api/chat/sse
Content-Type: application/json
```

```json
{
  "user_id": "sess_example",
  "message": "My family is from Anxi. Where should I begin?",
  "lang": "en"
}
```

其他接口：

- `POST /api/chat/json`：非流式备用接口
- `POST /api/archive/save`：保存登录用户档案
- `POST /api/archive/load`：读取登录用户档案
- `GET /health`：服务健康检查

归档接口需要 Supabase access token：

```http
Authorization: Bearer <supabase_access_token>
```

## 测试

```bash
cd backend
pytest -q
```

测试覆盖健康检查、中英文选择、非法语言回退、thread memory 隔离、SSE 格式
和 Supabase 归档接口契约。

## 部署

- 前端：推荐部署到 Vercel，Root Directory 设置为 `frontend`
- 后端：部署到 Linux 服务器，通过 systemd 运行 Uvicorn
- 反向代理：使用 Nginx 或 Caddy，将 `api.getrootlink.com` 转发到
  `127.0.0.1:8000`
- HTTPS：使用 Certbot 或 Caddy 自动签发证书

完整服务器配置见 [backend/DEPLOY.md](backend/DEPLOY.md)。

## 安全

- 不要提交任何真实 `.env` 文件
- Ark API key 与 Supabase service key 只能保存在后端
- 前端只能使用 Supabase publishable / anon key
- 生产环境不要直接暴露 Uvicorn 的 8000 端口
- 曾经写入源码的密钥必须在对应平台撤销并重新生成
