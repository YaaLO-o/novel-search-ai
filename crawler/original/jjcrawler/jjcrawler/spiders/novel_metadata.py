"""
晋江文学城元数据爬虫（只爬元数据，不下载章节）
基于原爬虫 novel_list.py 修改
数据保存到 JSON 文件：data/raw/jjwxc/YYYY-MM-DD/{novel_id}.json

特性：
- 自动保存进度，下次可继续
- 自动遍历所有分类组合
- 爬完所有组合后自动进入下一轮（从更深的页码继续）
"""

import re
import json
import scrapy
from datetime import datetime
from scrapy.http import Response
from scrapy import signals
from pathlib import Path
from rich.console import Console
from .utils import process_desc, set_log_level, get_novel_title

# 输出目录
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "raw" / "jjwxc"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# 进度文件
PROGRESS_FILE = BASE_DIR / "crawl_progress.json"

# 标签体系
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

# 每个组合爬取的页数
PAGES_PER_COMBO = 20


def load_progress() -> dict:
    """加载上次的进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"crawled_ids": [], "total_crawled": 0, "last_run": "", "combo_index": 0, "page_index": 0, "round": 1}


def save_progress(progress: dict):
    """保存进度"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def generate_combinations() -> list:
    """生成所有分类组合"""
    combos = []
    for xx in TAG_STRUCTURE["xx"]:
        for mv in ["0"] + list(TAG_STRUCTURE["mainview"].keys()):
            for sd in ["0"] + list(TAG_STRUCTURE["sd"].keys()):
                for lx in ["0"] + list(TAG_STRUCTURE["lx"].keys()):
                    combos.append({"xx": xx, "mainview": mv, "sd": sd, "lx": lx, "bq": "-1"})
    return combos


class NovelMetadataSpider(scrapy.Spider):
    """只爬取元数据，不下载章节"""
    name = "metadata"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)
        return spider

    def __init__(self, xx=None, yc=None, title: str = None, sd=None, mainview=None, bq=-1, *args, **kwargs):
        set_log_level()
        super(NovelMetadataSpider, self).__init__(*args, **kwargs)

        # 初始化
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = BASE_DIR / self.today
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载进度
        self.progress = load_progress()
        self.crawled_ids = set(self.progress["crawled_ids"])

        # 本次运行计数
        self.count = 0

        # 控制台和进度条
        self.console = Console()
        self.console.print(f"\n[bold green]上次已爬取: {self.progress['total_crawled']} 本[/]\n")

        # 生成所有组合
        self.combinations = generate_combinations()
        self.console.print(f"[bold cyan]共 {len(self.combinations)} 种分类组合[/]")

        # 从上次进度继续
        self.combo_index = self.progress.get("combo_index", 0)
        self.page_index = self.progress.get("page_index", 0)
        self.current_round = self.progress.get("round", 1)
        self.console.print(f"[bold cyan]当前轮次: 第 {self.current_round} 轮[/]\n")

        # 设置起始URL
        self._set_start_urls()

    def start_requests(self):
        """生成初始请求"""
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def spider_idle(self):
        """爬虫即将空闲时，尝试启动下一组的请求"""
        # 推进到下一个组合
        self._advance_to_next_combo()

        if self.start_urls:
            # 有新的 URL，启动请求
            self.logger.info(f"启动下一组请求: combo_index={self.combo_index}")
            for url in self.start_urls:
                req = scrapy.Request(url, callback=self.parse)
                self.crawler.engine.crawl(req)
            return False  # 返回 False 阻止爬虫进入空闲状态

    def _set_start_urls(self):
        """根据当前组合索引设置起始URL"""
        self.start_urls = []
        self.allowed_domains = ["www.jjwxc.net"]
        self.mobile_pages = False

        # 跳过无效组合（mainview=0 在晋江不支持）
        while self.combo_index < len(self.combinations):
            combo = self.combinations[self.combo_index]
            if combo["mainview"] != "0":
                break
            self.combo_index += 1

        if self.combo_index < len(self.combinations):
            combo = self.combinations[self.combo_index]
            self.current_combo = combo
            sd_text = f"sd{combo['sd']}={combo['sd']}&" if combo["sd"] != "0" else ""
            # 计算实际页码：当前轮次的偏移 + 当前页索引
            actual_page_start = (self.current_round - 1) * PAGES_PER_COMBO + self.page_index + 1
            actual_page_end = actual_page_start + PAGES_PER_COMBO
            self.start_urls = [
                f"https://www.jjwxc.net/bookbase.php?xx{combo['xx']}={combo['xx']}&mainview={combo['mainview']}&bq={combo['bq']}&{sd_text}lx={combo['lx']}&page={i}"
                for i in range(actual_page_start, actual_page_end)
            ]

    def _advance_to_next_combo(self):
        """推进到下一个组合，如果所有组合完成则进入下一轮"""
        self.combo_index += 1
        self.page_index = 0

        if self.combo_index >= len(self.combinations):
            # 所有组合完成，进入下一轮
            self.current_round += 1
            self.combo_index = 0
            self.console.print(f"\n[bold yellow]{'=' * 50}[/]")
            self.console.print(f"[bold yellow]第 {self.current_round - 1} 轮完成，进入第 {self.current_round} 轮[/]")
            self.console.print(f"[bold cyan]从第 {(self.current_round - 1) * PAGES_PER_COMBO + 1} 页继续爬取[/]")
            self.console.print(f"[bold yellow]{'=' * 50}[/]\n")

        self.progress["combo_index"] = self.combo_index
        self.progress["page_index"] = self.page_index
        self.progress["round"] = self.current_round
        self._set_start_urls()

    def parse(self, response: Response):
        """解析列表页，提取小说链接"""
        # 小说链接在页面各处，统一提取所有 onebook.php 链接
        novel_links = response.css("a[href*='onebook.php']::attr(href)").getall()

        if not novel_links:
            return

        # 去重（同一本小说可能有多个链接）
        seen = set()
        for href in novel_links:
            if href in seen:
                continue
            seen.add(href)
            url = f"https://www.jjwxc.net/{href}"
            yield response.follow(url, callback=self.parse_novel)

    def parse_novel(self, response: Response):
        """解析详情页，只提取元数据，不下载章节"""
        novel = self.get_novel_item(response)

        if novel:
            # 检查是否已爬取过
            if novel["platform_id"] in self.crawled_ids:
                return

            self.save_novel(novel)
            self.crawled_ids.add(novel["platform_id"])
            self.count += 1

            # 更新进度
            self.progress["crawled_ids"] = list(self.crawled_ids)
            self.progress["total_crawled"] = len(self.crawled_ids)
            self.progress["last_run"] = datetime.now().isoformat()

            # 每10本保存一次进度
            if self.count % 10 == 0:
                save_progress(self.progress)
                xx_name = TAG_STRUCTURE["xx"].get(self.current_combo["xx"], "?")
                self.console.print(
                    f"[cyan]进度: {self.count} | "
                    f"总计: {self.progress['total_crawled']} | "
                    f"[{xx_name}] {novel['title']}[/]"
                )

    def get_novel_item(self, response) -> dict | None:
        """提取小说元数据，返回标准格式"""
        title = get_novel_title(response, is_mobile_pages=False)
        if title is None:
            return None

        platform_id = re.findall(r"\d+", response.url)[0]

        # 跳过小树苗
        page_title = response.css("title::text").get()
        if re.findall("小树苗", page_title):
            return None

        # ===== 提取各字段 =====

        # 作者
        author = response.css("a[href*='oneauthor']::text").get(default="").strip()
        author_link = response.css("a[href*='oneauthor']::attr(href)").get()
        author_id = ""
        if author_link:
            author_match = re.findall(r"authorid=(\d+)", author_link)
            author_id = author_match[0] if author_match else ""

        # 类型
        genre_text = response.css(".rightul span::text")
        genre = genre_text[1].get().strip() if len(genre_text) > 1 else ""
        genre_parts = genre.split("-")

        # 解析 category
        category = {"channel": "", "sub_channel": ""}
        if len(genre_parts) >= 2:
            category["channel"] = genre_parts[1]  # 言情/纯爱/百合/无CP
        if len(genre_parts) >= 3:
            category["sub_channel"] = genre_parts[2]  # 近代现代/古色古香/架空历史/幻想未来

        # 字数
        word_count_text = response.xpath(
            "//span[@itemprop='wordCount']/text()").get()
        word_count = int(word_count_text[:-1]) if word_count_text else 0

        # 标签
        raw_tags = response.css("div.smallreadbody span a::text").getall()

        # 一句话简介、立意
        smallreadbody = response.css("div.smallreadbody span::text")
        oneliner = smallreadbody[-2].get().strip() if len(smallreadbody) >= 2 else ""
        meaning = smallreadbody[-1].get().strip() if smallreadbody else ""

        # 简介
        intro = process_desc(response.xpath('//*[@id="novelintro"]/node()'))
        if intro:
            intro = "\n".join(intro) if isinstance(intro, list) else str(intro)

        # 状态
        status = response.css("span.novelstatus::text").get(default="").strip()

        # VIP/免费状态
        vip = "VIP" in (response.css("span.novelstatus::text").get(default="") +
                        response.css(".rightul span::text").getall().__str__())
        free = "免费" in genre or "免费" in status

        # 评分、收藏数
        metrics = {}
        score_text = response.css("span[property='v:average']::text").get(default="").strip()
        collects_text = response.css("span[property='v:reviews']::text").get(default="").strip()

        if score_text:
            metrics["评分"] = score_text
        if collects_text:
            metrics["收藏"] = collects_text

        # 封面URL
        cover_url = response.css("img.novelimage::attr(src)").get(default="")
        if cover_url and not cover_url.startswith("http"):
            cover_url = f"https://www.jjwxc.net{cover_url}"

        # 更新时间
        update_time = response.css("span[itemprop='dateModified']::text").get(default="").strip()

        # 构建标准格式
        novel_data = {
            "platform": "jjwxc",
            "platform_id": platform_id,
            "url": f"https://www.jjwxc.net/onebook.php?novelid={platform_id}",
            "title": title,
            "author": author,
            "author_id": author_id,
            "intro": intro,
            "cover_url": cover_url,
            "status": status,
            "vip": vip,
            "free": free,
            "word_count": word_count,
            "chapter_count": 0,
            "publish_time": "",
            "update_time": update_time,
            "raw_tags": raw_tags,
            "category": category,
            "metrics": metrics,
            "crawl_time": datetime.now().isoformat(),
        }

        return novel_data

    def save_novel(self, novel: dict):
        """保存小说到JSON文件"""
        try:
            file_path = self.output_dir / f"{novel['platform_id']}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(novel, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存失败: {e}")

    def closed(self, reason):
        """爬虫关闭时保存进度"""
        save_progress(self.progress)
        self.console.print(f"\n[bold green]{'=' * 50}[/]")
        self.console.print(f"[bold green]爬取完成！[/]")
        self.console.print(f"[bold]本次爬取: {self.count} 本[/]")
        self.console.print(f"[bold]总计爬取: {self.progress['total_crawled']} 本[/]")
        self.console.print(f"[bold]当前轮次: 第 {self.current_round} 轮[/]")
        self.console.print(f"[bold]数据目录: {self.output_dir}[/]")
        self.console.print(f"[bold green]{'=' * 50}[/]\n")
