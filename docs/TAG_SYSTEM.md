# 标签体系设计：书荒雷达

**Version**: V0.1
**Date**: 2026-07-03

---

## 1. 设计目标

建立统一的标签体系，支持多维度组合搜索，覆盖小说的核心属性。

**设计原则**：
- 标签从用户真实搜索需求中提炼
- 三级分类：官方标签 / 用户标签 / 社区高频词
- 支持后续扩展为维度层级体系

---

## 2. 当前标签分类（V0.1）

| 类型 | 字段值 | 来源 | 说明 |
|------|--------|------|------|
| **官方标签** | `official` | 平台自带 | 晋江/起点/番茄等平台的分类标签 |
| **用户标签** | `user` | 用户手动添加 | 个人定义的口味标签 |
| **社区标签** | `community` | 推书文本提取 | 从推书帖/书单中提取的高频词 |

---

## 3. 标签来源优先级

```
官方标签（official）  >  用户标签（user）  >  社区标签（community）
```

搜索评分时加权：

| 标签类型 | 权重 |
|----------|------|
| official | +6 |
| user | +4 |
| community | +3 |

---

## 4. 标签命名规范

- 简体中文，2-8 个字
- 不加书名号、引号
- 不用缩写（除非广泛通用）
- 同类型下标签不重叠
- 支持 `#` 前缀的 hashtag 格式（从推书文本自动提取）

---

## 5. 数据库表

```sql
CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('official', 'user', 'community')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(name, type)
);

CREATE TABLE book_tags (
  book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  weight INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(book_id, tag_id)
);
```

### 字段说明

- `tags.name`：标签名（如 "BG"、"老实人"、"都市"）
- `tags.type`：标签来源（official / user / community）
- `book_tags.weight`：关联权重（重复添加时 +1，用于排序）

---

## 6. 平台标签映射（计划）

不同平台的标签体系不同，需要建立映射表：

| 平台 | 官方标签示例 | 书荒雷达映射 |
|------|-------------|-------------|
| 晋江 | 幻想未来、情有独钟 | official |
| 晋江 | 无cp / 纯爱 / 百合 / 言情 | official（CP类型维度） |
| 起点 | 都市、异能 | official |
| 留茄 | 甜宠、穿越 | official |

V0.2 计划增加维度分组（CP类型、题材、人设、剧情元素、文风、结局等）。

---

## 7. 标签质量规则（计划 V0.2）

- 单本小说标签数 < 3：标记为"标签不足"
- 标签频次 = 1 且不在白名单：标记为"疑似噪声"
- 同维度互斥标签同时出现：标记为"冲突"

---

## 8. 搜索查询示例

```
用户输入：bg 老实人 晋江
→ 分词为 ["bg", "老实人", "晋江"]
→ 对每本书计算匹配分数：
  - official 标签命中：+6
  - user 标签命中：+4
  - community 标签命中：+3
  - 书名命中：+5
  - 其他文本命中：+1
→ 按分数降序排列
```
