# RootLink Frontend

RootLink 的静态前端，包括官网、寻根 Agent 页面和 Vercel 兼容代理。

## 目录

```text
frontend/
├── public/
│   ├── index.html
│   ├── agent.html
│   └── images/
├── api/                 # 兼容旧地址的 Vercel 代理
├── .env.example
└── vercel.json
```

`agent.html` 会直接请求 RootLink FastAPI：

- 本地页面运行在 localhost 时：`http://localhost:8000`
- 生产环境：`https://api.getrootlink.com`
- 临时覆盖：在页面加载前设置 `window.ROOTLINK_API_BASE_URL`

## 本地预览

先启动根目录下的后端，然后在本目录运行：

```bash
python -m http.server 5500 -d public
```

访问 `http://localhost:5500`。后端的 `FRONTEND_ORIGINS` 需要包含该地址。

## Vercel

以 `frontend/` 作为 Vercel Root Directory。旧的 `/api/chat`、`/api/save`
和 `/api/load` 路径会代理到 `BACKEND_API_URL`，新页面则直接访问 FastAPI。

前端只包含 Supabase publishable key。不要在此目录或 Vercel 前端变量中放置
`SUPABASE_SERVICE_KEY`、Ark API key 等服务端密钥。
