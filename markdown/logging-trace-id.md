# 结构化日志 + Trace ID 中间件复盘

> 把全站 `print` 升级为结构化 JSON 日志，并给每个请求注入 Trace ID，让一次请求的所有日志能串成一条线。
> 实现时间：2026-06-22

---

## 一、为什么要做

| 改造前 | 改造后 |
| --- | --- |
| lifespan 里一堆 `print`，纯文本 | 标准库 `logging` 输出一行 JSON |
| 上服务器只能 `journalctl` 看一坨文本，难检索 | JSON 可被采集系统（ELK / 阿里云 SLS / Loki）按字段检索 |
| 多条日志之间无法关联属于哪个请求 | 每条日志带 `trace_id`，按 ID 能捞出一个请求的全部日志 |

核心价值：**出问题能定位**。结构化是为了机器能检索，Trace ID 是为了把散落各处的日志归到同一次请求。

---

## 二、技术选型

最终选 **标准库 `logging` + 自写 JSON Formatter**，没用 loguru / structlog。

| 方案 | 取舍 |
| --- | --- |
| 标准库 `logging`（采用） | 零依赖、与 uvicorn/SQLAlchemy 同体系、原理透明 |
| loguru | API 爽但多依赖，且和 uvicorn 自带 logging 是两套，要桥接 |
| structlog | 最专业但概念多，对当前规模偏重 |

结论：当前规模标准库够用，迁移成本低，等真嫌烦了再换。

---

## 三、四个组成部分

### 1. JSON Formatter（`src/common/logger.py`）

继承 `logging.Formatter`，重写 `format()` 把日志记录拼成一行 JSON：

```python
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": trace_id_var.get(),   # 从 contextvar 读当前请求 ID
        }
        if record.exc_info:                   # 有异常就带堆栈
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)   # 中文不转义
```

要点：
- `ensure_ascii=False` 让中文正常显示，不变成 `\uXXXX`
- `record.exc_info` 分支：配合 `logger.exception()` 自动带堆栈，排查报错关键

### 2. Trace ID 的存储：contextvars（`src/common/context.py`）

```python
import contextvars
trace_id_var = contextvars.ContextVar("trace_id", default="-")
```

`contextvars` 能在一次异步请求的上下文里存值，各处（controller / service）都能取到，且**并发请求之间互不串味**。默认 `-` 表示"不在请求上下文里"（如启动期日志）。

这是整套设计最巧的一环：**只要在请求上下文里打日志就自动带 trace_id，业务代码一行都不用改。**

### 3. Trace ID 中间件（`src/common/middleware.py`）

```python
class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16]
        trace_id_var.set(trace_id)            # 存进 contextvar，本次请求全程可读
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id   # 回写响应头，方便对账
        return response
```

要点：
- `BaseHTTPMiddleware` 来自 **Starlette**（FastAPI 底层），随 FastAPI 装好，无需额外依赖
- 优先沿用上游传入的 `X-Trace-Id`（以后接 Nginx 可做全链路同 ID），没有才自己生成
- 响应头回写，前端/排查时能拿到对应 ID

### 4. 统一初始化（`setup_logging()`）

```python
def setup_logging():
    handler = logging.StreamHandler()         # 输出到控制台，systemd 下被 journalctl 收走
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()                      # 清默认 handler，避免重复打
    root.addHandler(handler)
    root.setLevel(logging.INFO)
```

在 `main.py` 里 **app 创建之前**调用，并注册中间件：

```python
setup_logging()
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.add_middleware(TraceIDMiddleware)
```

---

## 四、数据流

```
请求进来
   ↓
TraceIDMiddleware: 生成/沿用 trace_id → trace_id_var.set(...)
   ↓
controller / service 里 logger.info(...)
   ↓
JsonFormatter: trace_id_var.get() 读出当前 ID，拼进 JSON
   ↓
输出一行 JSON 日志（带 trace_id）
   ↓
响应返回，头里带 X-Trace-Id
```

---

## 五、踩坑记录

1. **替换 print 时把 `raise SystemExit` 弄丢了**：lifespan 里 Redis/MySQL 连不上原本要终止启动，改 `logger.error` 时只剩日志没了 `raise`，导致"带病也能启动"。修复：log 完补回 `raise SystemExit`。**日志只是记录，不替代控制流。**
2. **中间件写好了忘了挂**：`TraceIDMiddleware` 定义完没在 `main.py` 里 `add_middleware`，导致 trace_id 永远是默认 `-`。定义 ≠ 生效，必须注册。
3. **测 formatter 时 `handlers[0]` 报 IndexError**：根 logger 默认可能没有 handler。测试应自建一个干净 logger + handler 挂 formatter，别假设根 logger 已有 handler。

---

## 六、验证结论（实测）

- lifespan 6 条日志全部 JSON 化，中文正常、字段齐全
- `/health` 响应头 `x-trace-id` 为 16 位 hex；传入自定义 `X-Trace-Id` 被原样沿用
- 上下文内日志带请求 ID、上下文外为默认 `-`，符合预期
- 启动期日志 trace_id 为 `-`（正确：请求之前无上下文）

---

## 七、遗留缺口（后续）

- **uvicorn 访问日志仍是纯文本**：`uvicorn` / `uvicorn.access` 两个 logger 未接管，要全站统一 JSON 需单独处理
- **业务代码尚未铺日志**：目前只有 lifespan 在打，service / controller 关键路径（登录、建用户等）还没加 `logger.info`
- **无日志落盘 + 轮转**：现靠 journalctl，未配置写文件 + 按大小/时间轮转
- **日志级别未按环境切换**：dev / prod 同级别，生产可调高到 WARNING 减噪
