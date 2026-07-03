"""
晋江文学城元数据爬虫
参考: https://github.com/dev-chenxing/jjwxc-crawler
仅爬取小说元数据，不下载章节内容

使用方法:
1. 安装依赖: pip install requests beautifulsoup4
2. 运行: python jjwxc_crawler.py

如需登录态，设置环境变量 JJWXC_COOKIE 或修改下方 COOKIE 变量
"""

import re
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from itertools import product

# ==================== 配置 ====================

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "jjwxc"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.jjwxc.net/",
}

# Cookie（从浏览器 F12 -> Network -> 复制）
COOKIE = ""  # 留空则不使用Cookie

# 延迟（秒）
DELAY_MIN = 0.5
DELAY_MAX = 1.5

# ==================== 标签体系 ====================

TAG_STRUCTURE = {
    "xx": {"1": "言情", "2": "纯爱", "3": "百合", "5": "无CP", "6": "多元"},
    "mainview": {
        "1": "男主", "2": "女主", "3": "主攻", "4": "主受",
        "5": "互攻", "8": "不明", "9": "其他", "12": "双视角", "13": "多视角",
    },
    "sd": {"1": "近代现代", "2": "古色古香", "4": "架空历史", "5": "幻想未来"},
    "lx": {
        "1": "爱情", "2": "武侠", "3": "奇幻", "4": "仙侠", "5": "游戏",
        "6": "传奇", "7": "科幻", "8": "童话", "9": "惊悚", "10": "悬疑",
        "16": "剧情", "17": "轻小说", "20": "古典衍生", "18": "东方衍生",
        "19": "西方衍生", "21": "其他衍生",
    },
}

# ==================== 工具函数 ====================

def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    if COOKIE:
        session.headers["Cookie"] = COOKIE
    return session


def random_delay():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def build_bookbase_url(params: dict, page: int) -> str:
    """构建 bookbase.php URL（参考原爬虫格式）"""
    parts = []
    if params.get("xx") and params["xx"] != "0":
        parts.append(f"xx{params['xx']}={params['xx']}")
    if params.get("mainview") and params["mainview"] != "0":
        parts.append(f"mainview={params['mainview']}")
    parts.append(f"bq={params.get('bq', '-1')}")
    if params.get("sd") and params["sd"] != "0":
        parts.append(f"sd{params['sd']}={params['sd']}")
    if params.get("lx") and params["lx"] != "0":
        parts.append(f"lx={params['lx']}")
    parts.append(f"page={page}")
    return f"https://www.jjwxc.net/bookbase.php?{'&'.join(parts)}"


# ==================== 爬取函数 ====================

def crawl_bookbase(params: dict, page: int, session: requests.Session) -> list:
    """爬取列表页，返回小说ID列表"""
    url = build_bookbase_url(params, page)
    try:
        resp = session.get(url, timeout=15)
        resp.encoding = "gb18030"
        return list(set(int(m) for m in re.findall(r"novelid=(\d+)", resp.text)))
    except Exception as e:
        print(f"  [ERROR] 列表页: {e}")
        return []


def extract_novel_metadata(novel_id: int, session: requests.Session) -> dict | None:
    """
    提取单本小说的元数据
    字段: 作者、类型、标签、主角、配角、一句话简介、立意、状态、字数、简介
    """
    url = f"https://www.jjwxc.net/onebook.php?novelid={novel_id}"
    try:
        resp = session.get(url, timeout=15)
        resp.encoding = "gb18030"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 跳过小树苗
        if soup.title and "小树苗" in soup.title.text:
            return None

        # 标题
        title_tag = soup.find("span", {"id": "novelcolor"})
        if not title_tag:
            return None
        title = title_tag.text.strip()

        # 作者
        author = ""
        author_link = soup.find("a", href=re.compile(r"oneauthor\.php"))
        if author_link:
            author = author_link.text.strip()

        # 类型（原创-言情-架空历史-爱情-女主视角）
        genre = ""
        genre_spans = soup.select(".rightul span")
        if len(genre_spans) > 1:
            genre = genre_spans[1].text.strip()

        # 标签
        tags = [a.text.strip() for a in soup.select("div.smallreadbody span a") if a.text.strip()]

        # 主角、配角、一句话简介、立意
        main_characters = ""
        supporting_characters = ""
        oneliner = ""
        theme = ""

        for span in soup.select("div.smallreadbody span"):
            text = span.get_text(strip=True)
            if text.startswith("主角："):
                main_characters = text[3:].strip()
            elif text.startswith("配角："):
                supporting_characters = text[3:].strip()
            elif text.startswith("一句话简介："):
                oneliner = text[5:].strip()
            elif text.startswith("立意："):
                theme = text[3:].strip()

        # 状态和字数
        status = ""
        status_tag = soup.find("span", {"class": "novelstatus"})
        if status_tag:
            status = status_tag.text.strip()

        word_count = ""
        word_tag = soup.find("span", {"itemprop": "wordCount"})
        if word_tag:
            word_count = word_tag.text.strip()

        # 组合状态
        if word_count:
            status = f"{status}/{word_count}" if status else word_count

        # 简介
        synopsis = ""
        synopsis_tag = soup.find(id="novelintro")
        if synopsis_tag:
            synopsis = synopsis_tag.get_text(strip=True)

        return {
            "id": novel_id,
            "title": title,
            "author": author,
            "genre": genre,
            "tags": tags,
            "main_characters": main_characters,
            "supporting_characters": supporting_characters,
            "oneliner": oneliner,
            "theme": theme,
            "status": status,
            "synopsis": synopsis,
            "url": url,
        }

    except Exception as e:
        print(f"  [ERROR] 详情页 {novel_id}: {e}")
        return None


def generate_combinations() -> list:
    """生成所有维度组合"""
    return [
        {"xx": xx, "mainview": mv, "sd": sd, "lx": lx, "bq": "-1"}
        for xx in TAG_STRUCTURE["xx"]
        for mv in ["0"] + list(TAG_STRUCTURE["mainview"])
        for sd in ["0"] + list(TAG_STRUCTURE["sd"])
        for lx in ["0"] + list(TAG_STRUCTURE["lx"])
    ]


# ==================== 主函数 ====================

def main():
    session = get_session()

    print("=" * 70)
    print("晋江文学城元数据爬虫")
    print("参考: https://github.com/dev-chenxing/jjwxc-crawler")
    print("=" * 70)

    # 1. 保存标签结构
    print("\n[1/4] 保存标签结构...")
    with open(OUTPUT_DIR / "tag_structure.json", "w", encoding="utf-8") as f:
        json.dump(TAG_STRUCTURE, f, ensure_ascii=False, indent=2)

    # 2. 爬取小说ID
    print("\n[2/4] 爬取小说列表...")
    combinations = generate_combinations()
    print(f"  共 {len(combinations)} 种组合")

    novel_combos = {}
    for i, combo in enumerate(combinations, 1):
        xx_name = TAG_STRUCTURE["xx"].get(combo["xx"], combo["xx"])
        mv_name = TAG_STRUCTURE["mainview"].get(combo["mainview"], "全部")
        sd_name = TAG_STRUCTURE["sd"].get(combo["sd"], "全部")
        lx_name = TAG_STRUCTURE["lx"].get(combo["lx"], "全部")

        if i % 10 == 0:
            print(f"  进度: {i}/{len(combinations)}")

        combo_ids = set()
        for page in range(1, 6):
            ids = crawl_bookbase(combo, page, session)
            combo_ids.update(ids)
            random_delay()

        if combo_ids:
            label = {
                "xx": combo["xx"], "xx_name": xx_name,
                "mainview": combo["mainview"], "mainview_name": mv_name,
                "sd": combo["sd"], "sd_name": sd_name,
                "lx": combo["lx"], "lx_name": lx_name,
            }
            for nid in combo_ids:
                novel_combos.setdefault(nid, []).append(label)

        random_delay()

    all_novel_ids = set(novel_combos.keys())
    print(f"\n  共发现 {len(all_novel_ids)} 本不重复小说")

    with open(OUTPUT_DIR / "novel_combo_mapping.json", "w", encoding="utf-8") as f:
        json.dump(novel_combos, f, ensure_ascii=False, indent=2)

    # 3. 爬取元数据
    print(f"\n[3/4] 爬取小说元数据...")
    novels = []
    failed_ids = []

    for i, novel_id in enumerate(sorted(all_novel_ids), 1):
        if i % 50 == 0:
            print(f"  进度: {i}/{len(all_novel_ids)} (成功: {len(novels)})")
            with open(OUTPUT_DIR / "novels_metadata_temp.json", "w", encoding="utf-8") as f:
                json.dump(novels, f, ensure_ascii=False, indent=2)

        metadata = extract_novel_metadata(novel_id, session)
        if metadata:
            metadata["source_combos"] = novel_combos.get(novel_id, [])
            metadata["source_tags"] = {
                "orientations": list(set(c["xx_name"] for c in metadata["source_combos"])),
                "views": list(set(c["mainview_name"] for c in metadata["source_combos"] if c["mainview_name"] != "全部")),
                "eras": list(set(c["sd_name"] for c in metadata["source_combos"] if c["sd_name"] != "全部")),
                "genres": list(set(c["lx_name"] for c in metadata["source_combos"] if c["lx_name"] != "全部")),
            }
            novels.append(metadata)
        else:
            failed_ids.append(novel_id)

        random_delay()

    # 4. 保存结果
    print("\n[4/4] 保存结果...")
    with open(OUTPUT_DIR / "novels_metadata.json", "w", encoding="utf-8") as f:
        json.dump(novels, f, ensure_ascii=False, indent=2)

    if failed_ids:
        with open(OUTPUT_DIR / "failed_ids.json", "w", encoding="utf-8") as f:
            json.dump(failed_ids, f)

    stats = {
        "total": len(novels),
        "failed": len(failed_ids),
        "by_orientation": {},
        "tag_stats": {"with_tags": 0, "total_tags": 0},
    }
    for novel in novels:
        if novel["genre"]:
            parts = novel["genre"].split("-")
            if len(parts) >= 2:
                stats["by_orientation"][parts[1]] = stats["by_orientation"].get(parts[1], 0) + 1
        if novel["tags"]:
            stats["tag_stats"]["with_tags"] += 1
            stats["tag_stats"]["total_tags"] += len(novel["tags"])

    with open(OUTPUT_DIR / "crawl_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 70}")
    print(f"完成！共爬取 {len(novels)} 本小说元数据")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
