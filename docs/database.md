# 数据库设计：书荒雷达

**Version**: V0.1
**Date**: 2026-07-03
**Database**: SQLite（Node.js 内置 `node:sqlite` 模块）

---

## 1. 概述

使用 SQLite 作为本地数据库，通过 `DatabaseSync` 同步 API 访问。数据库文件位于 `data/novels.sqlite`。

---

## 2. 表结构

### 2.1 books — 书目主表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK AUTOINCREMENT | 自增主键 |
| title | TEXT NOT NULL | 书名 |
| author | TEXT NOT NULL DEFAULT '待补充' | 作者 |
| platform | TEXT NOT NULL DEFAULT '待补充' | 平台 |
| summary | TEXT NOT NULL DEFAULT '' | 简介/推荐语 |
| official_url | TEXT NOT NULL DEFAULT '' | 正版链接 |
| status | TEXT NOT NULL DEFAULT '想看' | 阅读状态 |
| rating | REAL NOT NULL DEFAULT 0 | 评分（0-10） |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**唯一约束**: `UNIQUE(title, author)`

**status 枚举**: `想看` | `在看` | `已看` | `避雷`

### 2.2 tags — 标签表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK AUTOINCREMENT | 自增主键 |
| name | TEXT NOT NULL | 标签名 |
| type | TEXT NOT NULL | 官方/用户/社区 |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**唯一约束**: `UNIQUE(name, type)`

**type 枚举**: `official` | `user` | `community`

### 2.3 book_tags — 书目-标签关联表

| 字段 | 类型 | 说明 |
|------|------|------|
| book_id | INTEGER FK | 关联 books.id |
| tag_id | INTEGER FK | 关联 tags.id |
| weight | INTEGER DEFAULT 1 | 权重（添加次数） |

**主键**: `PRIMARY KEY(book_id, tag_id)`

### 2.4 import_batches — 导入批次表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| type | TEXT NOT NULL | 导入类型 |
| content_hash | TEXT UNIQUE | SHA-256 哈希 |
| created_at | TEXT DEFAULT CURRENT_TIMESTAMP | 导入时间 |

### 2.5 import_books — 导入批次关联表

| 字段 | 类型 | 说明 |
|------|------|------|
| import_id | INTEGER FK | 关联 import_batches.id |
| book_id | INTEGER FK | 关联 books.id |

### 2.6 recommend_edges — 推荐关系表

| 字段 | 类型 | 说明 |
|------|------|------|
| book_a_id | INTEGER FK | 书 A（ID 较小） |
| book_b_id | INTEGER FK | 书 B（ID 较大） |
| weight | INTEGER DEFAULT 1 | 推荐强度 |

**约束**: `CHECK(book_a_id < book_b_id)`

---

## 3. 关系图

```
books ──┬── book_tags ──── tags
        ├── import_books ── import_batches
        └── recommend_edges (自关联)
```

---

## 4. 索引（计划 V0.2）

```sql
CREATE INDEX idx_book_tags_tag ON book_tags(tag_id);
CREATE INDEX idx_book_tags_book ON book_tags(book_id);
CREATE INDEX idx_tags_type ON tags(type);
CREATE INDEX idx_books_platform ON books(platform);
CREATE INDEX idx_books_status ON books(status);
CREATE INDEX idx_books_author ON books(author);
```

---

## 5. UPSERT 逻辑

### 书目去重

```sql
ON CONFLICT(title, author) DO UPDATE SET
  platform = CASE WHEN excluded.platform != '待补充' THEN excluded.platform ELSE books.platform END,
  summary = CASE WHEN excluded.summary != '' THEN excluded.summary ELSE books.summary END,
  official_url = CASE WHEN excluded.official_url != '' THEN excluded.official_url ELSE books.official_url END,
  status = CASE WHEN books.status = '想看' THEN excluded.status ELSE books.status END,
  rating = CASE WHEN excluded.rating > 0 THEN excluded.rating ELSE books.rating END,
  updated_at = CURRENT_TIMESTAMP
```

**策略**: 新数据填充空字段，不覆盖已有有效数据。

### 标签去重

```sql
ON CONFLICT(book_id, tag_id) DO UPDATE SET weight = weight + 1
```

---

## 6. 推荐边逻辑

- 同批次导入的书两两建立推荐边
- `book_a_id < book_b_id` 保证无向边唯一
- 重复导入时 `weight + 1`
- 查询按 `weight DESC` 排序
