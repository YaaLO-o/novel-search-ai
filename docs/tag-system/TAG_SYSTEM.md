# TAG_SYSTEM.md

> AI 小说搜索引擎标签体系设计规范（Tag System Specification）
> Version: MVP v1.0
> Status: Draft

---

# 1. 文档目的

本文档定义 AI 小说搜索引擎的标签体系设计规范，是整个项目关于标签系统的最高设计标准。

任何涉及标签（Tag）、别名（Alias）、分类（Category）、数据库设计、搜索逻辑等内容，都必须遵循本规范。

本规范适用于：

* 标签设计
* 数据库建模
* 搜索逻辑
* 前端筛选器
* 数据导入
* 标签维护
* 后续 AI 自动标注（V2）

---

# 2. 设计目标

本项目不采用传统小说网站的"自由标签（Free Tag）"模式，而采用标准化标签体系。

设计目标如下：

* 标签长期稳定，不因网络流行词变化而频繁修改
* 标签语义唯一，避免重复和歧义
* 支持复杂组合查询
* 降低数据库维护成本
* 支持 Alias 扩展
* 支持未来 AI 自动标注
* MVP 阶段尽可能不依赖 AI，降低 Token 成本

---

# 3. 标签体系架构

整个搜索流程采用三层结构。

```text
User Query
      │
      ▼
Alias Expansion
      │
      ▼
Canonical Tag
      │
      ▼
Database Search
```

说明：

* User Query：用户输入的自然语言或关键词。
* Alias Expansion：将网络黑话、缩写、同义词转换为标准标签。
* Canonical Tag：数据库唯一认可的标准标签。
* Database Search：基于标准标签完成检索。

MVP 阶段搜索流程不调用 AI。

---

# 4. 核心概念

## 4.1 Canonical Tag（标准标签）

Canonical Tag 是数据库中的唯一标准标签。

特点：

* 长期稳定
* 唯一语义
* 可组合
* 可维护
* 可索引

例如：

```text
西幻
成长型
天然呆
群像
权谋
学院
HE
```

数据库只存储 Canonical Tag。

---

## 4.2 Alias（别名）

Alias 是用户搜索时使用的各种表达方式。

Alias 不进入数据库。

Alias 仅用于搜索转换。

例如：

```text
女嬷文

↓

女性成长
女性群像
女性互助
低恋爱占比
```

再例如：

```text
老房子着火

↓

成熟角色
男主先动心
追求型关系
```

Alias 可以：

* 一对一
* 一对多
* 多对一

---

# 5. 设计原则

## Principle 1：一个 Tag 只表达一个概念

每个 Tag 只能表示一个语义。

正确：

```text
成长型
天然呆
疯批
西幻
学院
```

错误：

```text
成长型天然呆女主
疯批忠犬男主
西幻学院恋爱
```

多个概念必须拆分。

---

## Principle 2：Tag 必须可组合

复杂语义应通过多个 Tag 组合实现。

例如：

```text
成长型女主
```

拆分为：

```text
角色：女主

成长：成长型
```

例如：

```text
疯批忠犬男主
```

拆分为：

```text
角色：男主

性格：疯批

性格：忠犬
```

组合能力优先于复杂标签。

---

## Principle 3：Canonical Tag 必须稳定

Canonical Tag 应具有长期稳定性。

适合作为 Canonical：

```text
西幻
无限流
成长型
群像
HE
```

不适合作为 Canonical：

```text
女嬷文
电子榨菜
老房子着火
训狗文学
```

此类概念应进入 Alias。

---

## Principle 4：避免重复表达

同一个概念只能存在一个 Canonical Tag。

例如：

错误：

```text
成长流
成长系
成长型
```

最终只能保留：

```text
成长型
```

其他全部作为 Alias。

---

## Principle 5：Tag 不使用完整句子

Tag 不是自然语言。

错误：

```text
男主后期追妻
```

正确：

```text
追妻

后期

主动追求
```

搜索时组合。

---

## Principle 6：Tag 应保持领域中立

Canonical Tag 不依赖某个平台的流行表达。

例如：

使用：

```text
追妻
```

而不是：

```text
训狗
```

平台流行语统一交由 Alias 管理。

---

# 6. 标签生命周期

每个 Tag 遵循统一生命周期。

```text
提出

↓

讨论

↓

审核

↓

加入 Canonical

↓

正式上线

↓

长期维护

↓

废弃（Deprecated）
```

任何 Canonical Tag 的新增、修改或废弃，都需要经过审核。

---

# 7. 标签组成

每个 Canonical Tag 至少包含以下信息。

| 字段           | 必填 | 说明                  |
| ------------ | -- | ------------------- |
| id           | 是  | 唯一 ID               |
| name         | 是  | 中文名称                |
| category     | 是  | 一级分类                |
| sub_category | 是  | 二级分类                |
| description  | 是  | 标签定义                |
| status       | 是  | active / deprecated |

可选字段：

| 字段       | 说明   |
| -------- | ---- |
| aliases  | 同义词  |
| related  | 相关标签 |
| conflict | 冲突标签 |
| examples | 示例作品 |
| notes    | 维护备注 |

---

# 8. Tag ID 规范

每个 Tag 必须拥有唯一 ID。

推荐格式：

```text
CATEGORY_SUBCATEGORY_NAME
```

例如：

```text
WORLD_SETTING_WESTERN_FANTASY

CHARACTER_PERSONALITY_TSUNDERE

PLOT_THEME_REVENGE

STYLE_NARRATIVE_GROUP

ENDING_HE
```

要求：

* 全部使用英文
* 全部使用大写
* 使用下划线连接
* ID 永久不修改

数据库引用 ID，而不是中文名称。

---

# 9. Alias 设计规范

Alias 不属于数据库标签。

Alias 的职责只有一个：

> 将用户输入转换为标准标签。

例如：

```text
女嬷文

↓

女性成长
女性群像
女性互助
```

例如：

```text
电子榨菜

↓

轻松
节奏快
爽文
```

Alias 不参与数据库建模。

---

# 10. 搜索流程

MVP 搜索流程如下：

```text
用户输入

↓

分词

↓

Alias 查询

↓

Canonical Tag

↓

数据库检索

↓

排序

↓

返回结果
```

整个过程：

* 不调用 AI
* 不产生 Token
* 可完全本地运行

---

# 11. 禁止事项

以下内容不得作为 Canonical Tag：

## 网络流行语

例如：

```text
女嬷文
老房子着火
电子榨菜
```

---

## 长句

例如：

```text
男主后期疯狂追妻
```

---

## 多概念组合

例如：

```text
成长型天然呆女主
```

---

## 重复语义

例如：

```text
成长流
成长系
成长型
```

只能保留一个。

---

## 模糊概念

例如：

```text
很好看
很虐
最近很火
```

不具备稳定定义，不纳入 Canonical。

---

# 12. MVP 范围

MVP v1 仅包含：

* 一级分类
* 二级分类
* Canonical Tag
* Alias
* SQLite 检索
* 标签过滤

不包含：

* AI 查询理解
* 自动标签生成
* 向量检索
* 推荐算法
* 知识图谱
* 多语言标签

上述能力将在后续版本逐步加入。

---

# 13. 后续规划

标签体系将在保持 Canonical Tag 稳定的前提下持续扩展。

未来版本计划支持：

* AI 自动标签生成
* 标签权重
* 标签共现关系
* 标签知识图谱
* 多语言名称
* 社区贡献审核机制
* 用户搜索日志驱动的 Alias 扩展

无论系统如何升级，本规范始终作为标签体系的基础设计标准，所有新增功能均应兼容 Canonical Tag + Alias 的整体架构。
