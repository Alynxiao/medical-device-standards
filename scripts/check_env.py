# -*- coding: utf-8 -*-
"""跑之前的自检：Python 版本、三个数据源能不能连上、目录能不能写。

    python scripts/check_env.py

任何一项不过，先解决再跑 run.py——首抓没有预置数据兜底，源不通就是真缺数据。
"""
import os
import socket
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 10
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

SOURCES = [
    ("标管中心·标准目录库", "https://app.nidc.org.cn/biaogzx/qxqwk.do"),
    ("全国标准信息平台·行标备案", "https://hbba.sacinfo.org.cn/"),
    ("标管中心·征求意见", "https://app.nidc.org.cn/biaogzx/dataGkZqyj.do?formAction=listHbbp&type=bzca"),
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    bad = 0

    v = sys.version_info
    ok = v >= (3, 8)
    print(f"[{'OK ' if ok else 'BAD'}] Python {v.major}.{v.minor}.{v.micro}")
    if not ok:
        bad += 1

    try:
        p = os.path.join(HERE, "data")
        os.makedirs(p, exist_ok=True)
        test = os.path.join(p, ".write_test")
        with open(test, "w") as f:
            f.write("x")
        os.remove(test)
        print("[OK ] 目录可写")
    except Exception as e:  # noqa: BLE001
        print(f"[BAD] 目录不可写：{e}")
        bad += 1

    socket.setdefaulttimeout(TIMEOUT)
    for name, url in SOURCES:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                code = r.status
                r.read(2048)
            print(f"[{'OK ' if code == 200 else 'BAD'}] {name}（HTTP {code}）")
            if code != 200:
                bad += 1
        except Exception as e:  # noqa: BLE001
            print(f"[BAD] {name}：{e}")
            bad += 1

    print()
    if bad:
        print(f"有 {bad} 项没通过。源不通多半是网络或官网临时不可用，换网络或过一会儿再试。")
        return 1
    print("自检通过，可以跑：python run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
