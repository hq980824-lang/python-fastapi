# 异常拦截器说明

## 目标

把所有异常（业务异常、未预料的 bug）统一转成规范的失败响应，避免把错误堆栈直接泄露给前端：

```json
{
  "code": 400,
  "msg": "用户不存在",
  "data": null
}
```

失败响应复用 `success/fail` 的统一结构，详见 `response.md`。

---

## 一、两个异常处理器（`src/common/exception.py`）

```python
from http import HTTPStatus
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from src.common.response import fail

# 处理主动抛出的 HTTPException（业务异常，如"用户不存在"）
async def http_err_handler(req: Request, exc: HTTPException):
    return JSONResponse(content=fail(msg=exc.detail, code=exc.status_code).model_dump())

# 兜底处理所有未捕获的异常（代码 bug、数据库挂了等）
async def global_err_handler(req: Request, exc: Exception):
    return JSONResponse(content=fail(msg="服务器异常", code=HTTPStatus.INTERNAL_SERVER_ERROR).model_dump())
```

**两个 handler 的分工：**

| Handler              | 捕获对象            | 触发场景                                        |
| -------------------- | --------------- | ------------------------------------------- |
| `http_err_handler`   | `HTTPException` | controller 里 `raise HTTPException(...)`，如"用户不存在" |
| `global_err_handler` | `Exception`     | 任何没被显式捕获的异常，兜底防止把堆栈泄露给前端                    |

`global_err_handler` 的意义：哪怕代码里出了没预料到的 bug，前端拿到的也是规范的 `{"code":500,"msg":"服务器异常"}`，而不是一大段 500 错误堆栈。

---

## 二、注册到应用（`src/main.py`）

```python
from src.common.exception import global_err_handler, http_err_handler

app.add_exception_handler(HTTPException, http_err_handler)
app.add_exception_handler(Exception, global_err_handler)
```

`add_exception_handler(异常类型, 处理函数)`：FastAPI 在请求处理过程中捕获到对应类型的异常时，自动调用注册的 handler。FastAPI 按异常类型精确/继承匹配，注册顺序不影响。

---

## 三、目前存在的问题与改进建议

### 1. datetime 序列化风险（高优先级）

异常 handler 用了 `fail(...).model_dump()` 再交给 `JSONResponse`。`model_dump()`（默认 `mode="python"`）返回的 dict 里如果含有 `datetime` 等非原生类型，`JSONResponse` 内部的 `json.dumps` 会直接报 `TypeError`。

目前 `fail()` 的 `data` 默认是 `None`，暂时不会触发。但只要哪天往失败响应里塞带 datetime 的 data，就会炸。

**建议**：统一改用 `model_dump(mode="json")`：

```python
return JSONResponse(content=fail(...).model_dump(mode="json"))
```

### 2. JSONResponse 没有设置 status_code

```python
# 现状：HTTP 状态码永远是 200，业务码塞在 body 的 code 里
return JSONResponse(content=fail(msg=exc.detail, code=exc.status_code).model_dump())
```

`JSONResponse` 没传 `status_code` 参数，所以 HTTP 层永远返回 200，真正的状态码只体现在响应体的 `code` 字段。如果希望 HTTP 状态码也准确（利于网关、监控、前端拦截器判断），应补上：

```python
return JSONResponse(
    status_code=exc.status_code,
    content=fail(msg=exc.detail, code=exc.status_code).model_dump(mode="json"),
)
```

`global_err_handler` 同理，应显式传 `status_code=HTTPStatus.INTERNAL_SERVER_ERROR`。

---

## 四、小结

| 关注点       | 现状                   | 状态   |
| --------- | -------------------- | ---- |
| 业务异常处理    | `http_err_handler`   | 已实现 |
| 服务器异常兜底   | `global_err_handler` | 已实现 |
| datetime 序列化 | `model_dump()` 有隐患 | 待改进 |
| HTTP 状态码  | 失败响应恒为 200           | 待改进 |
