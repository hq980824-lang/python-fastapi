# 点赞功能复盘（多对多 + 联合唯一约束）

> 用户给文章点赞/取消赞，防重复，统计点赞数。
> 实现时间：2026-06-25
> 价值：全新模块，独立完成度最高的一次（基本自己写，只在卡点处要思路）。核心新知识：**联合唯一约束**、**多对多关联表**、**双层防重**。

---

## 一、设计：点赞 = 用户与文章的多对多

一个用户能赞多篇文章，一篇文章能被多个用户赞 → 多对多。中间用一张 **关联表 likes** 记录「谁赞了哪篇」。

likes 表核心：两个外键 `user_id`（谁）、`post_id`（哪篇）+ id + create_time。每一行 = 一个「某用户赞了某文章」的事实。

---

## 二、核心新知识：联合唯一约束（防重复点赞）

**一个用户对同一篇文章只能赞一次。** 怎么保证？在 `(user_id, post_id)` 两列上加**联合唯一约束**——这两列的**组合**不能重复。

```python
from sqlalchemy import UniqueConstraint

class LikeDB(Base):
    __tablename__ = "likes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    create_time: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uniq_userid_postid"),
    )
```

要点：
- 跟之前单列 `unique=True` 不同，这是**多列联合唯一**（组合不重复，单列各自可重复）。
- 表级约束放 **`__table_args__`**，它必须是**元组**。
- **单元素元组末尾必须加逗号**：`(UniqueConstraint(...),)`。少了逗号 `(x)` 不是元组、是 x 本身 → 报错。（JS 的 `[x]` 直接是数组，Python 元组单元素要尾逗号——JS 没有的坑。）
- model 用 SQLAlchemy 2.0 `Mapped` 写法，见 [[sqlalchemy-mapped-upgrade]]。
- 外键列类型是 `Mapped[int]`（存的是 id 数字），**不是** `Mapped["UserDB"]`（那是 relationship）。

建表后 `SHOW CREATE TABLE likes` 可见 `UNIQUE KEY uniq_userid_postid (user_id, post_id)`。

---

## 三、双层防重（A 应用层 + B 数据库兜底）

点赞要防重复，两层防护：

```python
async def like(self, db, post_id, user_id):
    # 检查文章存在(防外键报错)
    post = await db.get(PostDB, post_id)
    if post is None:
        raise ValueError("点赞失败：文章不存在")

    # A. 应用层查重(友好提示)
    exists = await self._get_like(db, user_id, post_id)
    if exists:
        return "已经点赞过了"

    # B. 数据库兜底(并发安全)
    new_like = LikeDB(user_id=user_id, post_id=post_id)
    try:
        db.add(new_like)
        await db.commit()
    except IntegrityError:
        await db.rollback()        # commit 失败必须 rollback
        raise ValueError("点赞失败：请勿重复点赞")
    return "点赞成功"
```

- **A（应用层查重）**：先查有没有赞过，赞过就友好返回。覆盖绝大多数情况。
- **B（数据库兜底）**：并发下「两个请求同时查都说没赞，然后都插入」，唯一约束会拦住第二个、抛 `IntegrityError`，try 住。`rollback` 必须有（commit 失败后 session 坏了，要回滚才能继续）。复用了 user 创建时的 IntegrityError 模式。
- **取舍**：A 友好但有并发漏洞，B 安全但提示笼统。生产 A+B 结合。

---

## 四、其他要点

- **查文章是否存在用 `db.get(PostDB, post_id)`**：按主键查，最快，查不到返回 None。比扯 PostService 干净。
- **多条件查询**：`select(LikeDB).where(and_(LikeDB.user_id == user_id, LikeDB.post_id == post_id))`。
- **抽私有方法 `_get_like`**：like/unlike 都要「按 user+post 查记录」，抽出来复用。`_` 前缀 = Python 约定的「内部方法」（JS 用 `#` 或 `_`，Python 纯靠 `_` 约定）。
- **count 用聚合**：`select(func.count(LikeDB.id)).where(LikeDB.post_id == post_id)` 统计某文章被赞数。

---

## 五、接口设计（controller）

```python
@router.post("/like")          # 点赞:创建,用 POST
async def post_like(db: DbDep, current_user: CurrentUser, post_id: int):
    return await svc.like(db=db, post_id=post_id, user_id=current_user.id)

@router.delete("/unlike")      # 取消:删除,用 DELETE(RESTful)
async def post_unlike(db: DbDep, current_user: CurrentUser, post_id: int):
    return await svc.unlike(db=db, post_id=post_id, user_id=current_user.id)

@router.get("/count")          # 点赞数:公开信息,不要求登录
async def post_count(db: DbDep, post_id: int):
    return await svc.count(db=db, post_id=post_id)
```

- **user_id 从 `current_user.id` 来，不让前端传**（防伪造，同 post 的 author_id）。
- **post_id 走查询参数**（直接 `post_id: int`，FastAPI 自动当 query 参数）。
- POST 点赞 / DELETE 取消，符合 RESTful 语义。
- count 是公开信息，不加鉴权。

---

## 六、踩坑记录

1. **SQLAlchemy 多条件别用 `and`（最坑）**：`where(A and B)` 中 Python 的 `and` 会把条件表达式按逻辑求值，**只剩后一个条件**，查重逻辑失效。要用 `and_(A, B)` 或逗号 `where(A, B)`。JS 没这场景，Python 拼 SQL 条件**永远别用 `and`/`or` 关键字**。
2. **`__table_args__` 单元素元组缺逗号**：`(UniqueConstraint(...))` 不是元组，要 `(...,)`。
3. **422 错误 = 参数没给齐**：`BaseModel + Depends()` 会把字段当查询参数（要 URL 带）。身份信息（user_id）不该放 DTO 让前端传，要从 current_user 来。
4. **service 不该用 `CurrentUser`**：CurrentUser 是 HTTP 层依赖，service 是业务层，只收普通 `user_id: int`。controller 解析当前用户、传 id 进来。
5. **`from ntpath import exists` 垃圾 import**：编辑器见局部变量 `exists` 自动从 Windows 模块 ntpath 乱 import。警惕来源诡异的自动 import，删掉。
6. **点赞不存在的文章会撞外键**：likes.post_id 是外键，插入不存在的 post_id 触发 IntegrityError。靠「先 db.get 查文章存在」拦掉（友好），IntegrityError 兜底（并发）。
7. **`DbDep` vs `AsyncSession` 不一致？不冲突**：`DbDep = Annotated[AsyncSession, Depends(get_db)]`，本质就是 AsyncSession，只多了「让 FastAPI 注入」的元数据。controller 要注入用 DbDep，service 收传入值用纯类型 AsyncSession——后者更对（service 不依赖 FastAPI）。

---

## 七、验证（7 场景全过）

点赞成功 / 重复点赞拦截 / 文章点赞数=1 / 取消成功 / 取消后数=0 / 取消没点过的(友好) / 点赞不存在文章(拒绝)。计数随点赞取消正确变化。

---

## 八、相关

- model 的 Mapped 写法见 [[sqlalchemy-mapped-upgrade]]。
- IntegrityError 防重复模式最早见用户创建。
- CurrentUser 鉴权依赖见 [[fastapi-depends-authorization]]、[[redis-auth]]。
