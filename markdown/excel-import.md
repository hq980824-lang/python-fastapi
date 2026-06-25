# Excel 批量导入文章复盘（教学版）

> 上传 Excel（含文章 + 作者邮箱），批量导入文章；作者按邮箱对应到用户，不存在则跳过；返回成功/失败汇总。
> 实现时间：2026-06-24
> 价值：比纯 CRUD 更真实——涉及文件上传、数据对应、脏数据处理、健壮性。

---

## 一、需求与设计决策

| 决策点 | 选择 | 理由 |
| --- | --- | --- |
| 作者用什么标识 | **邮箱** | users 表 email 唯一，无歧义（用名字会重名） |
| 作者不存在怎么办 | **跳过 + 记录** | 不中断整批，最后汇总失败原因 |
| 返回什么 | **成功数 + 失败数 + 失败详情（带行号）** | 用户能精确定位哪行错、为什么 |

---

## 二、依赖准备

```bash
pip install openpyxl          # 读 Excel
pip install python-multipart  # FastAPI 接收文件上传(UploadFile)必需
```

两个都要同步进 `requirements.txt`（否则 Docker/服务器缺依赖，见 [[deployment]] 踩坑）。

**知识点**：FastAPI 某些功能依赖「可选额外库」，缺了运行时才报错——`UploadFile` 缺 `python-multipart`、`EmailStr` 缺 `pydantic[email]`。报错信息会直接告诉你装什么。

---

## 三、文件上传：跟 JSON 不同

之前接口收 JSON（`payload: PostCreate`），文件要用 `UploadFile`：

```python
from fastapi import UploadFile

@router.post("/import", response_model=ImportResult, dependencies=[Depends(get_current_user)])
async def import_posts(file: UploadFile, db: DbDep):
    return await svc.import_from_excel(db, file=file)
```

- `UploadFile` 走 `multipart/form-data`，Swagger `/docs` 会显示上传按钮。
- 鉴权用 `dependencies=[Depends(get_current_user)]`：函数体用不到 current_user，只要求登录，放装饰器比塞参数更干净。详见 [[fastapi-depends-authorization]]。

---

## 四、核心逻辑（service）

```python
async def import_from_excel(self, db: AsyncSession, file: UploadFile):
    # 1. 文件类型校验(service 抛 ValueError,由全局 handler 转 400)
    if not file.filename.endswith(".xlsx"):
        raise ValueError("只支持 .xlsx 格式的文件")

    # 2. 读文件 → openpyxl
    content = await file.read()                 # UploadFile.read 是异步,要 await
    sheet = load_workbook(BytesIO(content)).active

    # 3. 一次读进列表,后续复用(避免遍历 sheet 两次)
    data = [list(row) for row in sheet.iter_rows(min_row=2, values_only=True)]

    # 4. 收集邮箱(保序去重 + 过滤空值)
    emails = list(dict.fromkeys([row[-1] for row in data if row[-1]]))

    # 5. 批量查作者,做成 {email: user} 映射表(避免 N+1)
    users = (await db.execute(select(UserDB).where(UserDB.email.in_(emails)))).scalars().all()
    email_to_user = {user.email: user for user in users}

    # 6. 遍历每行,分流到 待创建 / 失败
    to_create, errors = [], []
    for idx, row in enumerate(data, start=2):   # start=2:行号对齐 Excel(跳了表头)
        if len(row) < 3:
            errors.append({"行": idx, "原因": "列数不足"}); continue
        title, content, email = row[0], row[1], row[2]
        if not title:                            # 真值判断:空字符串是假值
            errors.append({"行": idx, "原因": "标题为空"}); continue
        author = email_to_user.get(email)        # 字典 .get 查不到返回 None
        if author is None:
            errors.append({"行": idx, "原因": f"作者不存在：{email}"}); continue
        to_create.append(PostDB(title=title, content=content, author_id=author.id))

    # 7. 空数据提示
    if not to_create and not errors:
        raise ValueError("文件中没有数据行")

    # 8. 批量入库 + 返回汇总
    db.add_all(to_create)
    await db.commit()
    return {"success": len(to_create), "failed": len(errors), "errors": errors}
```

### 关键设计点

- **批量查作者做字典映射**：不要逐行 `SELECT user WHERE email=x`（N+1，1000 行 = 1000 查询）。先收集所有邮箱，一次 `IN` 查回来，做成 `{email: user}` 字典，之后内存 O(1) 查。这是「批量对应」的经典套路。
- **`enumerate(data, start=2)`**：遍历同时拿行号；`start=2` 因为数据从 Excel 第 2 行起（表头是第 1 行），让报错的行号跟用户在 Excel 看到的一致。
- **卫语句 + continue**：用「不满足就 continue 跳过」的扁平写法，而不是层层嵌套 if。
- **service 抛 ValueError，不抛 HTTPException**：分层——业务层抛业务异常，全局 `value_err_handler` 转成 400。

---

## 五、用到的 Python 语法（JS 程序员重点）

| 语法 | 说明 | JS 对比 |
| --- | --- | --- |
| 列表推导式 `[x for x in ...]` | 转换/收集 | `.map()` |
| 字典推导式 `{k: v for ...}` | 做映射表 | `Object.fromEntries(...)` |
| 带过滤推导式 `[... if cond]` | 边转边筛 | `.filter().map()` |
| `dict.fromkeys(list)` | **保序**去重（`set` 会乱序） | `[...new Set()]`（不保序） |
| 元组解包 `a, b, c = row` | 拆元组到变量 | 数组解构 `const [a,b,c]=row` |
| `enumerate(x, start=2)` | 带序号遍历 | 手动维护 index |
| `.get(key)` | 查不到返回 None，不报错 | `obj[key]` 返回 undefined |
| 真值判断 `if not title` | 空字符串/空列表/None/0 都是假值 | **空数组在 JS 是真值，Python 是假值** |
| `row[-1]` | 负索引取最后一个 | `arr.at(-1)` |

---

## 六、踩坑记录（全是 JS 转 Python 的真实坑）

1. **缩进决定逻辑归属（最坑）**：`continue` 少缩进一级，从「属于 if」变「属于 for」，导致每轮无条件跳过，后面代码变灰（死代码）。Python 没有 `{}`，全靠缩进——缩进错一级，逻辑全变。**JS 用花括号不会有这问题。** 工具（ruff format）也修不了，因为语法合法、只是逻辑错。
   - 排查技巧：代码莫名**变灰**＝永远执行不到，查上方是否有无条件 return/continue 或缩进脱块。
2. **字典 vs 集合的冒号**：`{"k": v}` 是字典（冒号），`{"k", v}` 是集合（逗号）。写成逗号会报「集合内不允许键值对」。
3. **`.xlxs` 拼写**：把 `.xlsx` 敲反成 `.xlxs`，逻辑没错但永远匹配不上，正常文件反被拒。隐蔽。
4. **解包数量不匹配**：`title, content, email = row` 若某行列数不足会崩。加 `if len(row) < 3` 防御。
5. **漏 await**：`import_from_excel` 是 async，controller 调用漏 `await` → 返回协程对象，函数体不执行。
6. **async vs sync 判断**：`db.add_all()` 同步（纯内存登记），`await db.commit()` 异步（真连数据库）。法则：**碰外部资源（DB/网络/文件）就 await，纯内存就不用**。类比 git：add=本地暂存，commit=提交落定（但 SQLAlchemy 的 commit 还要连数据库，所以异步）。
7. **虚拟环境要激活**：新终端 `make dev` 报 `No module named 'redis'`＝用了系统 Python。先 `source .venv/bin/activate` 看到 `(.venv)`。Docker 的 mysql/redis 也要先 `docker compose up -d mysql redis`。

---

## 七、健壮性清单（从「能跑」到「生产级」）

- ✅ 文件类型校验（非 .xlsx 拒绝）
- ✅ 列数不足的行跳过 + 记录
- ✅ 空标题 / 作者不存在跳过 + 记录
- ✅ 空表提示
- ✅ 失败汇总带行号（用户可定位）
- ✅ 批量查作者（避免 N+1）
- ✅ 返回值 schema 化（ImportResult）

---

## 八、工具：ruff（Python 的 Prettier + ESLint）

```bash
ruff format src/          # 格式化(缩进/空格/空行) ≈ Prettier
ruff check --fix src/     # 查问题+自动修(废 import 等) ≈ ESLint --fix
ruff format --diff src/   # 预览不实改
```

从别处复制代码缩进乱了，`ruff format` 一键修。建议 VS Code 装 Ruff 扩展开「保存时格式化」，体验同前端 Prettier。

---

## 九、可继续优化（选做）

- 合并两次遍历（已做：用 `data` 列表复用，只读 sheet 一次）。
- 大文件分批 commit（几万行时一次 commit 压力大）。
- 导入做成异步后台任务（超大文件，避免请求超时）——对应清单 #19 后台任务。
