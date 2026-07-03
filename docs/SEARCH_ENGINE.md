# 搜索引擎设计：书荒雷达

**Version**: V0.1
**Date**: 2026-07-03

---

## 1. 概述

当前搜索基于 SQLite + 内存评分，无外部搜索引擎依赖。所有数据加载到内存后进行匹配和排序。

---

## 2. 搜索 API

```
GET /api/books?q={关键词}&platform={平台}&status={状态}&sort={排序}
```

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| q | string | 搜索关键词（空格/逗号分隔多个词） |
| platform | string | 平台筛选 |
| status | string | 阅读状态筛选 |
| tagType | string | 限定标签类型搜索 |
| tags | string | 精确标签匹配 |
| sort | string | 排序方式：match / rating / recent |

---

## 3. 搜索流程

```
1. 加载全部 books + tags（LEFT JOIN）
2. 按平台/状态过滤
3. 对每本书计算匹配分数
4. 过滤 score > 0 的结果
5. 按排序方式排列
6. 返回
```

---

## 4. 评分算法

### 4.1 关键词匹配评分

对搜索词 `q` 分词后，逐词匹配：

| 匹配位置 | 分数 |
|----------|------|
| official 标签精确匹配 | +6 |
| 书名包含 | +5 |
| user 标签精确匹配 | +4 |
| community 标签精确匹配 | +3 |
| 其他文本（作者/平台/简介）包含 | +1 |

### 4.2 标签精确匹配评分

通过 `tags` 参数传入的标签，按类型加权：

| 匹配方式 | 分数 |
|----------|------|
| 指定 tagType 匹配 | +5 |
| 任意类型匹配 | +5 |

### 4.3 综合评分

```
总分 = 关键词匹配分 + 标签匹配分
```

---

## 5. 排序方式

| 排序 | 算法 |
|------|------|
| **match**（默认） | score DESC → rating DESC → id DESC |
| **rating** | rating DESC → id DESC |
| **recent** | id DESC |

---

## 6. 文本归一化

搜索前对所有文本执行 `normalize()`：
- 转小写
- 去除首尾空白

```js
function normalize(value) {
  return String(value || "").trim().toLowerCase();
}
```

---

## 7. 同类推荐

```
GET /api/books/{id}/similar
```

- 查询 `recommend_edges` 表，找与目标书关联的所有书
- 按 `weight DESC → rating DESC → id DESC` 排序
- 最多返回 20 本
- 返回推荐强度作为 `reason`

---

## 8. 标签云

```
GET /api/tags?type={类型}&q={关键词}
```

- 按 `weight DESC → bookCount DESC → name ASC` 排序
- 前端取 Top 24 展示

---

## 9. 已知限制

- 全表扫描：每次搜索加载全部数据到内存
- 无模糊匹配：不支持拼音/纠错/同义词
- 无分页：返回全部结果
- 评分是精确匹配，不支持部分匹配

---

## 10. 优化计划（V0.2+）

| 优化项 | 方案 | 优先级 |
|--------|------|--------|
| 数据库索引 | 为 tag_id、platform、status 添加索引 | 高 |
| 分页 | 返回 limit/offset | 中 |
| 部分匹配 | LIKE '%keyword%' 改为 FTS5 全文索引 | 中 |
| 多标签组合 | AND/OR/NOT 查询语法 | 高 |
| 同义词 | 标签同义词表 | 低 |
