# -*- coding: utf-8 -*-
"""抓征求意见稿详情页里的 PDF 附件直链（征求意见稿 + 编制说明）。

标管中心的征求意见详情页（viewZqyj&id=...）是固定结构：
  征求意见稿.pdf -> dataGkZqyj.do?formAction=openFileById&fileId=<32位>
  编制说明.pdf   -> 同上，另一个 fileId
fileId 与页面 id 不同，必须逐页抓，不能拼。

输出 data/draft_files.json : [{code,name,pdf,doc,page}]
"""
import json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
BASE = "https://app.nidc.org.cn/biaogzx/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# 页面里两个附件锚点的先后顺序不固定，靠锚文本判断，别靠位置
RE_FILE = re.compile(r'<a[^>]+href="([^"]*openFileById[^"]*)"[^>]*>(.*?)</a>', re.S | re.I)


def fetch(url, tries=3):
    for k in range(tries):
        try:
            req = Request(url, headers={"User-Agent": UA, "Referer": BASE})
            with urlopen(req, timeout=25) as r:
                raw = r.read()
            # 标管中心这批页面是 GB18030，用 utf-8 解会把中文全部丢成空，附件名就判不出来了
            try:
                return raw.decode("gb18030")
            except UnicodeDecodeError:
                return raw.decode("utf-8", "ignore")
        except Exception:
            if k == tries - 1:
                return ""
            time.sleep(1.2 * (k + 1))
    return ""


def one(item):
    html = fetch(item["url"])
    out = {"code": item.get("code", ""), "name": item.get("name", ""),
           "page": item["url"], "pdf": "", "doc": "", "ok": False}
    if not html:
        return out
    files = []
    for href, txt in RE_FILE.findall(html):
        t = re.sub(r"<[^>]+>", "", txt).strip()
        full = href if href.startswith("http") else BASE + href.lstrip("./")
        files.append((full, t))
    # 页面表格固定两列：先「征求意见稿」，后「编制说明」。
    # 锚文本常常只剩「.pdf」，靠文字判断会全落空，所以按顺序取，再用文字纠正。
    if files:
        out["pdf"] = files[0][0]
    if len(files) > 1:
        out["doc"] = files[1][0]
    for full, t in files:
        if "说明" in t:                      # 文字可信时以文字为准
            out["doc"] = full
            if out["pdf"] == full and len(files) > 1:
                out["pdf"] = [f for f, _ in files if f != full][0]
    out["ok"] = bool(out["pdf"])
    return out


def main():
    drafts = json.load(open(os.path.join(DATA, "drafts.json"), encoding="utf-8"))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if limit:
        drafts = drafts[:limit]
    print(f"待抓 {len(drafts)} 条")
    done, ok = 0, 0
    res = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(one, drafts):
            res.append(r)
            done += 1
            ok += r["ok"]
            if done % 50 == 0:
                print(f"  {done}/{len(drafts)}  命中 {ok}")
    json.dump(res, open(os.path.join(DATA, "draft_files.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"完成 {done} 条，拿到 PDF {ok} 条，未拿到 {done-ok} 条")


if __name__ == "__main__":
    main()
