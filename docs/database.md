# 数据库设计

## 概述
使用 SQLite 作为本地数据库，通过 Node.js 内置 `node:sqlite` 模块访问。

## 表结构

### 1. books — 书目主表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| title | TEXT NOT NULL | 书名 |
| author | TEXT DEFAULT '待补充' | 作者 |
| platform | TEXT DEFAULT '待补充' | 平台（晋江/起点/番茄等） |
| summary | TEXT | 简介/推荐语 |
| official_url | TEXT | 正版链接 |
| status | TEXT DEFAULT '想看' | 阅读状态：想看/在看/已看/避雷 |
| rating | REAL DEFAULT 0 | 评分（0-10） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**唯一约束**: `UNIQUE(title, author)` — 同作者同书名不重复

### 2. tags — 标签表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT NOT NULL | 标签名 |
| type | TEXT NOT NULL | 类型：official / user / community |
| created_at | TEXT | 创建时间 |

**唯一约束**: `UNIQUE(name, type)` — 同类型同名不重复

**标签类型说明**:
- `official`: 平台官方标签（如"都市""幻想未来"）
- `user`: 用户自定义标签（如"老实人女主""外星人"）
- `community`: 从推书文本提取的高频词

### 3. book_tags — 书目-标签关联表
| 字段 | 类型 | 说明 |
|------|------|------|
| book_id | INTEGER FK | 关联 books.id |
| tag_id | INTEGER FK | 关联 tags.id |
| weight | INTEGER DEFAULT 1 | 权重（被添加次数） |

**主键**: `PRIMARY KEY(book_id, tag_id)`

### 4. import_batches — 导入批次表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| type | TEXT | 导入类型（text） |
| content_hash | TEXT UNIQUE | 内容 SHA-256 哈希（防重复） |
| created_at | TEXT | 导入时间 |

### 5. import_books — 导入批次关联表
| 字段 | 类型 | 说明 |
|------|------|------|
| import_id | INTEGER FK | 关联 import_batches.id |
| book_id | INTEGER FK | 关联 books.id |

### 6. recommend_edges — 推荐关系表
| 字段 | 类型 | 说明 |
|------|------|------|
| book_a_id | INTEGER FK | 书 A（ID 较小） |
| book_b_id | INTEGER FK | 书 B（ID 较大） |
| weight | INTEGER DEFAULT 1 | 推荐强度（共同出现次数） |

**约束**: `CHECK(book_a_id < book_b_id)` — 保证无向边唯一

## 关系图
```
books ──┬── book_tags ──── tags
        ├── import_books ── import_batches
        └── recommend_edges (自关联)
```

## 导入去重逻辑
1. 计算导入文本的 SHA-256 哈希
2. 查询 import_batches 是否已有相同哈希
3. 如已存在则跳过，返回"这段文本已经导入过"
4. 如不存在则解析并入库

## 推荐边创建逻辑
同一导入批次中的所有书两两建立推荐关系：
- 书 A（ID 小）→ 书 B（ID 大）
- 重复导入时 weight + 1
- 查询时按 weight 降序排列
