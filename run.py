# -*- coding: utf-8 -*-
"""中国医械标准库 · 一键入口

    python run.py                  抓三源全量 + 生成页面（约 5 分钟）
    python run.py --build          只重新生成页面
    python run.py --only catalog   只抓某一个源（catalog/history/drafts/detail）
    python run.py --open           生成后自动打开页面

只用 Python 标准库，不需要装任何第三方包。
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
NEED = (3, 8)

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def call(script, args):
    path = os.path.join(HERE, script)
    if not os.path.exists(path):
        print(f"缺少脚本：{path}")
        return 1
    print(f"\n=== {script} {' '.join(args)} ===", flush=True)
    return subprocess.run([PY, path] + args, cwd=HERE).returncode


def main():
    if sys.version_info < NEED:
        print(f"需要 Python {NEED[0]}.{NEED[1]} 或更高，当前 {sys.version.split()[0]}")
        return 1

    ap = argparse.ArgumentParser(description="中国医械标准库")
    ap.add_argument("--build", action="store_true", help="只重新生成页面，不抓数据")
    ap.add_argument("--only", choices=["catalog", "history", "drafts", "detail"], help="只抓某一个源")
    ap.add_argument("--open", action="store_true", help="生成后自动打开页面")
    a = ap.parse_args()

    build_args = ["--open"] if a.open else []

    if a.build:
        return call("scripts/build_page.py", build_args)

    if a.only == "detail":
        return call("scripts/fetch_detail.py", [])

    sources = [a.only] if a.only else ["catalog", "history", "drafts"]

    # 全量跑之前先自查：源不通就别浪费五分钟。只提示不中止——自检偶有误报，
    # 真抓不动时抓取本身会报出是哪个源。
    if not a.only:
        print("\n=== 自检 ===")
        call("scripts/check_env.py", [])

    failed = []
    for s in sources:
        if call("scripts/fetch_all.py", ["--only", s]) != 0:
            failed.append(s)

    if failed:
        print(f"\n抓取未完成：{'、'.join(failed)}。页面未生成——缺源就不出残缺页面。")
        return 1

    # 补详情字段（适用范围等）。这一步**不阻断**：缺了只是卡片上没有适用范围，
    # 页面照样能出、能搜、能筛，比因为一个增强源失败就整包不出要好。
    if call("scripts/fetch_detail.py", []) != 0:
        print("\n详情字段没抓全：页面照出，但卡片上会缺适用范围。稍后可单独重跑：python run.py --only detail")

    if a.only:
        print(f"\n{sources[0]} 抓取完成。生成页面请跑：python run.py --build")
        return 0

    return call("scripts/build_page.py", build_args)


if __name__ == "__main__":
    sys.exit(main())
