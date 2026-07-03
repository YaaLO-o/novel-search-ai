# Alias 设计规范

**Version**: V0.2
**Date**: 2026-07-03

---

## 1. 什么是 Alias

**Alias（别名）** 是一个标签的替代名称，用于：
- 支持用户习惯的不同叫法
- 统一不同平台的标签命名
- 提高搜索召回率

**示例**：
- 标准标签：`先婚后爱`
- 别名：`婚后再爱`、`契约婚姻`、`婚后恋`

---

## 2. Alias 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **同义词** | 完全相同的含义 | 甜宠 = 宠文 |
| **近义词** | 含义相近但略有差异 | 先婚后爱 ≈ 契约婚姻 |
| **平台差异** | 不同平台的叫法 | 晋江"幻想未来" = 起点"科幻" |
| **缩写** | 常见缩写 | HE = Happy Ending |
| **口语化** | 网络用语/口语 | 老实人 = 木头 = 直男 |

---

## 3. 数据库表

```sql
CREATE TABLE tag_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  alias TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL CHECK(type IN ('synonym', 'close', 'platform', 'abbr', 'slang')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alias_name ON tag_aliases(alias);
```

### 字段说明

- `tag_id`：指向标准标签的 ID
- `alias`：别名文本（唯一）
- `type`：别名类型

---

## 4. Alias 来源

### 4.1 用户输入
- 用户添加标签时，如果命中已有别名，自动关联到标准标签
- 用户可手动添加新别名

### 4.2 平台映射
- 不同平台的标签体系建立映射表
- 导入时自动转换

### 4.3 社区提取
- 从推书帖/书单中提取高频词
- 人工审核后添加为别名

---

## 5. 搜索时的 Alias 处理

**查询流程**：
```
用户输入："婚后再爱"
→ 查找 tag_aliases 表，发现是 "先婚后爱" 的别名
→ 搜索时同时匹配 "先婚后爱" 和 "婚后再爱"
→ 合并结果，按分数排序
```

**评分规则**：
- 命中标准标签：+6 分
- 命中别名：+5 分（略低于标准标签）

---

## 6. Alias 数据格式（aliases.csv）

```csv
standard_tag,alias,type,platform
先婚后爱,婚后再爱,synonym,通用
先婚后爱,契约婚姻,close,通用
HE,Happy Ending,abbr,通用
甜宠,宠文,synonym,通用
都市,现代都市,slang,通用
```

---

## 7. 维护规则

1. **一个别名只能指向一个标准标签**（禁止一对多）
2. **标准标签不能是其他标签的别名**（禁止循环）
3. **别名删除时级联删除关联关系**
4. **定期审核低频别名**（使用次数 < 3 可考虑删除）
