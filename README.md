# 臆想创作

臆想创作是面向长篇小说创作的本地优先工作台，用于整理项目设定、规划章节、生成和修改正文，并追踪设定随剧情的变化。

```text
项目配置 → 世界观与大纲 → 人物、组织和伏笔 → 章节创作 → 分析与记忆沉淀
```

## 功能概览

### 项目设定与资料管理

- **项目配置、世界观设定和大纲管理**：维护小说背景、规则和章节计划；卷与章节大纲可以调整顺序。
- **人物卡片与人物关系**：整理人物身份、性格、经历、关系和成长信息。
- **组织势力**：记录组织结构、层级、资源、成员及阵营关系。
- **伏笔看板**：按状态跟踪线索，从埋设到发展、回收或废弃。

### 章节生成工作台

- 按已保存的大纲顺序确定新章节，不把新稿误写到已存在正文的旧章节。
- 提供快速写作、智能模式和深度创作等工作流，并可配置风格、节奏、目标字数和上下文资料。
- 自动保存章节草稿；刷新或重新进入时可以继续编辑。
- 支持按章节保存对话改稿会话，可对整章或选中的连续片段提出修改；候选稿由作者确认后再应用。
- 章节生成后可查看分析、审阅设定变化提案、比较和恢复历史版本，并查看运行步骤与用量记录。
- 写作偏好可按项目保存，编辑器字号作为个人设置保存。

### 长期记忆与设定共创

- 长期记忆中心汇总章节摘要和已沉淀的设定资料。
- 设定共创 Agent 可围绕人物、世界观等资料进行对话，辅助补齐结构化设定。

### 系统管理

提供 API 配置、用户、菜单、字典和系统配置等管理页面。

## 技术栈

```text
前端：Vue 3、TypeScript、Vite、Naive UI、Pinia
后端：Python、FastAPI、SQLAlchemy
默认数据库：SQLite（核心库与创作业务库分开）
模型接口：OpenAI-compatible API
```

## 环境要求

- Python 3.10 或更高版本（建议使用 Python 3.11）
- Node.js 18 或更高版本及 npm

## 本地启动

第一次运行时，在项目根目录打开两个 PowerShell 终端。

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

后端启动时会自动检查并运行数据库迁移。

### 2. 启动前端

在另一个终端中执行：

```powershell
cd frontend
npm install
npm run dev
```

访问 <http://127.0.0.1:5173>。开发服务器会把 `/backend-api/*` 请求转发到本机 `8001` 端口的 FastAPI 服务。

首次使用时，进入 **API 配置**，填写 OpenAI-compatible 服务的 API 地址、模型名称和 API Key。完成配置后即可在项目中使用模型功能。

## 数据与备份

默认情况下，数据保存在 `backend/data/`：

| 路径 | 内容 |
| --- | --- |
| `backend/data/core.db` | 用户、菜单、字典及系统配置等核心数据 |
| `backend/data/yixiang.db` | 项目、章节、人物、组织、伏笔、记忆和工作流记录等创作数据 |
| `backend/data/versions/` | 章节历史版本的正文快照 |

需要备份或迁移本地项目时，先停止后端服务，再复制整个 `backend/data/` 目录。该目录可能包含小说正文、项目设定和模型配置，请勿提交到公开代码仓库。

## 开发与检查

在 `frontend/` 目录运行生产构建和前端类型检查：

```powershell
npm run build
```

在已激活后端虚拟环境的 `backend/` 目录运行后端回归测试：

```powershell
python -m unittest discover -s tests
```

后端接口文档地址：<http://127.0.0.1:8001/docs>

服务健康检查地址：<http://127.0.0.1:8001/api/health>

## 项目结构

```text
backend/
  app/api/                 FastAPI 路由与接口
  app/agents/              Agent 能力与提示词调用
  app/agents_v3/           章节生成工作流、运行状态和版本持久化
  app/db/migrations/       核心库和业务库迁移
  app/memory/              记忆存取与上下文检索
  app/models/              数据模型
  data/                    本地数据库和章节版本文件
  tests/                   后端回归测试
frontend/
  src/api/                 前端 API 客户端
  src/components/          可复用页面组件
  src/components/chapter-generation/
                           章节生成工作台各功能面板
  src/pages/               页面与主要流程编排
docs/                      设计和开发计划
prompts/                   Agent 提示词模板
```

章节生成工作台的产品规则、阶段计划与验收记录见[开发计划](docs/章节生成工作台优化开发计划.md)。
