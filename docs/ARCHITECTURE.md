# 系统架构：书荒雷达

**Version**: V0.1
**Date**: 2026-07-03

---

## 1. 架构总览

```
┌─────────────┐     HTTP      ┌──────────────┐     SQL     ┌──────────┐
│   Browser   │ ◄──────────► │  Node.js     │ ◄─────────► │  SQLite  │
│  (Frontend) │              │  HTTP Server │             │  (data/) │
└─────────────┘              └──────────────┘             └──────────┘
                                    │
                                    │ future
                                    ▼
                             ┌──────────────┐
                             │   Crawler    │
                             │  (crawler/)  │
                             └──────────────┘
```

---

## 2. 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | 原生 HTML / CSS / JavaScript | 无框架依赖 |
| 后端 | Node.js (≥24) 原生 HTTP | 无 Express/Koa 依赖 |
| 数据库 | SQLite（`node:sqlite`） | Node.js 内置模块 |
| 部署 | 本地运行 | 端口 5173 |

---

## 3. 项目结构

```
novel-search-ai/
├── frontend/              # 前端静态文件
│   ├── index.html         # 主页面 + 模板
│   ├── app.js             # 前端逻辑（搜索/渲染/导入）
│   └── styles.css         # 样式
├── backend/               # 后端服务
│   ├── server.js          # HTTP 服务器 + API + 数据库
│   └── package.json       # 项目配置
├── crawler/               # 爬虫模块（开发中）
├── data/                  # 数据库文件（gitignored）
│   └── novels.sqlite
├── docs/                  # 项目文档
│   ├── PRD.md
│   ├── TAG_SYSTEM.md
│   ├── DATABASE.md
│   ├── SEARCH_ENGINE.md
│   ├── DATA_PIPELINE.md
│   └── ARCHITECTURE.md
├── .gitignore
└── README.md
```

---

## 4. API 设计

### 4.1 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/books` | 搜索/列表书目 |
| POST | `/api/books` | 新增/更新书目 |
| GET | `/api/books/{id}/similar` | 获取同类推荐 |
| GET | `/api/tags` | 获取标签列表 |
| POST | `/api/import/text` | 文本批量导入 |

### 4.2 静态文件服务

- `/` → `frontend/index.html`
- `/app.js` → `frontend/app.js`
- `/styles.css` → `frontend/styles.css`

路径安全检查：防止目录遍历攻击。

---

## 5. 前端架构

- **无框架**：原生 DOM 操作
- **渲染方式**：`<template>` 克隆 + 手动填充
- **状态管理**：全局变量 `sortMode`
- **数据流**：`render()` → `loadBooks()` + `api("/api/tags")` → `renderBooks()` + `renderTags()`

### 前端入口

```
render() → 并行加载 books + tags → 渲染标签云 + 书目卡片
```

---

## 6. 后端架构

- **单文件**：`server.js` 包含所有逻辑
- **路由**：URL 匹配，无路由框架
- **数据库**：`DatabaseSync` 同步 API
- **静态服务**：手动实现，带路径安全检查

### 启动流程

```
mkdirSync(data/) → new DatabaseSync() → CREATE TABLE → seedDatabase() → listen(PORT)
```

---

## 7. 数据流

### 搜索

```
Browser → GET /api/books?q=...&platform=...&status=...
→ db.prepare(SELECT books + tags GROUP BY).all()
→ hydrateBook() (解析 tag_blob)
→ scoreBook() (评分)
→ filter (平台/状态/分数)
→ sort (匹配度/评分/最近)
→ JSON 响应
```

### 导入

```
Browser → POST /api/import/text { text }
→ SHA-256 哈希去重
→ parseBooksFromText() (正则解析)
→ upsertBook() × N (UPSERT 入库)
→ addTags() × N (标签入库)
→ addRecommendationEdges() (推荐边)
→ JSON 响应
```

---

## 8. 安全考虑

| 项 | 措施 |
|----|------|
| 路径遍历 | `filePath.startsWith(ROOT)` 检查 |
| SQL 注入 | 参数化查询（`db.prepare().run()`） |
| XSS | `textContent` 赋值（不使用 innerHTML 插入用户数据） |
| CORS | 本地运行，无需处理 |

---

## 9. 扩展计划

| 阶段 | 架构变化 |
|------|---------|
| V0.2 | 添加爬虫模块（crawler/），独立进程 |
| V0.2 | 数据库添加索引 |
| V0.3 | 标签维度分组（dimensions 表） |
| V0.3 | FTS5 全文搜索 |
| V0.4 | AI 离线标签补充（独立脚本） |
