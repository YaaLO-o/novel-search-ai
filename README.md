# 书荒雷达 (Novel Search AI)

个人小说搜索与书库管理工具，解决"书荒"问题。

## 功能特性

- **智能搜索** — 按书名、作者、平台、标签多维搜索
- **标签系统** — 官方标签 / 个人标签 / 社区高频词三级分类
- **批量导入** — 粘贴 Obsidian 推书文本，自动解析入库
- **同类推荐** — 基于推荐关系图谱的关联推荐
- **多维排序** — 匹配度 / 评分 / 最近加入

## 快速开始

```bash
# 进入后端目录
cd backend

# 启动服务
node server.js

# 访问 http://localhost:5173
```

## 项目结构

```
novel-search-ai/
├── frontend/          # 前端静态文件
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── backend/           # 后端服务
│   ├── server.js
│   └── package.json
├── crawler/           # 爬虫模块（开发中）
├── data/              # 数据库文件（gitignored）
└── docs/              # 项目文档
    ├── PRD.md
    ├── MVP.md
    ├── database.md
    └── roadmap.md
```

## 技术栈

- **前端**: 原生 HTML / CSS / JavaScript
- **后端**: Node.js (>=24) HTTP 服务器
- **数据库**: SQLite (node:sqlite)

## 导入格式

支持粘贴以下格式的推书文本：

```
《书名》
作者：作者名
平台：晋江
官方标签：幻想未来，情有独钟
标签：bg，老实人女主
简介：这是一本好书...
```

同一段落中的书会自动建立"同类推荐"关系。

## 文档

详见 [docs/](./docs/) 目录。
