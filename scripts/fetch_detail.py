# -*- coding: utf-8 -*-
"""补抓标管中心每条标准的详情页字段（只用 Python 自带库，不装任何第三方包）。

为什么需要：目录库列表接口只给标准号/名称/状态/日期。判「这个产品用什么材料」「这标准管什么」
只能靠名称关键词，于是 PTFE 一条都抽不到、聚丙烯酰胺被当成聚丙烯。
详情页里有官方字段，比名称可靠：
  ICS 分类号 / 中国标准分类号(CCS) / 归口单位(技委会) / 标准适用范围(一段话) / 采标情况 / 代替关系

为什么用这一段而不是直接读页面：站点是 **GBK** 编码，用 utf-8 解会把「归口单位」变成乱码，
正则一条都匹配不上（一开始就是这么错的，4 条全解析出 None）。

输出 data/catalog_detail.json：{标准号: {ics, ccs, tc, adopt, scope, replaced, replaces}}
只追加字段，不改 catalog.json。已抓过的自动跳过，中断后重跑可续。
"""
import io
import json
import os
import re
import time
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "catalog_detail.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return raw.decode("gbk", "replace")      # 站点是 GBK，别改成 utf-8


def field(t, label):
    """取 <td>label：</td><td>值</td> 的值。标签与值可能同格，也可能在下一格。"""
    m = re.search(label + r"[：:]\s*(?:</td>\s*<td[^>]*>)?(.*?)(?:</td>|</tr>)", t, re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()


def grab(url):
    t = get(url)
    return {
        "ics": field(t, "ICS"),
        "ccs": field(t, "中国标准分类"),
        "tc": field(t, "归口单位"),
        "adopt": field(t, "采标情况"),
        "scope": field(t, "标准适用范围"),
        "replaced": field(t, "代替号"),
        "replaces": field(t, "曾被代替号"),
    }


def main():
    src = os.path.join(DATA, "catalog.json")
    if not os.path.exists(src):
        print("缺 data/catalog.json，先跑 scripts/fetch_all.py")
        return 1
    cat = json.load(io.open(src, encoding="utf-8"))
    done = {}
    if os.path.exists(OUT):
        done = json.load(io.open(OUT, encoding="utf-8"))
        print("续跑：已有 %d 条" % len(done))

    todo = [r for r in cat if r["code"] not in done]
    print("待抓 %d 条（每条一次详情页请求，约 0.05 秒，2000 条约 2 分钟）" % len(todo))
    if not todo:
        ok = sum(1 for v in done.values() if v.get("tc"))
        print("无需抓取：%d 条，其中 %d 条有归口单位" % (len(done), ok))
        return 0

    t0 = time.time()
    for i, row in enumerate(todo, 1):
        for attempt in range(3):
            try:
                done[row["code"]] = grab(row["url"])
                break
            except Exception as e:
                if attempt == 2:
                    done[row["code"]] = {"error": "%s: %s" % (type(e).__name__, e)}
                time.sleep(1.5)
        if i % 200 == 0 or i == len(todo):
            io.open(OUT, "w", encoding="utf-8").write(json.dumps(done, ensure_ascii=False, indent=0))
            el = time.time() - t0
            print("  %d/%d  %.0fs  预计还需 %.0fs" % (i, len(todo), el, el / i * (len(todo) - i)), flush=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(done, ensure_ascii=False, indent=0))
    ok = sum(1 for v in done.values() if v.get("tc"))
    print("完成：%d 条，其中 %d 条拿到归口单位" % (len(done), ok))
    return 0


if __name__ == "__main__":
    sys.exit(main())
