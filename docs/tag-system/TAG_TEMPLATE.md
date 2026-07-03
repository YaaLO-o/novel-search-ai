# Tag 编写模板

**Version**: V0.2
**Date**: 2026-07-03

---

## 1. 模板说明

每个标准标签（canonical tag）都需要按此模板编写，确保信息完整、格式统一。

---

## 2. 单个 Tag 模板

```yaml
---
tag_name: "甜宠"
category: "剧情元素"
dimension: "剧情元素"
aliases:
  - "宠文"
  - "甜蜜"
platforms:
  - "晋江"
  - "起点"
  - "番茄"
description: "以甜蜜、轻松、宠溺为主的剧情风格，通常包含大量甜蜜互动和撒糖情节"
examples:
  - "《嫁给偏执大佬后我甜了》"
  - "《总裁的甜蜜小娇妻》"
conflicts:
  - "虐恋"
related_tags:
  - "BG"
  - "先婚后爱"
  - "治愈"
priority: "high"
status: "active"
created_at: "2026-07-03"
---
```

---

## 3. 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `tag_name` | string | ✅ | 标准标签名（2-8字） |
| `category` | string | ✅ | 所属一级分类 |
| `dimension` | string | ✅ | 所属维度 |
| `aliases` | array | ⬜ | 别名列表 |
| `platforms` | array | ⬜ | 支持的平台 |
| `description` | string | ✅ | 标签定义说明 |
| `examples` | array | ⬜ | 示例小说 |
| `conflicts` | array | ⬜ | 互斥标签 |
| `related_tags` | array | ⬜ | 相关标签 |
| `priority` | enum | ✅ | 优先级：high/medium/low |
| `status` | enum | ✅ | 状态：active/deprecated/draft |
| `created_at` | date | ✅ | 创建时间 |

---

## 4. 编写规范

### 4.1 tag_name
- 使用 `TAG_NAMING.md` 中的命名规范
- 英文标签统一大写
- 不加符号、不加前缀

### 4.2 description
- 用一句话说明标签含义
- 避免使用标签名本身解释
- 示例：
  - ✅ "以甜蜜、轻松、宠溺为主的剧情风格"
  - ❌ "甜宠就是很甜很宠的小说"

### 4.3 aliases
- 列出所有已知的别名
- 参考 `ALIAS_RULE.md` 的分类
- 每个别名一行

### 4.4 conflicts
- 列出不能同时出现的标签
- 同一维度内互斥的标签
- 示例：`甜宠` 与 `虐恋` 互斥

### 4.5 related_tags
- 列出经常一起出现的标签
- 帮助用户发现相关书籍

---

## 5. 批量编写建议

1. **按维度分组编写**：先写完一个维度的所有标签
2. **参考平台数据**：优先收录主流平台的官方标签
3. **收集用户反馈**：记录用户实际搜索的关键词
4. **定期更新**：每月审核一次标签使用情况

---

## 6. 示例：人设维度标签

```yaml
---
tag_name: "老实人"
category: "人设"
dimension: "人设"
aliases:
  - "木头"
  - "直男"
  - "榆木脑袋"
description: "性格木讷、憨厚、不懂浪漫的角色设定"
examples:
  - "《老实人不老实》"
conflicts: []
related_tags:
  - "BG"
  - "甜宠"
  - "追妻火葬场"
priority: "high"
status: "active"
---
```
