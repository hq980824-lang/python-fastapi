# 用 Depends 抽公共授权依赖

> 把多个接口重复的「查资源 + 校验归属」逻辑，抽成一个 FastAPI 依赖函数复用。
> 整理时间：2026-06-23
> 场景：posts 模块的 update / delete 接口，前半段「查文章 + 判空 + 校验是不是本人」完全重复。

---

## 一、问题：重复的授权前置逻辑

update 和 delete 接口开头一字不差地重复：

```python
db_post = await svc.get_by_id(db, post_id)       # 查文章
if not db_post:                                   # 不存在 → 400
    raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不存在")
if db_post.author_id != current_user.id:          # 不是本人 → 403
    raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="该文章不属于您")
```

这段干的事：**「拿到一篇属于当前用户的文章」**，输出一个校验通过的 `db_post`。

**核心洞察**：这正符合「值由程序准备」的模式 —— 凡是程序准备的值就用 `Depends`。所以把它做成依赖函数，返回 `db_post`，谁需要「我自己的文章」就 `Depends` 它。

---

## 二、做法

### 第 1 步：写依赖函数

```python
async def get_own_post(post_id: int, db: DbDep, current_user: CurrentUser) -> PostDB:
    db_post = await svc.get_by_id(db, post_id)
    if not db_post:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="文章不存在")
    if db_post.author_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="该文章不属于您")
    return db_post      # ★ 关键：把校验通过的对象交出去
```

要点：
- **依赖函数自己也能声明依赖**：`post_id`（路径）、`db`、`current_user` 都由 FastAPI 层层注入。
- **必须 return**：依赖的价值在「返回那个校验过的对象」，忘了 return 就返回 None（见踩坑）。

### 第 2 步：接口用上它

```python
@router.put("/{post_id}", response_model=PostResp)
async def update_post(payload: PostUpdate, db: DbDep, db_post: PostDB = Depends(get_own_post)):
    return await svc.update_post(db, payload=payload, db_post=db_post)

@router.delete("/{post_id}")
async def delete_post(db: DbDep, db_post: PostDB = Depends(get_own_post)):
    return await svc.delete_post(db, db_post=db_post)
```

变化：
- 那 5 行查 + 校验全没了，被 `db_post: PostDB = Depends(get_own_post)` 一行替代。
- 接口连 `post_id` 参数都不用写 —— 依赖函数内部声明了 `post_id`，FastAPI 自动从路径 `/{post_id}` 取。
- 接口函数只剩「自己独有的事」，鉴权交给依赖。

---

## 三、这体现的 Depends 高级能力

1. **依赖可以返回业务对象**：不只是「准备个 db」，还能「准备一个校验过的对象，不合格直接拦截」。
2. **依赖能嵌套依赖**：`get_own_post` 自己又依赖 `db`、`current_user`，FastAPI 层层解析。
3. **依赖里抛异常会中断请求**：校验不通过直接 403/400，接口函数根本不执行 —— 这正是想要的。
4. **横切逻辑收口**：以后任何「操作自己文章」的接口，加 `Depends(get_own_post)` 就自带「查 + 鉴权」，不再重复。

这就是大厂 FastAPI 代码的常见样子：把鉴权、查公共资源这类横切逻辑抽成依赖，接口只写业务。

---

## 四、踩坑记录

1. **依赖函数忘了 `return db_post`**（最易踩）：校验逻辑都写了（异常照抛），但漏了 return。结果依赖返回 None，接口里 `db_post` 拿到 None，调 service 时炸（None 没有 author_id、不能 setattr）。
   **教训**：依赖的意义在「交付物」（返回值），不只是「做校验」。抽依赖时先确认 return 了什么。
2. **何时用 Depends 的判断法则**：参数的值是「前端直接传的」还是「程序准备的」？
   - 前端直接传（body / path / query 的散值）→ 不用 Depends。
   - 程序准备（db 连接、当前用户、把散查询参数组装成对象、查校验过的资源）→ 用 Depends。
   - 注意：`payload: PostCreate` 来自 body，FastAPI 自动解析，**不用** Depends；`params: PageQuery = Depends()` 来自 query 要组装成对象，**要** Depends。

---

## 五、相关

- 依赖别名 `DbDep` / `CurrentUser` 的定义见 `src/common/dependencies.py`，思路见 [[postman-token-automation]] 同期重构。
- 鉴权设计（401 没登录 vs 403 没权限）见用户模块；JWT 实现见 [[redis-auth]]。
