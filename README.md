# 51kim.com 本地镜像

对 https://www.51kim.com/  （氪主页）的逆向分析与本机部署版本。

## 启动

双击 `start.bat`，或在目录下运行：

```bash
python server.py 8080
```

然后浏览器打开 **http://127.0.0.1:8080/**

（服务当前已在后台运行于 8080 端口）

## 账号系统（SQLite 本地登录）

右上角「个人中心」已改为**本地账号登录**，数据存于 SQLite 数据库 `users.db`（首次启动自动创建，密码用 PBKDF2 加盐哈希存储）：

- 点击「个人中心」图标 → 弹出登录/注册面板
- 支持 **注册、登录、退出登录、修改密码**
- 登录状态通过 HttpOnly Cookie 会话保持，刷新页面不掉线
- 会话有效期 7 天
- 首次使用请先点「注册」创建本地账号

用户可管理自己的数据；数据库文件 `users.db` 可直接用 SQLite 工具查看。

## 管理后台（SQLite 数据库可视化管理）

浏览器打开 ** http://127.0.0.1:8080/admin **，使用管理员账号登录：

- 账号：`admin`
- 密码：`123456`
- 账号与会话存于 `users.db` 的 `admin_users` / `admin_sessions` 表，密码同样使用 PBKDF2 加盐哈希，Cookie 为 HttpOnly。
- 首页「个人中心」面板里也添加了「后台管理」入口。

后台支持对 `site_data.db` 和 `users.db` 做以下操作：

| 数据表 | 支持操作 |
|--------|----------|
| 分类标签 `categories` | 查看、新增、编辑、删除、显示/隐藏、启用/停用 |
| 站点分组 `groups` | 查看、新增、编辑、删除、显示/隐藏、启用/停用 |
| 站点条目 `sites` | 查看、新增、编辑、删除、显示/隐藏、启用/停用 |
| 顶部图标 `header_icons` | 查看、新增、编辑、删除、显示/隐藏、启用/停用 |
| 注册用户 `users` | 查看、新增、编辑、删除、重置用户密码 |

侧边栏底部有「修改管理员密码」入口，修改时需输入当前密码并二次确认新密码；密码使用 PBKDF2 加盐哈希保存。修改后请用新密码登录后台。

说明：

- `显示(visible)=否` 或 `启用(enabled)=否` 的条目立即从首页数据中排除，刷新主页即可看到效果。
- 主键字段（分类 ID、分组键、图标 ID、用户 ID 等）在编辑时不可修改，避免破坏关联关系；新增时由数据库自动分配。
- 删除注册用户时会同时清理该用户的登录会话。
- 所有修改实时写入 SQLite，无需重启服务；如需恢复站点初始数据，可运行 `python manage_sitedb.py rebuild`。

## 站点数据（SQLite 本地数据库）

主页的**站点导航数据**（分类标签 + 站点网格）和**右上角 4 个图标**已从静态文件迁移到 SQLite 数据库 `site_data.db`（首次启动自动从抓取数据生成）。服务器每次请求都从数据库读取并实时编码为原站的 `SplitSet` 格式返回，因此**直接改数据库即可改变页面内容，无需改代码、无需重启**（刷新浏览器即可）。

数据库表结构：

| 表 | 内容 |
|----|------|
| `categories` | 13 个分类标签（常用/生活/… + 外网 6 个），含内网/外网分组与排序 |
| `groups` | 每个分类下的站点分组（共 118 个） |
| `sites` | 站点明细：名称、网址、图标路径（共 613 个） |
| `header_icons` | 右上角 4 个图标（个人中心/壁纸中心/告诉朋友/信息中心）+ 返回按钮，含标题、图标样式、类型、排序、启用状态 |

每张表都含 `enabled`（启用/停用）和 `visible`（显示/隐藏）字段；只有两者都为 1 的条目会出现在首页。旧数据库在启动时会自动补齐这两列，已有数据保持原样。

命令行管理工具 `manage_sitedb.py`：

```bash
python manage_sitedb.py list categories          # 查看所有分类
python manage_sitedb.py list sites 230           # 查看「生活」分类的站点
python manage_sitedb.py list icons               # 查看右上角图标
python manage_sitedb.py add-site 230 231 "新站" "https://example.com/" "kimzhuye/xx/xx/icon.png"
python manage_sitedb.py rename-site 1 "新名称"    # 按站点 id 改名
python manage_sitedb.py del-site 1               # 按 id 删除
python manage_sitedb.py set-icon 1 title "新标题" # 改图标标题（1=user_center）
python manage_sitedb.py rebuild                  # 从原始抓取数据重建数据库
```

也可直接用任意 SQLite 工具（如 DB Browser for SQLite）打开 `site_data.db` 编辑。编码/解码逻辑在 `splitcodec.py`，数据库→前端配置的生成在 `db_config.py`（经校验与原始数据逐字节一致）。

## 网站逆向分析结论

- **服务端**：Microsoft IIS，页面为纯静态 HTML 外壳。
- **前端**：jQuery + 自研 `kim.zhuye.front.*` 组件库（压缩后 JS 约 440KB，CSS 约 120KB），从 CDN `res.zhuye.kim` 加载。
- **数据编码**：站点导航数据、分类、配置均以「长度前缀字符串」内嵌在 HTML 里，由 `SplitSet / SplitTable / SplitDataRow` 解析器解码：
  - 3 位长度 + 内容（数据行字段）
  - 6 位长度 + 内容（行）
  - 4 位长度 + 内容（行组）
  - 10 位长度 + 内容（表）
  - `cfg` 字段从索引 2/3/4/5 分别读取 serverURI、metaSearchURI、resourceServerURI、resourceServerAPIURI。
- **资源域名**：图标/背景图统一在 `https://res.zhuye.kim/<资源ID>`，资源 ID 形如 `kimzhuye/xx/xx/xxx.png`、`group1/kimzhuye/...jpg`。
- **外部依赖**：百度统计、天气/公告/主题等 `/front/*` AJAX 接口。

## 本地化改造

- 全部 **708 个静态资源**（119 个首页图标 + 497 个分类图标 + 背景图 + CSS/JS/主题资源）已下载到 `res/`，总计约几 MB。
- HTML 中 `cfg` 的 4 个 URI 字段改为本机地址，CSS/JS 引用改为本地路径，移除百度统计与 IE 兼容脚本。
- `server.py` 对 `/front/*` 接口返回成功响应；分类接口 `/front/site/get_list` 现在由 **`site_data.db` 数据库**提供 13 个分类的真实数据（服务器实时编码为 SplitSet 格式），并回显 `curReqMark`（JS 用它丢弃过期响应，缺失会导致分类切换无效）。右上角 4 个图标、初始分类标签(`scgd`)与默认站点列表(`csl`)同样从数据库读取并注入页面。`/meta-search` 重定向到百度搜索。
- 导航链接本身保持指向原网站（这是导航页的功能）。

## 问题修复记录

- **分类标签点击无内容**：初次部署时 `/front/site/get_list` 返回空数据，点击「生活/产品」等标签后站点列表为空。已从原站抓取 13 个分类的真实数据存入 `api/`，并修正 `curReqMark` 回显。
- **右上角绿色开关无效**：该开关是「内网/外网」站点列表切换（切到外网会显示 Youtube/Facebook 等，并切换搜索引擎为 Google）。外网分类数据来自 HTML 内嵌的 `csl` SplitSet，现已正常工作。
- **壁纸中心 / 告诉朋友 点击空白**：`/front/bgclass/get_list`、`/front/bgimg/get_list`、`/front/share` 三个接口原来返回空。已从原站抓取真实响应存入 `api/`，并下载壁纸/分享图标。告诉朋友显示全部分享渠道。
- **壁纸分类按钮（风景/素雅/唯美等）点击空白**：初次修复时误用了错误的 classId（12/14/15...），原站这些 ID 本身返回空。用浏览器实测原站点击各分类的真实请求后得到正确映射：动态=10、风景=2、素雅=4、唯美=5、纯色=6、静物=7、星空=8、城市=9、人物=11。已按正确 ID 重新抓取 9 个分类的壁纸数据（`api/bgimg_*.json`）并下载约 840 张壁纸图片。
- **个人中心登录**：原站用微博/微信 OAuth 登录，本地无法使用。已替换为 SQLite 本地账号系统（见上节）。
- **站点导航数据与右上角图标迁入 SQLite**：原先分类标签、613 个站点、右上角 4 个图标硬编码在 HTML/JS/JSON 中，不便修改。已全部导入 `site_data.db`，服务器按请求读取并实时编码；`splitcodec.py` 保证编码与原站逐字节一致（13 个分类 + `scgd`/`csl` 全部校验通过）。改数据库即改页面，无需重启。
- **管理后台**：新增 `/admin` 可视化管理界面，管理员 `admin/123456` 可对四类 SQLite 数据进行查看、新增、编辑、删除、显示/隐藏、启用/停用，无需手动写 SQL。

## 验证结果

用 Edge 无头浏览器实测：
- 页面标题、背景图、全部导航图标正常渲染
- 分类切换：生活 40 个站点、产品 41、设计 45、运营 46，均加载真实数据
- 绿色开关：切到外网显示 Youtube/Facebook 等 116 个站点，6 个外网分类均可切换，切回内网正常
- 壁纸中心：9 个分类全部可切换，各分类 30~151 张壁纸（合计约 609 张），图片全部加载成功、0 失败；告诉朋友：全部分享渠道正常显示
- 登录系统：注册 → 自动登录 → 刷新保持 → 改密码 → 退出 → 用新密码重新登录，全流程通过，0 错误
- 管理后台：`admin/123456` 登录；分类/分组/站点/图标/注册用户五个表格均正常加载（13/118/613/5/1 条）；搜索、新增、编辑、删除、显示/隐藏、启用/停用全部通过；停用 bilibili 后首页立即消失，恢复后立即出现；0 个 JavaScript 错误、0 个失败请求
- 用户管理：新增用户可用新密码登录；重置密码后旧密码失效、新密码生效；编辑昵称即时保存；删除用户后无法登录；管理员改密后立即生效并可改回原密码，全流程通过
- 本地图片请求全部成功，JavaScript 运行时错误 0 个

## 文件说明

| 文件 | 用途 |
|------|------|
| `index.html` | 本地化后的主页 |
| `admin.html` / `assets/css/admin.css` / `assets/js/admin.js` | 管理后台页面与样式逻辑 |
| `admin_db.py` | 管理员账号、管理员改密、会话、站点与用户数据库 CRUD、字段迁移 |
| `assets/css/home.min.css` | 原站 CSS（URL 已本地化） |
| `assets/js/home.min.js` | 原站 JS（默认域名已本地化） |
| `assets/css/local-auth.css` / `assets/js/local-auth.js` | 本地 SQLite 登录界面与逻辑 |
| `res/` | 镜像的静态资源（图标、背景、主题等） |
| `api/` | 原站抓取的真实接口数据（壁纸/分享；站点数据已迁入数据库） |
| `users.db` | SQLite 用户账号数据库（注册用户、用户会话、管理员账号与管理会话，首次启动自动创建） |
| `site_data.db` | SQLite 站点数据库（分类/站点/分组/右上角图标，首次启动自动生成） |
| `splitcodec.py` | SplitSet 编解码器（数据库→前端格式，逐字节一致） |
| `db_config.py` | 从数据库生成前端配置（scgd/csl/图标） |
| `build_sitedb.py` | 从抓取数据生成站点数据库 |
| `manage_sitedb.py` | 站点数据库命令行管理工具 |
| `favicon.ico` | 站点图标 |
| `server.py` | 本地服务器 + API + SQLite 认证 + 站点数据库驱动 |
| `download_assets.py` | 资源抓取脚本 |
| `build_local.py` | 本地化改写脚本 |
| `start.bat` | Windows 一键启动 |
