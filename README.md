# 臆想创作

臆想创作是一个面向长篇小说创作的本地优先 AI 工作台。第一版目标是跑通：

```text
项目配置 -> 世界观/角色/组织/伏笔管理 -> 章节生成 -> 章节分析 -> 记忆沉淀
```

## 技术栈

```text
前端：Vue 3 + TypeScript + Vite + Naive UI + Pinia
后端：FastAPI
数据库：SQLite
模型接口：OpenAI-compatible
```

## 目录

```text
frontend/   前端工作台
backend/    后端 API 与 Agent 编排
prompts/    Agent 提示词模板
```

## 启动方式

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

打开前端地址后，在“API 配置”里填写支持 OpenAI-compatible 的服务地址、模型名和 API Key。
