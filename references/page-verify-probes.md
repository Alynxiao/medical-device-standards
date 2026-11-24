# 出页面后的验证探针

改完 `templates/page.html` 或 `build_page.py` 之后，按这套顺序跑一遍。每段独立可复制，在浏览器控制台（或自动化工具的 JS 执行入口）里跑。

**照例先重置状态，再验。** 上一步留下的筛选会让下一步看起来像 bug。

## 1. 打开页面（中文路径要编码）

```python
import urllib.parse
url = "file:///D:/…/medical-device-standards/" + urllib.parse.quote("医械标准库_2026-11-20.html")
new_tab(url); wait_for_load()
```

## 2. 整体断言：结构 + 渲染 + 排序

```js
(() => {
  const rows = filtered();
  // 排序校验：同状态组内发布日期必须不增
  let bad = [], prev = null, prevSt = null;
  for (let i = 0; i < rows.length; i++) {
    const st = rows[i].status, d = (rows[i].issue || "").replace(/\D/g, "").slice(0, 8);
    if (prev && st === prevSt && d && prev.d && d > prev.d) bad.push(i + ":" + rows[i].code);
    prev = {d}; prevSt = st;
  }
  return JSON.stringify({
    total: rows.length,
    卡片数: document.querySelectorAll("#list .card").length,   // 必须是 50，0 = JS 抛错了
    pills: [...document.querySelectorAll(".pill")].map(p => p.textContent.trim()),
    panels: [...document.querySelectorAll(".ptitle")].map(p => p.textContent),
    mine: [...document.querySelectorAll("#f_mine .btn")].map(b => b.textContent.trim()),
    逆序违例: bad.length,
    首六条: rows.slice(0, 6).map(r => r.status + "|" + r.issue + "|" + r.code)
  }, null, 1);
})()
```

卡片数 0 而 `total` 正常 → 不是数据问题，是模板 JS 炸了。用下面这段定位：

```js
(() => { try { render(); return "ok"; } catch (e) { return e.message + "\n" + e.stack; } })()
```

## 3. 收藏 / 最近看过全链路

```js
// a. 清场 + 重载（只删存储不重载，内存里的 FAV/RECENT 还在）
localStorage.removeItem("mdstd_fav"); localStorage.removeItem("mdstd_recent");
// b. 点第一条星标
const c = document.querySelectorAll("#list .card")[0];
c.querySelector(".fv").click();
// 注意：render() 重建了 DOM，c 已是旧节点——要看新节点的星标
[...document.querySelectorAll("#f_mine .btn")].map(b => b.textContent.trim());  // ★ 收藏1
localStorage.getItem("mdstd_fav");                                            // ["GB/Z 169-2026"]
// c. 点标题记最近看过（会新开标签页，当前页不变）
document.querySelector("#list .card .t a").click();
// d. 重载页面，确认持久化后计数仍是 1/1，且「最近看过」视图有 1 条
```

验完必须清干净，别把测试收藏留在使用者浏览器里：

```js
localStorage.removeItem("mdstd_fav"); localStorage.removeItem("mdstd_recent");
```

## 4. 顶栏胶囊 / 主题二级

```js
state.mine=""; state.status=""; state.nmpa=""; state.cat1=""; state.page=1; render();
const pills = [...document.querySelectorAll(".pill")];
pills[2].click();                                  // 即将实施
// 断言：列表 50 条、面包屑「状态：即将实施 ×共 N 条」、首条状态一致
pills[0].click();                                  // 回全部
[...document.querySelectorAll("#f_area .btn.lvl1")].find(x => x.textContent.includes("04 骨科")).click();
// 断言：二级目录出现在 .sub 里，且二级计数加和 = 一级总数
```

## 4b. 按用途 / 材料种类 / 适用范围（改过 role_of 或卡片模板必跑）

```js
// 先把所有筛选清干净（直接改 state，不要 forEach click——render() 会重建 DOM）
state.q=""; state.role=""; state.mat=""; state.nmpa=""; state.cat1=""; state.status=""; state.mine=""; state.page=1; render();
const btns = () => [...document.querySelectorAll("#f_role .btn")];
btns().map(b => b.textContent.trim());          // 产品要求 N / 材料标准 N / 试验方法 N
btns().find(b => b.textContent.includes("材料标准")).click();
[...document.querySelectorAll("#f_role .sub .btn")].map(b => b.textContent.trim());
                                                 // 金属/高分子/陶瓷/天然生物源/其他，加和 = 材料总数
[...document.querySelectorAll("#f_role .sub .btn")].find(b => b.textContent.includes("金属材料")).click();
// 断言：卡片数 = 金属材料条数；抽 5 张卡的名字看有没有产品混进来（刃具/水门汀/试剂盒 都是产品）

// 适用范围：默认折叠一行，点击展开
const c = document.querySelector("#list .card"), sc = c.querySelector(".sc");
sc.className;                                    // "sc"
sc.click(); sc.className;                        // "sc open"，且高度变大（一行 → 多行）
```

**核心场景必验一条**：搜「髋关节」→ 找到 `YY 0118` → 展开适用范围，原文必须出现「金属、常规超高分子量聚乙烯、陶瓷材料」。这句话是「产品→材料」唯一的官方桥，它没出来就说明 scope 没入库或搜索没带上 scope。

搜索覆盖范围的验证：搜「超高分子量聚乙烯」应同时命中**材料标准本身**（`GB/T 19701.x`）和**产品标准**（名称里没有这四个字、但适用范围里写了的产品，如膝关节衬垫）。只命中材料标准 = 搜索还没带上 `r.scope`。

## 5. 截图

```python
cdp('Emulation.setDeviceMetricsOverride', width=1440, height=900, deviceScaleFactor=1, mobile=False)
capture_screenshot()
```

截图要能看到：左栏「我的」计数归零、顶栏四个胶囊、首屏是现行组最新发布的那几条、卡片星标在左侧。
