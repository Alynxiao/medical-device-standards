# 医械标准数据源：可用接口与分页坑

以下参数均为实测可用。站点改版时按最后一节重新探，不要硬猜参数名。

## 1. 标管中心·器械标准目录库（主表）

- 入口：`https://app.nidc.org.cn/biaogzx/qxqwk.do`
- **旧域名 `app.nifdc.org.cn` 已连不上，标管中心整套已迁到 `app.nidc.org.cn`**，换域名即可。
- 只能用 POST 带条件：`qxqwk.do?formAction=list&istiaojian=3`
  - 参数：`index`（页码）、`pageSize`（**最大 500，实测生效**）、`bzml`（`20210406a001`=通用技术领域 / `20210406a002`=专业技术领域）、`chalbid`（标准性质 YY/YY-T/GB/GB-T/GB-Z）、`chabiao`（编号）、`chaname`（名称）、`bzsyfw_s`（适用范围）、`bzmlone`/`bzmltwo`（一/二级目录）
  - **少了 `istiaojian` 或改成 GET，条件全部失效**，服务器静默返回默认那一页——状态码 200、页面正常，传什么参数结果都一样。
  - 翻页可 GET `&index=&pageSize=`，但必须先用 POST 设过条件（Struts + session）。
- 返回 GBK 编码 HTML，每行 11 个 `td`：序号 / 目录名称 / 一级目录 / 二级目录 / 标准编号 / 标准名称 / 批准日期 / 实施日期 / 实施状态 / 修改单信息 / 操作。
  - 每个 `td` 的显示文本都被截断，**全文在各自的 `span title=` 属性里**。要按列逐个 `td` 取 title，**不要在整行 `findall('span title')` 之后按序号取**——一行里有 4 个 title（目录名称 / 一级目录 / 二级目录 / 标准名称），按序号取会把一级目录名当成标准名称。
  - 每行带 `qxqwk.do?formAction=view&id=<id>`，这就是「点标题跳官方页」的链接。
- 条数量级（判断是否翻到底）：通用技术领域约 240 条、专业技术领域约 1,900 条，合计 2,100 上下。

## 2. 标准信息平台·行业标准备案库

- 列表：`https://hbba.sacinfo.org.cn/stdList`（bootstrap-table，服务端分页）
- **取数接口：POST `https://hbba.sacinfo.org.cn/stdQueryList`**，`Content-Type: application/x-www-form-urlencoded`
  - 参数：`current`（页码，从 1 起）、`size`（100 可用，越大越快）、`key`、`ministry`（`yjj`=国家药监局）、`industry`、`pubdate`、`date`、`status`（`[]` 或 `["现行"]`）
  - 返回 JSON：`{total, records:[{pk, code, chName, status, issueDate, actDate, chargeDept, industry, recordNo}]}`，日期是毫秒时间戳；**详情页 = `/stdDetail/<pk>`**
  - 直连可行，不需要 cookie，也不需要 scrapling。
- 页面上「国家药监局 (N)」括号里的数字只是**现行**数，接口 total 是含废止的全量，两个数别混。
- 本库只有 `code / chName / status / 日期 / 备案号`，**没有分类号、没有国标**。
- `issueDate` / `actDate` 是**东八区零点**的毫秒时间戳。按 UTC 格式化会整批早一天（列表页写 2026-08-24，转出来是 2026-08-23），必须用 `timezone(timedelta(hours=8))`。

## 3. 标管中心·标准草案征求意见

- 列表：`https://app.nidc.org.cn/biaogzx/dataGkZqyj.do?formAction=listHbbp&type=bzca`（`type=nlx` 是拟立项，不收）
- 分页：**GET `&index=N&pageSize=N`**，默认每页 10 条。
- 总条数只在页面内联脚本里：`new Pagination(297, 10, 1, "dataGkZqyj.do?formAction=listHbbp&type=bzca")` —— 第一个参数就是总数，**对账认这个数**。
- 单条详情：`dataGkZqyj.do?formAction=viewNotice&id=<id>`，不需登录；表里每项带 `viewZqyj&id=`（草案页）和 `openFileById&fileId=`（草案 PDF）。
- **列表只保留近三年**，更早的在这个栏目里找不到。
- 正确入口从 `www.nidc.org.cn/nifdc/bshff/ylqxbzhgl/index.html` 的「标准草案征集意见」点进来，自己拼 formAction 会撞 500（`login.do` 那套要登录）。

## 4. 国标检索（只补查，不做主线）

- `https://std.samr.gov.cn/gb/search/gbQueryPage?searchText=<词>&pageNumber=1&pageSize=10` 返回 JSON：`{total, rows:[{C_STD_CODE, C_C_NAME, STD_NATURE, ISSUE_DATE, ACT_DATE, STATE, id}]}`
- **`searchText` 只匹配名称；`ccsCode` / `icsCode` / `C_STD_CODE` 等分类参数发了也不生效**（照样返回全库数万条）——要「全部医械国标」不要走这条路，直接用标管中心目录库（那里带国标）。

## 5. 全国团体标准信息平台（只探过，未入库）

- 列表页：`https://www.ttbz.org.cn/standard.html`（Vue + axios 单页，直接拼 `StandardManage/StandardList` 之类路径会「资源不存在」）。
- **取数接口：POST `/cms-proxy/ms/portal/standardInfo/getPortalStandardList`**，表单编码。
  - 参数：`pageNo`（从 1 起）、`pageSize`、`standardStatus`（1=现行）、`standardTitleCn`（按名称模糊搜，**不是** `name` / `keyword` / `title`，发错了静默返回全库不报错）、`standardNo`（按编号搜）。
  - 返回 `{result, code, data:{total, rows:[...]}}`，行字段：`standardNo`、`standardTitleCn`、`organName`（发布团体）、`standardStatus/standardStatusName`、`publishDate`、`implementDate`、`abolishDate`、`icsl1Name`、`ccsl1Name`、`standardUniqueId`。
- **未登录硬门槛：`total` 一律被截断成 100，第 11 页返回 0 条**，`pageSize=200` 也只回 100 条。全库实际十余万项（列表页显示 123410）。所以拿不到真实总数，也就无法对账——不要拿「抓了 100 条」当全量。
- 要全量只有两条路：登录账号，或按发布团体（`organName` / `organCode`）逐个切片，每家每页 ≤100 条。做之前先确认收录范围，别默认全收。
- 字段名探法：hook `XMLHttpRequest.prototype.send` 记录表单体，再用同步 XHR 循环试候选参数名、比对返回的 `data.rows[0]` 是否真的被过滤（`total` 恒为 100，只能看首行变没变）。

## 站点改版时怎么重新拿接口

1. 浏览器里 hook `fetch` 和 `XMLHttpRequest.prototype.open/send`，再点一次筛选或翻页，真实请求和参数就打出来了；
2. 没有请求说明是整页提交：去内联 `<script>` 里搜 `bootstrapTable` / `url:` / `Pagination(` / `location.href`，参数名和总数都在那儿；
3. 该站分页组件约定：GET `?&index=N&pageSize=N`，条件则 POST 到 `<xxx>.do?formAction=...`；
4. **不要在浏览器 `js()` 里跑十几轮的循环抓取**——CDP 求值默认 5 秒就超时，且变量随页面跳转丢失。探明参数后改用 curl / Python 直连，上千条十几秒就完。
