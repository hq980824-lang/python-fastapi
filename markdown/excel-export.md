# Excel 导出文章复盘（教学版）

> 把数据库里的文章导出成 .xlsx 文件，触发浏览器下载。
> 实现时间：2026-06-24
> 核心新知识点：**怎么把生成的文件「流」给浏览器下载**（跟返回 JSON 完全不同）。
> 配套：导入见 [[excel-import]]。

---

## 一、导出 vs 导入

| | 导入 | 导出 |
| --- | --- | --- |
| 方向 | Excel → 数据库 | 数据库 → Excel |
| openpyxl | `load_workbook` 读 | `Workbook()` 写 |
| 难点 | 脏数据、对应、校验 | **把文件流给浏览器下载**（响应类型/响应头） |

导出整体比导入简单（不用处理脏数据），唯一的新东西是「返回文件」这种响应模式。

---

## 二、查数据：单独写「查全部」方法，别硬复用分页

导出要**全部**数据，但项目的 `get_all` 强制要 `PageQuery`。**不要传假分页参数**（如 `size=10000`）去 hack 复用——语义不清。单独写：

```python
async def get_all_for_export(self, db: AsyncSession):
    stmt = (
        select(PostDB)
        .options(selectinload(PostDB.author))   # 预加载作者(导出要写作者邮箱,不然异步懒加载崩)
        .order_by(PostDB.id)                     # 排序,导出顺序稳定
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

**工程判断**：当「复用」要靠 hack（传假参数）才能实现时，不如分开写。导出和分页是两种需求，各管各的更清晰。

---

## 三、用 openpyxl 写 Excel

跟读相反——`Workbook()` 新建，`ws.append([...])` 一行行写：

```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.append(["标题", "内容", "作者邮箱", "状态"])     # 表头
for post in db_posts:
    ws.append([post.title, post.content, post.author.email, post.status.value])
```

要点：
- `post.author.email` —— 要写作者信息，所以第二步必须 `selectinload(PostDB.author)` 预加载。
- **`post.status.value`（坑）**：`post.status` 是枚举对象，直接写进去会显示成 `PostStatus.DRAFT`（枚举的名字）。要 `.value` 才得到干净的 `"draft"`（枚举的值）。
  - `PostStatus.DRAFT` = 枚举对象 → str 后是 `"PostStatus.DRAFT"`
  - `PostStatus.DRAFT.value` = `"draft"` ← 要的

---

## 四、核心：把 Excel 变成可下载的响应

### service：workbook → 内存字节流

```python
from io import BytesIO

buffer = BytesIO()      # 内存里的"假文件"
wb.save(buffer)         # Excel 写进字节流(不落硬盘)
buffer.seek(0)          # ★ 指针拨回开头,否则读出来是空
return buffer
```

**`seek(0)` 是高频坑**：`wb.save` 写完后，流的「读取指针」停在末尾。不拨回开头，controller 读到的是空字节，下载的文件打不开。

### controller：StreamingResponse 发给浏览器

```python
from fastapi.responses import StreamingResponse

@router.get("/export", dependencies=[Depends(get_current_user)])
async def export_posts(db: DbDep):
    buffer = await svc.export_to_excel(db)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=posts.xlsx"},
    )
```

三个关键（都是「返回文件」的新东西）：
- **`StreamingResponse`**：专门返回流/文件的响应类型（不是返回 JSON）。
- **`media_type`**：那一长串是 xlsx 的标准 MIME，告诉浏览器「这是 Excel」。
- **`Content-Disposition: attachment; filename=...`**：**触发下载**的关键头。`attachment` 让浏览器弹下载框，`filename` 指定下载文件名。没这个头浏览器会尝试直接显示（乱码）。

---

## 五、怎么验证（重点，容易困惑）

**Postman Body 区域看到一堆乱码 = 正常，不是错！**

二进制文件（xlsx 本质是 zip）在 Postman 的文本视图里就是乱码。判断成功看：
- **状态 200 + 有文件大小**（如 5.82 KB，说明真生成了内容）
- 乱码开头是 **`PK`** —— zip/xlsx 的标志性文件头，看到就说明是合法 xlsx。
- 乱码里有 `docProps/`、`xl/theme/` —— xlsx 的内部结构。
- 开头是 `PK` 而不是 `{"code":...}` —— 顺带证明项目的 `ResponseRoute` 没把文件流错误地包成 JSON。

**真正验证内容**：
- Postman：`Send` 旁下拉 → **`Send and Download`** → 存成 .xlsx → 用 Excel 打开看数据。
- 或代码层：把返回的 BytesIO 用 `load_workbook` 读回来，遍历 `iter_rows` 看内容。

---

## 六、踩坑 / 知识点小结

1. **Postman 乱码 = 正常**：二进制文件就这样，看 200 + PK 头判断成功，下载下来才能看内容。
2. **`buffer.seek(0)`**：BytesIO 写完指针在末尾，不拨回开头读到空。
3. **`status.value`**：枚举写进 Excel 要取 `.value`，否则显示 `PostStatus.DRAFT`。
4. **预加载 author**：导出带关联字段，查询要 `selectinload`，否则异步懒加载崩（见 [[excel-import]] 同类坑）。
5. **ResponseRoute 不包文件流**：项目的统一响应包装只处理 `application/json`，文件流的 media_type 不是 json，会被跳过——所以导出能正常返回二进制。
6. **导出别硬复用分页查询**：单独写 `get_all_for_export`，复用要 hack 时不如分开。

---

## 七、生产级可继续优化（选做）

- **导出限量 / 支持过滤**：大数据量一次导全部会内存爆、请求超时。生产常加上限或按条件导。
- **分批查 + 流式写**：超大数据量时，查一批写一批，不一次性全加载进内存。
- **异步后台任务**：超大导出做成后台任务、生成后给下载链接，避免请求超时（对应清单 #19）。

---

## 八、待办

- 把 model 升级成 SQLAlchemy 2.0 的 `Mapped["UserDB"]` 写法 —— 解决 `post.author` 类型推断不出（白色无补全）的问题，也是更现代的写法。
