# -*- coding: utf-8 -*-
"""中国医械标准库 —— 全量抓取（三个源）

用法：
    python scripts/fetch_all.py            # 三个源全抓
    python scripts/fetch_all.py --only catalog
    python scripts/fetch_all.py --only history
    python scripts/fetch_all.py --only drafts

产物（写在本技能的 data/ 下，不进对外包）：
    data/catalog.json   现行有效标准全集（标管中心目录库）
    data/history.json   行业标准全历史含废止（标准信息平台备案库）
    data/drafts.json    标准草案征求意见（逐项拆分）
    data/raw/           各源原始响应，便于核对
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

CATALOG_BASE = "https://app.nidc.org.cn/biaogzx/qxqwk.do"
HISTORY_URL = "https://hbba.sacinfo.org.cn/stdQueryList"
DRAFT_BASE = "https://app.nidc.org.cn/biaogzx/dataGkZqyj.do"

# 官方目录库的两个顶层目录键
AREA_KEYS = [("20210406a001", "通用技术领域"), ("20210406a002", "专业技术领域")]

# YY 序列里混入的非器械（化妆品/制药机械/药品包装/食品添加剂），按名称排除
NON_DEVICE_WORDS = ["化妆品用", "制药机械", "药品包装", "食品添加剂"]


def _open(url, data=None, referer=None, timeout=90, retries=3):
    headers = {"User-Agent": UA}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if referer:
        headers["Referer"] = referer
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2)
    raise last


def _text(raw, prefer="gbk"):
    for enc in (prefer, "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:  # noqa: BLE001
            continue
    return raw.decode(prefer, "ignore")


def _fmt_date(ms):
    """源站日期是东八区零点，按 UTC 转会差一天，固定 +08:00。"""
    try:
        import datetime
        return datetime.datetime.fromtimestamp(
            ms / 1000, datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


def _nature(code):
    """YY / GB 为强制性，YY/T、GB/T、GB/Z 为推荐性；GB/Z 记为指导性。"""
    c = (code or "").upper().replace(" ", "")
    if c.startswith("GB/Z") or c.startswith("YY/Z"):
        return "指导性"
    if c.startswith("YY/T") or c.startswith("GB/T"):
        return "推荐性"
    if c.startswith("YY") or c.startswith("GB"):
        return "强制性"
    return ""


def _std_type(code):
    c = (code or "").upper()
    return "国标" if c.startswith("GB") else ("行标" if c.startswith("YY") else "其他")


def _is_non_device(name):
    return any(w in (name or "") for w in NON_DEVICE_WORDS)


# ---------------------------------------------------------------- 目录库（现行有效）

def _parse_catalog(s):
    """表格列固定：0序号 1目录名称 2一级目录 3二级目录 4编号 5名称 6批准 7实施 8状态 9修改单 10操作。
    每格的完整文本在 span 的 title 属性里（显示文本被截断），必须按列取 title。"""
    def _span_title(td):
        m = re.search(r'<span title="([^"]*)"', td, re.S)
        return html.unescape(m.group(1)).strip() if m else ""

    out = []
    for tr in re.findall(r"<tr[^>]*bgcolor.*?</tr>", s, re.S):
        if "formAction=view" not in tr:
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 10:
            continue
        cells = [html.unescape(re.sub(r"<[^>]+>", "", td)).replace("\xa0", " ").strip() for td in tds]
        vid = re.search(r"formAction=view&id=(\w+)", tr)
        out.append({
            "code": cells[4],
            "name": _span_title(tds[5]) or cells[5],
            "area": _span_title(tds[1]) or cells[1],
            "cat1": _span_title(tds[2]) or cells[2],
            "cat2": _span_title(tds[3]) or cells[3],
            "issue": cells[6],
            "act": cells[7],
            "status_raw": cells[8],
            "amend": cells[9],
            "url": f"{CATALOG_BASE}?formAction=view&id={vid.group(1)}" if vid else "",
        })
    return out


def fetch_catalog():
    rows, pages = [], 0
    for key, label in AREA_KEYS:
        idx = 1
        while idx <= 12:
            body = urllib.parse.urlencode({
                "index": idx, "pageSize": 500, "chalbid": "", "chabiao": "",
                "chaname": "", "bzsyfw_s": "", "bzml": key, "bzmlone": "", "bzmltwo": "",
            }).encode()
            s = _text(_open(f"{CATALOG_BASE}?formAction=list&istiaojian=3", data=body,
                            referer=CATALOG_BASE))
            if idx == 1:
                os.makedirs(RAW, exist_ok=True)
                with open(os.path.join(RAW, f"catalog_{key}.html"), "w", encoding="utf-8") as f:
                    f.write(s)
            part = _parse_catalog(s)
            pages += 1
            if not part:
                break
            rows += part
            print(f"  目录库 {label} 第{idx}页 {len(part)} 条")
            if len(part) < 500:
                break
            idx += 1
            time.sleep(0.3)

    seen, out = set(), []
    for r in rows:
        k = (r["code"], r["name"], r["url"])
        if k in seen:
            continue
        seen.add(k)
        if _is_non_device(r["name"]):
            print(f"  剔除非器械：{r['code']} {r['name'][:30]}")
            continue
        r["status"] = r.pop("status_raw")
        r["kind"] = "catalog"
        out.append(r)
    print(f"目录库合计 {len(out)} 条（{pages} 页）")
    return out


# ---------------------------------------------------------------- 行业标准备案（含废止）

def _parse_history(recs):
    out = []
    for r in recs:
        code = (r.get("code") or "").strip()
        if not code:
            continue
        name = (r.get("chName") or "").strip()
        if _is_non_device(name):
            continue
        out.append({
            "code": code,
            "name": name,
            "status": "废止" if r.get("status") == "废止" else "现行",
            "issue": _fmt_date(r.get("issueDate")),
            "act": _fmt_date(r.get("actDate")),
            "record_no": r.get("recordNo") or "",
            "url": f"https://hbba.sacinfo.org.cn/stdDetail/{r.get('pk')}" if r.get("pk") else "",
            "kind": "history",
        })
    return out


def fetch_history():
    rows, idx = [], 1
    while idx <= 60:
        body = urllib.parse.urlencode({
            "current": idx, "size": 100, "key": "", "ministry": "yjj",
            "industry": "", "pubdate": "", "date": "", "status": "[]",
        }).encode()
        j = json.loads(_open(HISTORY_URL, data=body, referer="https://hbba.sacinfo.org.cn/stdList").decode("utf-8"))
        recs = j.get("records") or []
        total = j.get("total")
        if not recs:
            break
        rows += _parse_history(recs)
        print(f"  行业标准备案 第{idx}页 累计 {len(rows)}/{total}")
        if total and idx * 100 >= total:
            break
        idx += 1
        time.sleep(0.3)
    print(f"行业标准备案合计 {len(rows)} 条")
    return rows


# ---------------------------------------------------------------- 标准草案征求意见

def _parse_draft_notices(s):
    out = []
    for href, title, date in re.findall(
            r'<a[^>]+href="([^"]*viewNotice[^"]*)"[^>]*>(.*?)</a>.*?(\d{4}-\d{2}-\d{2})', s, re.S):
        out.append({
            "notice_url": href if href.startswith("http") else f"https://app.nidc.org.cn/biaogzx/{href.lstrip('./')}",
            "title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
            "date": date,
        })
    return out


def fetch_drafts(limit=None):
    notices, idx = [], 1
    base = f"{DRAFT_BASE}?formAction=listHbbp&type=bzca"
    while idx <= 40:
        s = _text(_open(f"{base}&index={idx}&pageSize=100",
                        referer="https://www.nidc.org.cn/nifdc/bshff/ylqxbzhgl/index.html"), prefer="utf-8")
        part = _parse_draft_notices(s)
        if not part:
            break
        notices += part
        print(f"  征求意见 第{idx}页 累计 {len(notices)} 条")
        if len(part) < 100:
            break
        idx += 1
        time.sleep(0.25)

    seen, uniq = set(), []
    for n in notices:
        if n["notice_url"] in seen:
            continue
        seen.add(n["notice_url"])
        uniq.append(n)
    if limit:
        uniq = uniq[:limit]

    items = []
    for i, n in enumerate(uniq, 1):
        try:
            s = _text(_open(n["notice_url"]), prefer="utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"  [失败] {n['title'][:30]} {e}")
            continue
        # 每条草案一行的链接：viewZqyj&id=...
        ids = re.findall(r"formAction=viewZqyj&id=(\w+)", s)
        # 名称/项目号/截止日在同一行，按表格单元格抓
        cells_rows = re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S)
        names, codes, deadlines = [], [], []
        for tr in cells_rows:
            if "viewZqyj" not in tr:
                continue
            tds = [html.unescape(re.sub(r"<[^>]+>", "", td)).replace("\xa0", " ").strip()
                   for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            m = re.search(r'<a[^>]*href="[^"]*viewZqyj[^"]*"[^>]*>(.*?)</a>', tr, re.S)
            names.append(html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else "")
            proj = [c for c in tds if re.match(r"^[A-Z]?\d{6,}[-A-Za-z0-9]*$", c)]
            codes.append(proj[0] if proj else "")
            dl = [c for c in tds if re.match(r"^\d{4}-\d{2}-\d{2}$", c)]
            deadlines.append(dl[-1] if dl else "")
        for k, pid in enumerate(ids):
            items.append({
                "code": codes[k] if k < len(codes) else "",
                "name": names[k] if k < len(names) else "",
                "status": "征求意见中",
                "issue": n["date"],
                "act": "",
                "deadline": deadlines[k] if k < len(deadlines) else "",
                "notice_title": n["title"],
                "url": f"{DRAFT_BASE}?formAction=viewZqyj&id={pid}",
                "kind": "draft",
            })
        if i % 40 == 0:
            print(f"  拆草案 {i}/{len(uniq)}，累计 {len(items)} 项")
        time.sleep(0.15)
    print(f"征求意见 {len(uniq)} 条通知 → {len(items)} 项草案")
    return items, uniq


# ---------------------------------------------------------------- 入口

def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    p = os.path.join(DATA, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"  写出 {p}（{len(obj) if isinstance(obj, list) else '—'} 条）")


def main():
    ap = argparse.ArgumentParser(description="中国医械标准库 · 全量抓取")
    ap.add_argument("--only", choices=["catalog", "history", "drafts"], default=None)
    ap.add_argument("--draft-limit", type=int, default=None, help="只拆前 N 条通知（调试用）")
    a = ap.parse_args()

    if a.only in (None, "catalog"):
        print("[1/3] 抓现行有效标准全集")
        save("catalog.json", fetch_catalog())
    if a.only in (None, "history"):
        print("[2/3] 抓行业标准全历史")
        save("history.json", fetch_history())
    if a.only in (None, "drafts"):
        print("[3/3] 抓标准草案征求意见")
        items, notices = fetch_drafts(limit=a.draft_limit)
        save("drafts.json", items)
        save("draft_notices.json", notices)
    print("完成。下一步：python run.py --build")


if __name__ == "__main__":
    sys.exit(main())
