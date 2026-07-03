# 小说标签体系（Tag System）

本目录用于维护 AI 小说搜索引擎的全部标签规范。

标签体系采用：

```
User Query
↓
Alias Expansion
↓
Canonical Tag
↓
Database Search
```

整个 MVP 不依赖 AI。

搜索过程全部通过：

- Alias Expansion
- Canonical Tag
- SQLite

完成。

---

## 目录说明

| 文件 | 说明 |
|------|------|
| [TAG_SYSTEM.md](./TAG_SYSTEM.md) | 整体设计原则 |
| [CATEGORY.md](./CATEGORY.md) | 标签分类 |
| [TAG_NAMING.md](./TAG_NAMING.md) | 命名规范 |
| [ALIAS_RULE.md](./ALIAS_RULE.md) | Alias 规范 |
| [TAG_TEMPLATE.md](./TAG_TEMPLATE.md) | 新增 Tag 模板 |
| [TAG_REVIEW.md](./TAG_REVIEW.md) | 审核规则 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本记录 |

---

## 设计目标

- **长期稳定**：核心结构不变，扩展通过别名和新维度
- **易维护**：CSV 数据 + Markdown 规范，人工可读可编辑
- **可扩展**：新增维度/标签不影响现有数据
- **去重**：Alias 机制统一不同叫法
- **AI 可理解**：结构化数据，未来可接入 AI 能力
