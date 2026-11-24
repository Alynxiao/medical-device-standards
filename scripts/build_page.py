# -*- coding: utf-8 -*-
"""把三个源合并成一份页面数据，并生成单文件离线 HTML。

用法：python scripts/build_page.py [--open]

输入（data/ 下，由 fetch_all.py 生成）：catalog.json / history.json / drafts.json
输出：<技能根>/中国医械标准库_<数据日期>.html
"""
import argparse
import datetime
import json
import os
import re
import sys
import webbrowser
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
TPL = os.path.join(HERE, "templates", "page.html")
BASE_NAME = "中国医械标准库"

VERSION = "1.0.0"


def qr_data_uri():
    """公众号二维码：读 assets/qrcode.jpg 转 base64 内嵌，保证单文件离线可用。
    图和技能一起走，换二维码只换这张图，不用改代码。图不在就返回空串，页面那格自然空着。"""
    import base64
    p = os.path.join(HERE, "assets", "qrcode.jpg")
    if not os.path.exists(p):
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()



# ---- 产品分类：对齐药监局《医疗器械分类目录》的 22 个子目录 ----
# 标管中心的 43 个目录是「按技委会分工」，不是「按产品分类」；用它做导航会出现
# 「听诊器 1 条」「婴儿保育设备 3 条」这类碎片。所以导航改用产品分类：
# 一级 = 药监局的 22 类（只显示有条目的），二级 = 该类下原来的标管中心细目录。
# 通用类（生物学评价、包装、UDI…）与具体产品无关，单独一档放在最前。
# 未分类 = 征求意见稿与早期废止版：标管中心不给这两类赋目录号，补不了。
UNI = "__uni__"
NONE = "__none__"
NMPA_ORDER = [
    "01 有源手术器械", "02 无源手术器械", "03 神经和心血管手术器械", "04 骨科手术器械",
    "05 放射治疗器械", "06 医用成像器械", "07 医用诊察和监护器械", "08 呼吸、麻醉和急救器械",
    "09 物理治疗器械", "10 输血、透析和体外循环器械", "11 医疗器械消毒灭菌器械",
    "12 有源植入器械", "13 无源植入器械", "14 注输、护理和防护器械", "15 患者承载器械",
    "16 眼科器械", "17 口腔科器械", "18 妇产科、辅助生殖和避孕器械", "19 医用康复器械",
    "20 中医器械", "21 医用软件", "22 临床检验器械",
]
CAT_TO_NMPA = {
    # 通用：与具体产品没有直接关系
    "医疗器械生物学评价": UNI, "消毒灭菌通用技术": UNI, "医疗器械包装": UNI,
    "医用电气设备通用要求": UNI, "医疗器械质量管理": UNI,
    "医疗器械唯一标识（UDI）": UNI, "医疗器械临床评价": UNI,
    "医疗装备产业与应用": UNI, "可靠性与维修性技术": UNI, "纳米材料生物学评价": UNI,
    # 产品类
    "医学实验室与体外诊断器械和试剂": "22 临床检验器械",
    "外科植入物": "13 无源植入器械",
    "医用增材制造技术医疗器械": "13 无源植入器械",   # 3D 打印件多是骨科/口腔植入物
    "口腔材料、器械和设备": "17 口腔科器械",
    "医用X射线设备及用具": "06 医用成像器械",
    "医用超声设备": "06 医用成像器械",
    "医用光学和仪器": "06 医用成像器械",             # 内窥镜为主；其中检眼镜/验光仪严格属 16
    "输液、输血、采血、引流器械": "14 注输、护理和防护器械",
    "医用防护器械": "14 注输、护理和防护器械",
    "注射器（针）、穿刺器械": "14 注输、护理和防护器械",
    "放射治疗、核医学和放射剂量学": "05 放射治疗器械",
    "呼吸麻醉设备及装置": "08 呼吸、麻醉和急救器械",
    "除颤器、起搏器": "08 呼吸、麻醉和急救器械",     # 起搏器严格属 12 有源植入器械
    "外科手术器械": "02 无源手术器械",
    "医用体外循环设备及装置": "10 输血、透析和体外循环器械",
    "物理治疗器械": "09 物理治疗器械",
    "避孕与妇产科器械": "18 妇产科、辅助生殖和避孕器械",
    "辅助生殖医疗器械": "18 妇产科、辅助生殖和避孕器械",
    "消毒灭菌设备": "11 医疗器械消毒灭菌器械",
    "医用血管内导管及非血管内导管": "03 神经和心血管手术器械",
    "手术、治疗电子仪器": "01 有源手术器械",
    "医用机器人": "01 有源手术器械",
    "诊断电子仪器": "07 医用诊察和监护器械",
    "监护电子仪器": "07 医用诊察和监护器械",
    "生物电信号反馈设备": "07 医用诊察和监护器械",
    "脑机接口医疗器械": "07 医用诊察和监护器械",
    "婴儿保育设备": "07 医用诊察和监护器械",
    "听诊器": "07 医用诊察和监护器械",
    "中医器械": "20 中医器械",
    "人工智能医疗器械": "21 医用软件",
    "患者承载器械": "15 患者承载器械",
    "医用康复器械": "19 医用康复器械",
    "其他": NONE,
}

# ---- 二级细分：把混在大目录里的条目按名称抽到药监局的空类里 ----
# 标管中心没按药监局的维度设这三类目录，条目混在别处：骨科工具在「外科手术器械」、
# 眼科光学在「医用光学和仪器」、起搏器在「除颤器、起搏器」。
# 规则只认明确的产品词（不认泛字如「骨」「眼」），宁可漏、不误分：
# 「骨密度仪」属 06 不属 04，「眼轴长测量仪」属 16 属得对。
# (药监局类, 包含词, 排除词) —— 排除词命中就留在原目录，不做二次细分
NAME_SPLIT = [
    # 骨科：只认手术工具。植入物（接骨板/螺钉/髓内钉/骨水泥）属 13，牙科骨凿属 17
    ("04 骨科手术器械",
     ["骨科", "骨钻", "骨锯", "骨钳", "骨剪", "骨凿", "骨锉", "骨锤",
      "咬骨", "骨刀", "植骨", "颅骨钻", "骨牵引", "复位钳", "打拔器"],
     ["牙", "植入物", "植入器械", "接骨板", "螺钉", "髓内钉", "骨水泥", "环抱器"]),
    ("16 眼科器械",
     ["眼科", "检眼镜", "验光", "裂隙灯", "眼压计", "视力表", "角膜",
      "眼底", "眼轴", "人工晶状体", "人工晶体", "白内障", "视野计", "同视机"],
     ["内窥镜", "手术显微镜"]),
    # 有源植入：只认带电的植入物。「植入式给药装置」是输液港，属无源
    ("12 有源植入器械",
     ["起搏器", "人工耳蜗", "植入式神经刺激", "神经刺激器",
      "植入式心脏", "植入式心律", "脑深部刺激", "有源植入"],
     ["植入式给药"]),
]


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def norm_family(code):
    """归并成「标准线」键：YY / YY/T / YY/Z 视为同一条线（强制转推荐是同一标准），
    GB / GB/T / GB/Z 同理；YY 与 GB 不同线（9706.1 这类同号不同线，不能混判）。
    号段去前导零（YY/T 0510 与 YY/T 510 是同一条）。"""
    c = (code or "").upper().replace("—", "-").replace("–", "-").strip()
    m = re.match(r"^(YY/T|YY/Z|YY|GB/T|GB/Z|GB)\s*([\d.]+)", c)
    if not m:
        return None
    fam = "YY" if m.group(1).startswith("YY") else "GB"
    num = ".".join(str(int(x)) if x.isdigit() else x for x in m.group(2).split("."))
    return (fam, num)


def std_type(code):
    c = (code or "").upper()
    if c.startswith("GB"):
        return "国标"
    if c.startswith("YY"):
        return "行标"
    return "其他"


def nature(code):
    c = (code or "").upper().replace(" ", "")
    if c.startswith("GB/Z") or c.startswith("YY/Z"):
        return "指导性"
    if c.startswith("YY/T") or c.startswith("GB/T"):
        return "推荐性"
    if c.startswith("YY") or c.startswith("GB"):
        return "强制性"
    return ""


def _year(code):
    """标准号末尾的年份。'YY/T 0316-2016' -> 2016"""
    m = re.search(r"-\s*(\d{4})\s*$", (code or "").replace("—", "-").replace("–", "-"))
    return int(m.group(1)) if m else 0


def norm_name(s):
    s = (s or "").replace("—", "-").replace("–", "-")
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = re.sub(r"\s+", "", s)
    return s.strip()


def strip_part(s):
    """去掉「第N部分：」：同一份文件各部分分别征求意见，部分号会变，
    去掉后才能和已发布版本的名称对上。"""
    return re.sub(r"第\s*[0-9一二三四五六七八九十]+\s*部分[:：]?", "", s)


def today():
    return datetime.date.today().isoformat()


# ---- 按用途归类 + 详情字段（ICS / 分类号 / 技委会 / 适用范围）----
# 为什么不用官方分类：药监局 22 类分的是「管什么产品」，标管中心 43 个目录分的是「归哪个技委会」，
# 都不是「这标准是干什么用的」。研发要的是产品要求 / 材料 / 试验方法这条线，只能自己判。
# 判据用「名称 + 适用范围」：名称里"XX材料 第1部分：粉料"是材料标准，"…的测定/试验方法"是方法标准；
# 适用范围（官方原文）常写着"适用于由金属、超高分子量聚乙烯、陶瓷材料制成…"，能看出材料，可作佐证。

# 方法词：只看"这份标准是不是在讲怎么测"。加了独立的「试验 / 测定 / 测试 / 分析 / 测量」——
# 少了它们，「银汞合金的腐蚀试验」「差示扫描量热法测定超高分子量聚乙烯熔化焓」这类
# 会被当成材料标准混进材料里。
METH_W = ["试验方法", "测试方法", "检验方法", "检测方法", "测定方法", "评价方法", "分析方法",
          "表征方法", "试验规程", "标准方法", "测量程序", "的测定", "测定法",
          "试验", "测试", "测定", "分析", "测量", "表征", "评估", "评价"]
# 名称以这些词收尾的，基本就是方法标准。比起「名称里出现过就算」，看结尾误判少一个数量级。
METH_END = ("方法", "试验", "程序", "规程", "法", "测定", "测试", "分析", "评价", "评估", "表征", "测量")
METH_NO = ["要求", "规范", "术语"]   # 带这些词的多半是产品/基础标准，不是方法标准
# 「试验方法 / 测试方法 / …」这种完整词组，出现就是方法标准，不用再看有没有产品词——
# 「接触性创面敷料试验方法 第1部分：液体吸收性」是方法不是敷料产品标准。
METH_PHRASE = ["试验方法", "测试方法", "检验方法", "检测方法", "测定方法", "评价方法",
               "分析方法", "表征方法", "试验规程", "测量程序"]
PROD_W = ["假体", "手术器械", "设备", "器具", "系统", "装置", "导管", "导丝", "支架", "球囊", "封堵",
          "敷料", "缝线", "缝合线", "注射器", "注射针", "输液器", "输血器", "针", "机", "仪", "盒",
          "包", "钳", "剪", "刀", "镊", "钩", "钻", "锯", "床", "套", "插头", "接头", "阀", "泵",
          "罐", "袋", "种植体", "瓣膜", "起搏器", "除颤", "吻合器", "内窥镜", "喉镜", "避孕套",
          "节育器", "听诊器", "体温计",
          # 牙科与外科的成品：这些东西里含"合金/树脂/陶瓷"，但它们是产品不是材料，
          # 不排除的话「技工室用硬质合金刃具」「氧化锌丁香酚水门汀」都会算成材料标准
          "刃具", "水门汀", "胶囊", "分离器", "封闭", "粘接", "海绵", "管路", "牙冠", "贴面",
          "衬垫", "义齿", "充填", "印模"]
MAT_W = ["材料", "专用料", "加工材", "粉料", "棒材", "板材", "管材", "粉末", "绳材", "丝材", "型材",
         "聚合物", "树脂", "合金", "陶瓷", "玻璃", "不锈钢", "纯钛", "钛合金", "镍钛", "镍-钛",
         "钛-6铝", "钴铬", "钴-铬", "钽", "镁", "锌", "聚乙烯", "聚丙烯", "聚四氟乙烯", "聚醚醚酮",
         "聚乳酸", "聚丙交酯", "聚氨酯", "聚碳酸酯", "聚氯乙烯", "聚烯烃", "硅橡胶", "硅胶", "硅凝胶",
         "胶原", "明胶", "壳聚糖", "纤维素", "水凝胶", "海藻酸", "透明质酸", "羟基磷灰石", "氧化铝",
         "氧化锆", "磷酸钙", "脱细胞", "丝素", "非织造布"]

# 材料种类：先匹配先归。金属排在最前——"镍钛形状记忆合金绳材"是金属不是线材。
MAT_GROUPS = [
    ("金属材料", ["不锈钢", "纯钛", "钛合金", "镍钛", "镍-钛", "钛-6铝", "钴铬", "钴-铬", "钽",
                  "镁", "锌", "合金"]),
    ("高分子材料", ["聚乙烯", "聚丙烯", "聚四氟乙烯", "聚醚醚酮", "聚乳酸", "聚丙交酯", "聚氨酯",
                    "聚碳酸酯", "聚氯乙烯", "聚烯烃", "硅橡胶", "硅胶", "硅凝胶", "树脂", "聚合物",
                    "水凝胶", "海藻酸", "透明质酸", "非织造布"]),
    ("陶瓷与无机材料", ["陶瓷", "氧化铝", "氧化锆", "羟基磷灰石", "磷酸钙", "生物玻璃", "玻璃"]),
    ("天然与生物源材料", ["胶原", "明胶", "壳聚糖", "纤维素", "脱细胞", "动物源", "异种", "丝素",
                          "牛", "猪"]),
    ("其他材料", []),
]


def role_of(name):
    """产品要求 / 材料 / 试验方法。

    判定顺序（每条都是踩坑后加的，别随手调）：
      1. 带「要求 / 规范 / 术语」的一律不判方法：这类名字里常有"…材料和试验方法""…通用
         要求"，早期按"含试验方法就是方法"判，一次性错了一大批产品标准。
      2. 名字里有「试验方法 / 测试方法 / …」完整词组的 → 方法。不看产品词：
         「接触性创面敷料试验方法 第1部分：液体吸收性」是方法，不是敷料标准。
      3. 名字**以**方法词结尾的 → 方法。看结尾比看到处出现可靠：
         「…髋关节假体测试」「…毒理学风险评估」是方法；「17α-羟孕酮测定试剂盒」不是。
      4. 名字中间带方法词、又没有产品词、也不是试剂盒/校准品 → 方法。
      5. 没有产品词、但带材料词 → 材料。
      6. 其余 → 产品要求。
    """
    n = (name or "").strip()
    if any(w in n for w in METH_NO):
        pass
    elif any(w in n for w in METH_PHRASE):
        return "方法"
    elif n.endswith(METH_END):
        return "方法"
    elif any(w in n for w in METH_W) and not any(w in n for w in PROD_W) \
            and not any(w in n for w in ["试剂", "校准品", "质控品", "参考品", "软件"]):
        return "方法"
    if not any(w in n for w in PROD_W) and any(w in n for w in MAT_W):
        return "材料"
    return "要求"


def mat_group_of(name):
    n = name or ""
    for g, ws in MAT_GROUPS:
        if any(w in n for w in ws):
            return g
    return "其他材料"


def attach_detail(rows):
    """补详情字段。catalog_detail.json 由 scripts/fetch_detail.py 生成，没有就跳过（不报错）。"""
    path = os.path.join(DATA, "catalog_detail.json")
    det = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        # 抓取失败的那条只留了 error 键，当成没抓到
        det = {(k or "").strip(): v for k, v in raw.items()
               if isinstance(v, dict) and "error" not in v}
    miss = 0
    for r in rows:
        d = det.get((r["code"] or "").strip(), {})
        if not d:
            miss += 1
        r["ics"] = d.get("ics", "")
        r["ccs"] = d.get("ccs", "")
        r["tc"] = d.get("tc", "")
        r["adopt"] = d.get("adopt", "")
        r["scope"] = d.get("scope", "")
        r["role"] = role_of(r["name"])
        r["mat"] = mat_group_of(r["name"]) if r["role"] == "材料" else ""
    if miss:
        print(f"  提示：{miss} 条没有详情字段（草案/备案库来源），按用途和材料种类仍按名称判")
    return det


def build_rows():
    cat = load("catalog.json")
    his = load("history.json")
    dra = load("drafts.json")
    T = today()

    rows = []
    seen = set()

    def _code_key(code):
        c = (code or "").upper().replace("—", "-").replace("–", "-")
        return re.sub(r"\s+", "", c)

    def add(r):
        # 去重键 = 「标准线 + 号 + 年份」：同一版本只留一条。
        # 不能带名称——两个源对同一标准的名称写法可能不同（会重复入库），
        # 也不能带完整号——YY 0033-2000 与 YY/T 0033-2000 是同一条标准的两种写法。
        # catalog 先加，所以同版本优先留 catalog 的官方状态。
        f = norm_family(r["code"])
        if f:
            k = (f[0], f[1], _year(r["code"]))
        else:
            # 草案只有项目号没有标准号：必须带上名称——同一项目号可能被复用到
            # 一份文件的不同部分（如「第4部分」「第5部分」），只按号去重会误删。
            k = ("_", _code_key(r["code"]), norm_name(r.get("name", "")))
        if k in seen:
            return
        seen.add(k)
        r["type"] = std_type(r["code"])
        r["nature"] = nature(r["code"])
        fam = norm_family(r["code"])
        r["grp"] = (fam[0] + " " + fam[1]) if fam else ""
        rows.append(r)

    # 1) 现行有效全集（官方状态：现行 / 即将实施）
    for r in cat:
        add({
            "code": r["code"], "name": r["name"], "status": r.get("status") or "现行",
            "issue": r.get("issue", ""), "act": r.get("act", ""),
            "area": r.get("area", ""), "cat1": r.get("cat1", ""), "cat2": r.get("cat2", ""),
            "amend": r.get("amend", ""), "note": r.get("amend") if r.get("amend") not in ("/", "", None) else "",
            "url": r.get("url", ""), "src": "catalog",
        })

    # 2) 行业标准历史：补废止版；补目录库漏收的现行版（状态按实施日算）
    #    采信规则：同一条标准线上存在更晚年份的版本时，这个旧版一律按「已被代替」记为废止，
    #    不采信备案库的「现行」——它会成规模滞后。
    known = defaultdict(int)          # 标准线 -> 最大年份
    for r in rows:
        f = norm_family(r["code"])
        if f:
            known[f] = max(known[f], _year(r["code"]))
    for r in his:
        f = norm_family(r["code"])
        if f:
            known[f] = max(known[f], _year(r["code"]))

    for r in his:
        f = norm_family(r["code"])
        y = _year(r["code"])
        superseded = bool(f) and known.get(f, 0) > y
        if r.get("status") == "废止" or superseded:
            # 废止版不入库：页面只收现行、即将实施、征求意见。
            # 备案库里成规模滞后的「现行」也走这条——它实际已被更晚年份的版本代替。
            continue
        st = "即将实施" if (r.get("act") or "") > T else "现行"
        add({
            "code": r["code"], "name": r["name"], "status": st,
            "issue": r.get("issue", ""), "act": r.get("act", ""),
            "area": "", "cat1": "", "cat2": "", "amend": "", "note": "",
            "url": r.get("url", ""), "src": "history",
        })

    # 3) 征求意见稿：与现行版并存；名称撞上「同年或更晚发布」的已发布标准才算疑似已转正
    #    （撞上更早年份的同名标准 = 这轮在修订，不是转正）
    pub_year = {}
    name2pos = {}
    for r in rows:
        if r["status"] in ("现行", "即将实施"):
            y = (r.get("issue") or "")[:4]
            nm = norm_name(r["name"])
            if nm and y.isdigit():
                pub_year[nm] = max(pub_year.get(nm, 0), int(y))
        if r["cat1"]:
            name2pos.setdefault(norm_name(r["name"]), (r["area"], r["cat1"], r["cat2"]))

    for r in dra:
        nm = norm_name(r["name"])
        dy = (r.get("issue") or "")[:4]
        promoted = bool(nm) and nm in pub_year and dy.isdigit() and pub_year[nm] >= int(dy)
        # 草案自己没有目录号，但名称能对上已发布的标准（含去掉「第N部分」再对），
        # 就继承那条标准的目录——370/663 条能这样归上，剩下的只能留「未分类」。
        pos = name2pos.get(nm) or name2pos.get(strip_part(nm))
        add({
            "code": r.get("code", ""), "name": r["name"], "status": "征求意见中",
            "issue": r.get("issue", ""), "act": "", "deadline": r.get("deadline", ""),
            "area": pos[0] if pos else "", "cat1": pos[1] if pos else "", "cat2": pos[2] if pos else "",
            "amend": "",
            "note": "同名标准已发布" if promoted else "",
            "url": r.get("url", ""), "src": "draft",
        })

    # 4) 位置回填 + 产品分类
    #    废止老版本、补录版自己没有目录：按同号族继承（同一标准的旧版和现行版属同一目录）。
    #    草案没有标准号、组不成族，只能落「未分类」——标管中心本来也不给它目录号。
    grp_cat = {}
    for r in rows:
        if r["cat1"] and r["grp"]:
            grp_cat.setdefault(r["grp"], (r["area"], r["cat1"], r["cat2"]))
    for r in rows:
        if not r["cat1"] and r["grp"] in grp_cat:
            r["area"], r["cat1"], r["cat2"] = grp_cat[r["grp"]]
    for r in rows:
        r["nmpa"] = CAT_TO_NMPA.get(r["cat1"], NONE) if r["cat1"] else NONE
        nm = r["name"] or ""
        for cls, words, skip in NAME_SPLIT:
            if any(w in nm for w in skip):
                continue
            if any(w in nm for w in words):
                r["nmpa"] = cls
                break

    # 同号版本数（YY 与 YY/T 算同一条线）
    cnt = defaultdict(int)
    for r in rows:
        if r["grp"]:
            cnt[r["grp"]] += 1
    for r in rows:
        r["vers"] = cnt.get(r["grp"], 1) if r["grp"] else 1

    def _sort_key(code):
        """按「族 → 号段数值 → 年份」排，避免字符串比较把 11417.10 排到 11417.2 前面。"""
        c = (code or "").upper().replace("—", "-").replace("–", "-")
        m = re.match(r"^(YY/T|YY/Z|YY|GB/T|GB/Z|GB)\s*([\d.]+)", c)
        if not m:
            return (9, (), 0)
        fam = 0 if m.group(1).startswith("YY") else 1
        nums = tuple(int(x) for x in m.group(2).split(".") if x.isdigit())
        return (fam, nums, 0)

    # 排序：先按状态分组（现行 → 即将实施 → 征求意见中），组内按发布日期倒序——
    # 这样「现行有效的、最新发布的」永远在最上面。不做全库纯时间倒序：征求意见稿
    # 的征集日期是当下，会把草案全顶到首屏。
    ORDER = {"现行": 0, "即将实施": 1, "征求意见中": 2}

    def _pub_key(r):
        d = re.sub(r"\D", "", (r.get("issue") or ""))[:8]
        return -int(d) if d else 0

    rows.sort(key=lambda r: (ORDER.get(r["status"], 9), _pub_key(r), _sort_key(r["code"])))
    attach_detail(rows)   # 补 ICS/分类号/技委会/适用范围，并按用途、材料种类归类
    return rows


def main():
    ap = argparse.ArgumentParser(description="中国医械标准库 · 生成离线页面")
    ap.add_argument("--open", action="store_true", help="生成后打开")
    a = ap.parse_args()

    rows = build_rows()
    if not rows:
        print("data/ 下没有数据，先跑 python scripts/fetch_all.py")
        return 1

    dates = [r["issue"] for r in rows if r.get("issue")]
    updated = max(dates) if dates else today()

    stats = {
        "all": len(rows),
        "现行": sum(1 for r in rows if r["status"] == "现行"),
        "即将实施": sum(1 for r in rows if r["status"] == "即将实施"),
        "征求意见中": sum(1 for r in rows if r["status"] == "征求意见中"),
    }

    with open(TPL, encoding="utf-8") as f:
        tpl = f.read()
    html = (tpl
            .replace("__TITLE__", BASE_NAME)
            .replace("__VERSION__", VERSION)
            .replace("__QRCODE__", qr_data_uri())
            .replace("__UPDATED__", updated)
            .replace("__STATS__", json.dumps(stats, ensure_ascii=False))
            .replace("__DATA__", json.dumps(rows, ensure_ascii=False, separators=(",", ":"))))

    out = os.path.join(HERE, f"{BASE_NAME}_{updated}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 {out}（{len(rows)} 条，{os.path.getsize(out)//1024} KB）")
    print("  现行 {现行} / 即将实施 {即将实施} / 征求意见中 {征求意见中}".format(**stats))
    rc = defaultdict(int)
    for r in rows:
        rc[r.get("role") or "要求"] += 1
    print("  按用途：产品要求 {} / 材料 {} / 试验方法 {}".format(
        rc.get("要求", 0), rc.get("材料", 0), rc.get("方法", 0)))
    mc = defaultdict(int)
    for r in rows:
        if r.get("mat"):
            mc[r["mat"]] += 1
    print("  材料种类：" + " / ".join(f"{g} {mc.get(g,0)}" for g, _ in MAT_GROUPS))
    if a.open:
        webbrowser.open(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
