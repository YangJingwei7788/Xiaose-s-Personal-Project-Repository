# 萧瑟喵AI工作台（codex+deepseek辅助开发）

基于 **FastAPI + SQLAlchemy（异步）** 构建的轻量 AI 对话全栈应用，支持多用户、流式对话、会话角色设定、收藏与历史，并可自由接入多种大模型来源（公共 API / 本地大模型 / DeepSeek）。原生 HTML/CSS/JS 前端，已做移动端适配。

##  功能介绍

### 1. 账号体系
- **注册 / 登录弹窗**：进入即可先体验（游客模式），需要使用时右上角点「登录」弹出登录/注册窗口，注册后自动切换到登录。
- **JWT 鉴权**：登录发放 7 天有效的令牌，密码使用 bcrypt 加密存储。
- **用户管理独立页（/user）**：更换头像、修改昵称、修改密码。
- **修改密码安全策略**：改密成功后自动退出当前登录，弹窗提示「密码已修改，请重新登录」。
- **密码明文预览**：输入框右侧带 👁 显示/隐藏开关（不再依赖浏览器原生图标，稳定可用），并阻止浏览器自动填充。

### 2. 对话工作台（/）
- **流式对话**：SSE 流式输出，逐字显示 AI 回复；Ctrl+Enter 快捷发送。
- **本次登录会话**：左侧「对话」列表只显示本次登录新建的会话，登录即开始全新工作区。
- **角色设定**：每个会话可点 ⚙ 设置「角色」（如：你是一位资深的 Python 工程师…），该设定会作为 system 指令随每次提问发送给 AI，随会话保存在数据库，可随时修改/清除。
- **收藏 / 历史**：对话可收藏、打开过的对话自动记入浏览历史；两者都支持**重命名**、删除与清空，长期保留。

### 3. 多来源大模型接入（设置页 /settings → API设置）
| 来源 | 说明 |
| --- | --- |
| 公共 API | 服务器自带的 Ollama（默认模型见 .env `OLLAMA_MODEL`），所有用户可选 |
| 本地大模型 | 填写本地/局域网 Ollama 地址（如 http://192.168.1.10:11434），会话**直接调用该地址**，不经过服务器公共 API |
| DeepSeek | 官方 API，可选 `deepseek-v4-pro` / `deepseek-v4-flash` 模型；输入 API Key 时弹窗询问**是否保存到账号数据库**（不保存则仅当前浏览器会话有效，重新登录自动消失） |

- 设置保存后即为该用户的默认来源。
- 聊天输入框右侧显示**当前使用的模型预览**，点击弹出来源菜单，随时切换；DeepSeek 等多模型来源旁有 **▲** 可进一步选择具体模型。

### 4. 缓存与降级
- Redis 缓存对话详情/列表/上下文/登录令牌等（缓存失效策略），Redis 不可用时**自动降级直查数据库**，不影响业务。

### 5. 移动端适配
- 屏幕宽度 ≤768px 自动切换为「列表屏 / 聊天屏」两屏布局，弹窗、设置页、用户页均有手机端适配。

## 🛠技术栈

- 后端框架：FastAPI + Uvicorn
- 数据库：MySQL 8（异步驱动 aiomysql）
- ORM：SQLAlchemy 2.x（异步）
- 缓存：Redis（redis-py asyncio，可关闭）
- 鉴权：PyJWT；密码：passlib + bcrypt
- AI 调用：Ollama `/api/chat`（NDJSON 流式）与 DeepSeek OpenAI 兼容接口（SSE 流式）
- 前端：原生 HTML/CSS/JS（无构建步骤）

##  快速开始

### 1. 环境要求
- Python ≥ 3.11
- MySQL 8.x（本机或远程）
- Redis 6.x（可选，`REDIS_ENABLED=false` 可关闭）
- Ollama（使用公共 API / 本地大模型时需要）

### 2. 安装依赖
```bash
uv sync
```

### 3. 配置
复制 `.env.example`（或参考下表）为 `.env` 并修改：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `mysql+aiomysql://root:123456@localhost:3306/xiaosemiao_ai` | MySQL 异步连接串 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `REDIS_ENABLED` | `false` | 是否启用 Redis 缓存（关掉则直查数据库） |
| `JWT_SECRET` | 内置默认值 | 生产环境务必改成随机字符串 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | 公共 API（服务器 Ollama）地址 |
| `OLLAMA_MODEL` | `deepseek-r1:8b` | 公共 API 默认模型 |
| `CONTEXT_MESSAGE_COUNT` | `20` | 发送给模型的上下文消息条数（最近 N 条） |

### 4. 初始化数据库
```bash
mysql -uroot -p < scripts/init_db.sql
```
表结构会在应用启动时通过 `Base.metadata.create_all` 自动创建（并对旧库做字段增量迁移）。

### 5. 启动服务
```bash
uv run uvicorn xiaosemiao_ai.main:app --reload --port 8000
```
- 工作台：http://127.0.0.1:8000/
- 用户管理：http://127.0.0.1:8000/user
- 设置：http://127.0.0.1:8000/settings
- 接口文档（Swagger）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

### 6. 运行测试（无需 MySQL / Redis）
```bash
uv run pytest
```

##  API 一览

统一响应格式：`{ "code": 0, "message": "success", "data": ... }`；鉴权请求头：`Authorization: <token>`。

### 用户 `/api/user`
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | /api/user/register | 注册 |
| POST | /api/user/login | 登录，返回 JWT |
| GET | /api/user/info | 当前用户信息 |
| PUT | /api/user/update | 修改昵称/头像 |
| PUT | /api/user/password | 修改密码 |
| POST | /api/user/avatar | 上传头像（自动替换旧图） |
| POST | /api/user/logout | 登出，令牌失效 |
| GET | /api/user/settings/llm | 获取我的大模型设置 |
| PUT | /api/user/settings/llm | 保存大模型设置（公共/本地/DeepSeek） |

### 对话 `/api/chat`
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | /api/chat/create | 新建空白会话 |
| GET | /api/chat/list | 分页会话列表 |
| GET | /api/chat/detail | 会话详情（含 system_prompt 与消息） |
| POST | /api/chat/send | 发送提问（SSE 流式返回；可选 provider/base_url/api_key/model） |
| PUT | /api/chat/title | 修改标题 |
| PUT | /api/chat/role | 修改角色设定（system_prompt） |
| DELETE | /api/chat/delete | 删除会话 |
| DELETE | /api/chat/clear | 清空全部会话 |

### 收藏 `/api/favorite` 与历史 `/api/history`
支持 add / list / remove / clear / check（收藏）等接口，列表返回 `ChatListItem`（id 即会话 ID，可复用重命名/删除）。

##  项目结构

```
xiaosemiao_ai/
├── main.py           # 应用入口与页面路由（/ /user /settings）
├── config/           # settings(.env) / db_conf(MySQL) / cache_conf(Redis 缓存)
├── models/           # ORM 模型：user/user_token/chat/chat_message/favorite/history
├── schemas/          # Pydantic 校验模型
├── crud/             # 数据访问层
├── routers/          # API：user/chat/favorite/history + deps(鉴权依赖)
├── utils/            # security(密码/JWT) / llm_client(公共/本地/DeepSeek) / common
└── html/             # index.html(工作台) / user.html(用户管理) / settings.html(设置)
scripts/init_db.sql   # 建库 SQL
tests/                # pytest（SQLite 内存库 + 假模型流）
```

##  常见问题

- **启动报数据库连接失败**：确认 MySQL 已启动、已执行 `scripts/init_db.sql`、`.env` 连接串正确。
- **对话没反应 / 模型调用失败**：确认你选择的来源可用——公共 API 需服务器 Ollama 已启动并拉取了 `OLLAMA_MODEL`；本地大模型需地址可达；DeepSeek 需有效 API Key。
- **修改 .env 后需重启服务生效。**
