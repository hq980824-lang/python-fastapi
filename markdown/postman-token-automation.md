# Postman Token 自动化配置（教学版）

> 解决痛点：每个接口手动加 Authorization 头、token 过期后挨个改。
> 目标：登录一次自动写入 token，所有接口自动继承，过期重新登录即全盘刷新。
> 整理时间：2026-06-23

---

## 一、为什么要这么做

接口加了 JWT 鉴权后，用 Postman 测试会遇到两个麻烦：

1. **每个接口都要手动加** `Authorization: Bearer <token>` 请求头——重复劳动。
2. **token 过期后**要把每个接口的头挨个改一遍——噩梦。

解法分两层：
- **第一层**：Collection 级统一 Auth + 变量，所有请求自动继承，改一处生效。
- **第二层**：登录请求用脚本自动把返回的 token 写进变量，连「改一处」都省了。

---

## 二、第一层：Collection 变量 + 统一 Auth

**核心认知**：不要在每个请求里单独写 Authorization 头，在 Collection（集合）层级设一次，子请求自动继承。

### 步骤

1. **打开 Collection 设置**：左侧单击 Collection 名（最顶层那行，不是子文件夹），主区域打开设置页，顶部出现 Authorization / Variables / Scripts 等标签。

2. **配 Authorization**：
   - 点 `Authorization` 标签
   - Auth Type 选 **Bearer Token**
   - Token 框填变量占位符：`{{token}}`（连花括号一起打）
   - 保存（Ctrl+S）

3. **配 Variables**（存 token 的地方）：
   - 点 `Variables` 标签
   - 加一行：Variable = `token`，值先留空（等登录脚本自动填）
   - 保存

4. **子请求设继承**：每个接口的 Authorization → Type 选 **Inherit auth from parent**（从父级继承）。新建请求默认就是继承，一般不用动。

配完效果：所有请求自动带 `Authorization: Bearer {{token}}`，一个头都不用手填。

---

## 三、第二层：登录后自动写入 token

让登录接口在拿到响应时，自动把 token 存进 `{{token}}` 变量。

### 前置：先看清登录接口的真实返回结构

**这一步必须先做**，因为脚本要按真实结构取值。本项目 `/auth/login` 返回：

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {
    "token": "Bearer eyJhbGci..."
  }
}
```

两个关键点：
- token 字段路径是 `data.token`（不是 `data.access_token` 之类，**别照抄教程，看自己的**）。
- 值里**已带 `Bearer ` 前缀**。

### 脚本

在 **login 请求**的 `Scripts` 标签（新版 Postman 叫 Scripts → Post-response，老版叫 Tests）里写：

```javascript
const res = pm.response.json();
if (res.data && res.data.token) {
    // 去掉开头的 "Bearer " 前缀，只存纯 token
    const token = res.data.token.replace(/^Bearer\s+/, "");
    pm.collectionVariables.set("token", token);
    console.log("token 已更新:", token);
}
```

逐行说明：
- `res.data.token` —— 按真实结构取值。
- `.replace(/^Bearer\s+/, "")` —— **关键**：去掉 `Bearer ` 前缀。因为 Collection 的 Auth 类型是 Bearer Token，Postman 会**自己加** `Bearer `。若把带前缀的值存进去，最终变成 `Bearer Bearer xxx`，鉴权失败。
- `pm.collectionVariables.set(...)` —— 写进 collection 变量。

---

## 四、踩坑记录

1. **`Bearer Bearer` 重复前缀**（最易踩）：登录返回值自带 `Bearer `，而 Postman Bearer Token 类型也会自动加前缀。必须在脚本里 `replace` 去掉，只存纯 token。
2. **token 字段路径照抄教程**：不同项目返回结构不同，必须先实际调一次登录看 JSON，确认字段名和层级。本项目是 `data.token`。
3. **变量作用域**：用 `pm.collectionVariables`（集合级），不要用 `pm.environment`（环境级）除非你建了 Environment。和第二步建变量的位置要一致。
4. **找不到 Scripts 标签**：新版 Postman 是 `Scripts → Post-response`，老版本叫 `Tests`，是同一个东西。

---

## 五、最终工作流

1. token 过期 → 重新 Send 一次 **login** 请求。
2. 脚本自动把新 token 写进 `{{token}}`。
3. 其他所有接口立即可用新 token，**什么都不用手动改**。

一次调登录，全盘刷新。

---

## 六、更快的替代方案：Swagger /docs

只是开发期快速自测，不用 Postman 也行：

- 项目用了 `HTTPBearer`，FastAPI 自动在 `/docs` 生成 **Authorize** 按钮。
- 点 Authorize 填一次 token，页面上**所有接口**调用自动带 token。

**怎么选**：
- 快速自测 → `/docs` 的 Authorize，最快。
- 长期维护接口集合 / 写测试 / 团队共享 → Postman（配一次终身受益，所有项目通用）。

---

## 七、相关

- JWT 鉴权实现见 [[redis-auth]]（HTTPBearer 提取 token、`get_current_user` 依赖）。
- 鉴权设计（401 vs 403、哪些接口公开/保护）见用户模块 controller。
