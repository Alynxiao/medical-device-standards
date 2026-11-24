# 标准正文可得性：谁给正文、入口怎么拼

做「这条标准点过去能不能看到正文」这类判断时看这一份。所有结论都实测过，不是推测。

## 一句话结论

| 来源 | 正文 | 入口 |
|---|---|---|
| 征求意见稿 | **有 PDF 全文** | 标管中心 `viewZqyj` 详情页，附件就在页面上 |
| 强制性国标 GB | **在线预览可看**（不能下载） | 国家标准全文公开系统 openstd |
| GB/T、GB/Z 未采标 | 在线可看 | openstd |
| GB/T、GB/Z 采标 | **无**（版权） | openstd 上明写「暂不提供在线阅读服务」 |
| YY、YY/T | **无** | 标管中心只有目录信息；正式文本要买或机构订阅 |

## 标管中心：目录页没有正文，征求意见页有

- 目录详情 `biaogzx/qxqwk.do?formAction=view&id=<32hex>` —— 只有 ICS、CCS、归口单位、起草单位、代替关系、采标情况。**没有任何正文或下载链接**，别指望在这里找 PDF。
- 征求意见详情 `biaogzx/dataGkZqyj.do?formAction=viewZqyj&id=<32hex>` —— 页面上挂两个附件：`本次征求意见稿` 与 `编制说明`，都指向 `dataGkZqyj.do?formAction=openFileById&fileId=<32hex>`。实测直接 curl 可得 PDF（1～1.4 MB，无需登录、无需 referer）。

### 抓附件链接的两个坑

1. **锚文本往往只剩 `.pdf`**。页面把文件名拆到旁边的单元格里，`<a>` 里只有 `.pdf` 三个字，靠「锚文本含『征求意见稿』」判断会全落空。**按表格列顺序取**：第一个 = 征求意见稿，第二个 = 编制说明；文字里真出现「说明」二字时才用它纠正。
2. **`fileId` 与页面 `id` 无关**，是另一套 32 位 hex，必须逐页抓，不能由 `id` 拼出来。
3. **整站 GB18030**，`raw.decode("gb18030")`。用 utf-8（尤其 `errors="ignore"`）会把中文吞成空串，既不报错也抓不到附件名。

## 国家标准全文公开系统（openstd）

按标准号检索，不需要先抓 hcno：

```
https://openstd.samr.gov.cn/bzgk/std/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=<urllib/encodeURIComponent 标准号>
```

结果页每行一个「查看详细」按钮，`onclick="showInfo('<32hex hcno>')"`；详情页是：

```
https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=<hcno>
```

### 谁有「在线预览」

| 类型 | 实测表现 |
|---|---|
| 强制性 GB（采标也算） | 有「在线预览」按钮，提示「采用了 ISO、IEC 等标准，涉及版权，**本系统仅提供在线阅读服务**」 |
| 推荐性 GB/T 采标 | 明确写「**暂不提供在线阅读服务**」 |
| 推荐性 GB/T 未采标 | 有在线阅读/下载 |

判据落在本地数据上就是 `adopt` 字段：**非空 = 采标 = 国标里看不到正文**（强制 GB 除外）。

### 两个施工细节

- 详情页的「在线预览」是 JS 绑定事件，`href`/`onclick` 都取不到；`Target.getTargets` 也看不到它另开的窗口。**不要指望自动化走完「点开预览」，给到 openstd 检索页就够了**，由人在那边点。
- `c.gb688.cn/bzgk/gb/showGb?type=online&hcno=...` 会因证书问题被浏览器拦成「您的连接不是私密连接」。它是旧域名，**不要把它当默认直链发出去**。
- openstd 首屏加载偏慢，`Page.navigate` 偶发 5s 超时；导航后多等 3～4 秒再读 DOM，超时了就重试一次，别当成站点不可用。

## 报数口径

主库 2,802 条时的分布：能看正文 817 条（草案 663 + 强制 GB 87 + GB/T 未采标 67）= 29%；拿不到 1,985 条 = 71%。条数会变，**公式不变**：

```
能看 = status==征求意见中  +  code 以 "GB " 开头  +  (GB/T|GB/Z 且 adopt 为空)
```
