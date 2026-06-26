# SQLAlchemy 2.0 Model 升级复盘（Mapped 写法）

> 把 ORM model 从老式 `Column(...)` 升级到 SQLAlchemy 2.0 的 `Mapped[X] = mapped_column(...)` 写法。
> 实现时间：2026-06-25
> 动机：老写法编辑器推不出字段类型（`post.author` 白色、无补全）；新写法类型友好、是官方现代推荐。
> 关键：**只换声明写法，表结构零变化，不需要 Alembic 迁移。**

---

## 一、核心变化：Column → Mapped + mapped_column

```python
# 旧
id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

# 新
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键ID")
```

三处变化：
1. 加类型标注 `: Mapped[int]` —— 告诉编辑器这列是 int，能补全/查错。
2. `Column` → `mapped_column`。
3. 类型参数可省 —— `Mapped[int]` 已声明 int，`mapped_column` 里不用再写 `Integer`。

---

## 二、类型对应表

| 旧 | 新 | 备注 |
| --- | --- | --- |
| `Integer` | `Mapped[int]` | 类型可省 |
| `String(50)` | `Mapped[str]` + `mapped_column(String(50))` | **长度推不出，要明写 String(50)** |
| `Text` | `Mapped[str]` + `mapped_column(Text)` | **Text 推不出（默认会变 VARCHAR），要明写 Text** |
| `DateTime` | `Mapped[datetime]` | 要 `from datetime import datetime`，类型可省 |
| 枚举 `SQLEnum(PostStatus)` | `Mapped[PostStatus]` | **能自动推断用 Enum 存，连 SQLEnum 都省了** |
| `nullable=False` | `Mapped[int]`（不带 None） | 默认非空，省 nullable |
| `nullable=True` | `Mapped[int \| None]` | **类型带 None = 可空** |

**类型推断的边界（重要）**：Python 基础类型（int/datetime/枚举）能推；但**具体列类型选择**（Text vs 默认 VARCHAR、String 的长度）推不出，必须在 `mapped_column` 里明写。

---

## 三、relationship 升级

```python
# 旧（编辑器推不出类型，post.author 白色无补全）
author = relationship("UserDB", back_populates="posts")

# 新（明确类型，post.author.email 能补全）
author: Mapped["UserDB"] = relationship(back_populates="posts")     # 多对一：单个
posts: Mapped[list["PostDB"]] = relationship(back_populates="author")  # 一对多：list
```

- 多对一（一篇文章一个作者）→ `Mapped["UserDB"]`
- 一对多（一个作者多篇文章）→ `Mapped[list["PostDB"]]`
- 类名**始终用字符串**（带引号），运行时靠 SQLAlchemy 延迟解析，避免循环 import。

---

## 四、TYPE_CHECKING：解决「类型要 import、运行时不能 import」

`Mapped["PostDB"]` 里编辑器想找 PostDB 做类型检查，但真 import 会造成两个 model 互相依赖（循环 import）。解法：

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:                                  # 运行时=False，类型检查时=True
    from src.modules.posts.post_model import PostDB
```

- **运行时**：`TYPE_CHECKING` 是 False → import 不执行 → 不循环 import。
- **编辑器静态分析**：当成 True → 看得到 import → 不标黄、能补全。

一举两得。注意：`Mapped[...]` 里**仍用字符串**（`"PostDB"`），TYPE_CHECKING 只是让编辑器认识它。

**通用模式**：任何「类型标注需要某类、但运行时 import 会循环依赖」都用 TYPE_CHECKING。类比 TS 的 `import type`。

---

## 五、踩坑记录

1. **编辑器自动 import 引发循环依赖**：删掉老 relationship 后写 `Mapped["PostDB"]`，编辑器「好心」自动加 `from ... import PostDB`，反而造成循环 import。要删掉，改用 TYPE_CHECKING。编辑器不懂 SQLAlchemy 字符串引用机制。
2. **`import datetime` vs `from datetime import datetime`**：`Mapped[datetime]` 要的是 datetime **类**，必须 `from datetime import datetime`；`import datetime` 导入的是**模块**，类型不对。（datetime 模块里有个同名 datetime 类，经典混淆。）
3. **content 漏写 Text → 表结构被改**：`Mapped[str | None] = mapped_column(comment=...)` 没写 `Text`，默认映射成 VARCHAR，TEXT 列就被改成 VARCHAR 了——破坏了「只换写法不动表」。必须 `mapped_column(Text, ...)`。
4. **`Mapped[UserDB]` 漏引号**：TYPE_CHECKING 里 import 的类运行时不存在，`Mapped[UserDB]`（无引号）运行时 NameError。要 `Mapped["UserDB"]`（字符串延迟解析）。规则：TYPE_CHECKING 导入的类，在 Mapped 里用都加引号。

---

## 六、验证：确认表结构没变

升级是纯写法变更，验证核心是「表结构跟升级前一致」：

```python
print(PostDB.__table__.c.content.type)     # TEXT(没变成 VARCHAR ✅)
print(PostDB.__table__.c.title.type)       # VARCHAR(200)
print(PostDB.__table__.c.status.type)      # VARCHAR(9)（枚举自动映射）
print(PostDB.__table__.c.author_id.nullable)  # False（Mapped[int] 默认非空）
```

实测结果全部与升级前一致 → 确认**不需要 Alembic 迁移**。
（最权威验证：`alembic revision --autogenerate`，若生成空迁移＝表无差异。）

---

## 七、收获

- **新旧写法可混用**：先升 UserDB、PostDB 还是旧的，能正常跑 → 大项目可渐进升级，不必一次全改。
- **`Mapped[X | None]` 类型即约束**：可空与否写在类型里，比 nullable 直观。
- **枚举省 SQLEnum**：`Mapped[PostStatus]` 自动推断。
- **类型推断有边界**：长度、Text 这类列细节仍要明写。
- 升级后 `post.author.email` 有补全了，最初的动机达成。

---

## 八、相关

- model/关系最初的建立见一对多建模；relationship 字符串引用的「failed to locate」坑见 [[docker-compose]]（同类「类未加载」问题）。
- 枚举 `PostStatus` 定义见 `post_dto.py`。
