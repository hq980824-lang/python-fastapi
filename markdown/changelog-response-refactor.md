# 本次改动复盘：统一响应 + 异常处理

> 这份文档按「遇到的问题 → 怎么解决」的顺序，把这一轮的所有改动串起来，方便回头理解每一步为什么这么改。

---

## 一句话总结

把「每个接口手动拼 `success()`」改成「框架自动包装」，过程中修掉了 4 个真实 bug。最终效果：controller 只写业务逻辑 + 一行 `response_model`，统一的 `{code, msg, data}` 结构由路由层自动套上。

---

## 改动涉及的文件

| 文件                              | 改了什么                              |
| ------------------------------- | --------------------------------- |
| `src/modules/users/user_dto.py` | 时间字段类型 `str` → `datetime`         |
| `src/common/exception.py`       | `model_dump()` → `model_dump(mode="json")` |
| `src/common/route.py`           | 修对自动包装逻辑（这次的核心）                   |
| `src/modules/users/user_controller.py` | 改用 `response_model`，删掉手动转换样板  |
| `requirements.txt`              | 补上 `cryptography` 依赖              |

---

## 按顺序复盘每个问题

### 问题 1：连数据库直接 500 —— 缺 `cryptography`

**报错：**
```
RuntimeError: 'cryptography' package is required for sha256_password
or caching_sha2_password auth methods
```

**原因：** MySQL 8.0+ 默认用 `caching_sha2_password` 认证，需要 RSA 加密密码，而 RSA 依赖 `cryptography` 包，venv 里没装。

**解决：** 装上 `cryptography`，并写进 `requirements.txt`。

---

### 问题 2：查询用户报 datetime 校验错误

**报错：**
```
ValidationError: 2 validation errors for UserResp
create_time: Input should be a valid string ...
  input_value=datetime.datetime(2026, 6, 16, ...), input_type=datetime
```

**原因：** 数据库 `create_time`/`update_time` 是 `DateTime` 列，查出来是 `datetime` 对象；但 `UserResp` 里把它们声明成了 `str`。Pydantic v2 不会自动把 `datetime` 当字符串校验。

**解决：** `user_dto.py` 里字段类型从 `str` 改成 `datetime`。

```python
# 改前
create_time: str | None = None
# 改后
create_time: datetime | None = None
```

---

### 问题 3：datetime 序列化隐患（response + exception 两处）

**问题：** `model_dump()`（默认 `mode="python"`）返回的 dict 里 `create_time` 还是 `datetime` 对象。一旦交给 `json.dumps` / `JSONResponse` 就会报 `TypeError: Object of type datetime is not JSON serializable`。

**解决：** 统一改用 `model_dump(mode="json")`，让 Pydantic 在转 dict 时就把 datetime 转成 ISO 字符串。

```python
# 改前
.model_dump()
# 改后
.model_dump(mode="json")
```

---

### 问题 4：`create_router` 启动直接崩

**报错：**
```
TypeError: APIRoute.__init__() got an unexpected keyword argument 'prefix'
```

**原因：** 搞混了两个类。

| 类           | 是什么          | 接受 `prefix`？ |
| ----------- | ------------ | ----------- |
| `APIRoute`  | **单条**路由     | 否           |
| `APIRouter` | 路由**分组**（容器） | 是           |

`create_router` 想创建一个带 `prefix`/`tags`/`route_class` 的路由分组，却用了单条路由的 `APIRoute`。

**解决：** 改用 `APIRouter`。

```python
# 改前
return APIRoute(prefix=prefix, tags=tags, route_class=ResponseRoute)
# 改后
return APIRouter(prefix=prefix, tags=tags, route_class=ResponseRoute)
```

---

### 问题 5（最隐蔽）：自动包装其实是「死代码」

这是这次最值得记住的一个。改完前面之后，接口能跑了，但**返回的根本不是统一结构**——`success()` 那行从来没被执行过。

**最初的错误写法：**
```python
async def custom_handler(request: Request):
    response = await original_handler(request)
    if isinstance(response, Response):   # ← 永远成立
        return response
    return success(data=response).model_dump()   # ← 永远走不到，死代码
```

**为什么是死代码：** `original_handler(request)` 返回的**已经是**一个 `Response` 对象（FastAPI 已经帮你序列化好了）。所以 `isinstance(response, Response)` 永远为真，直接 return 原样响应，下面的包装逻辑根本碰不到。

也就是说：之前 controller 手动 `success()` 时响应是统一的；一改成「靠自动包装」，反而把统一结构弄丢了，而且不报错，很难发现。

**正确思路：** 不能原样放行，要把 handler 已经序列化好的 JSON body 取出来，重新套上外壳。

```python
async def custom_handler(request: Request):
    response = await original_handler(request)
    # 只处理 JSON 响应，靠 content-type 判断
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return response
    data = json.loads(response.body)                       # 取出原始数据
    content = success(data=data).model_dump(mode="json")   # 套统一外壳
    return JSONResponse(content=content, status_code=response.status_code)
```

---

### 问题 6：包装判断不能用 `isinstance(response, JSONResponse)`

修问题 5 时第一版写的是 `if not isinstance(response, JSONResponse): return response`，结果包装又没生效。

**原因：** 用了 `response_model` 之后，FastAPI 返回的是基类 `Response`，**不是** `JSONResponse`。按类型判断会把它当成「非 JSON」放行，跳过包装。

**解决：** 改成判断响应头的 `content-type` 是否以 `application/json` 开头，不依赖具体的 Response 子类。

---

## 最终的设计：两层各管一件事

```
数据库查询
  → UserDB（SQLAlchemy ORM 对象）
  → [第一层] response_model=UserResp 自动转换
       ORM → DTO，datetime → ISO 字符串（靠 from_attributes=True）
  → [第二层] ResponseRoute 自动套外壳
       {"code":200,"msg":"操作成功","data":{...}}
```

| 层               | 职责                       | 写在哪                  |
| --------------- | ------------------------ | -------------------- |
| `response_model` | ORM → DTO + 类型序列化         | controller 接口声明上     |
| `ResponseRoute`  | 套 `code/msg/data` 统一外壳   | `src/common/route.py` |

**controller 现在长这样**（对比改之前，样板代码基本消失）：

```python
# 改前：每个接口都要手动转换 + 包装
@router.get("/{user_id}")
async def get_user(user_id: int, ...):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return UserResp.model_validate(user).model_dump(mode="json")

# 改后：声明 response_model，直接返回 ORM 对象
@router.get("/{user_id}", response_model=UserResp)
async def get_user(user_id: int, ...):
    user = await svc.get_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="用户不存在")
    return user
```

---

## 几条值得记住的经验

1. **`APIRoute` 是单条路由，`APIRouter` 是路由分组** —— `prefix`/`route_class` 挂在后者上。
2. **自定义 `APIRoute` 时，`original_handler` 返回的已经是 `Response`** —— 想改内容得「拆开 → 改 → 重新封装」，不能原样 return。
3. **判断响应类型用 `content-type`，别用 `isinstance`** —— `response_model` 会让返回类型变成基类 `Response`。
4. **`model_dump()` 默认不转 datetime** —— 要进 JSON 就用 `model_dump(mode="json")`。
5. **「不报错」不等于「对」** —— 死代码型 bug（问题 5）最坑，一定要实际打一次请求验证返回结构。

---

## 相关文档

- 统一响应细节：`response.md`
- 异常处理细节：`exception-handler.md`
- 数据库连接与迁移：`db-connection.md`
