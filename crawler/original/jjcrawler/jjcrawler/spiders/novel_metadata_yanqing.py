"""
晋江文学城元数据爬虫 - 言情专用版
只爬取言情(xx=1)分类下的所有小说元数据
数据保存到 JSON 文件：data/raw/jjwxc/YYYY-MM-DD/{novel_id}.json

特性：
- 自动保存进度，下次可继续
- 自动翻页直到所有页面爬完
- 去重：已爬取的小说自动跳过
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

# 进度文件（言情专用）
PROGRESS_FILE = BASE_DIR / "crawl_progress_yanqing.json"

# 每次爬取的页数
PAGES_PER_RUN = 20


def load_progress() -> dict:
    """加载上次的进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"crawled_ids": [], "total_crawled": 0, "last_run": "", "current_page": 1}


def save_progress(progress: dict):
    """保存进度"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


class NovelMetadataYanqingSpider(scrapy.Spider):
    """只爬取言情(xx=1)分类下的所有小说元数据"""
    name = "metadata-yanqing"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)
        return spider

    def __init__(self, *args, **kwargs):
        set_log_level()
        super(NovelMetadataYanqingSpider, self).__init__(*args, **kwargs)

        # 初始化
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.output_dir = BASE_DIR / self.today
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载进度
        self.progress = load_progress()
        self.crawled_ids = set(self.progress["crawled_ids"])

        # 本次运行计数
        self.count = 0

        # 控制台
        self.console = Console()
        self.console.print(f"\n[bold green]上次已爬取: {self.progress['total_crawled']} 本（言情）[/]\n")

        # 从上次页码继续
        self.current_page = self.progress.get("current_page", 1)
        self.console.print(f"[bold cyan]从第 {self.current_page} 页开始[/]\n")

        # 设置起始URL
        self._set_start_urls()

    def start_requests(self):
        """生成初始请求"""
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def spider_idle(self):
        """爬虫即将空闲时，启动下一批请求"""
        self._load_next_batch()

        if self.start_urls:
            self.logger.info(f"启动下一批请求: page={self.current_page}")
            for url in self.start_urls:
                req = scrapy.Request(url, callback=self.parse)
                self.crawler.engine.crawl(req)
            return False

    def _set_start_urls(self):
        """设置起始URL（言情分类，不带其他筛选）"""
        self.start_urls = []
        self.allowed_domains = ["www.jjwxc.net"]
        self.mobile_pages = False

        # 只用 xx1=1，不加 mainview/sd/lx 筛选
        page_end = self.current_page + PAGES_PER_RUN
        self.start_urls = [
            f"https://www.jjwxc.net/bookbase.php?xx1=1&page={i}"
            for i in range(self.current_page, page_end)
        ]

    def _load_next_batch(self):
        """加载下一批页面"""
        self.current_page += PAGES_PER_RUN
        self.progress["current_page"] = self.current_page
        self._set_start_urls()

    def parse(self, response: Response):
        """解析列表页，提取小说链接"""
        novel_links = response.css("a[href*='onebook.php']::attr(href)").getall()

        if not novel_links:
            return

        seen = set()
        for href in novel_links:
            if href in seen:
                continue
            seen.add(href)
            url = f"https://www.jjwxc.net/{href}"
            yield response.follow(url, callback=self.parse_novel)

    def parse_novel(self, response: Response):
        """解析详情页，只提取元数据"""
        novel = self.get_novel_item(response)

        if novel:
            if novel["platform_id"] in self.crawled_ids:
                return

            self.save_novel(novel)
            self.crawled_ids.add(novel["platform_id"])
            self.count += 1

            self.progress["crawled_ids"] = list(self.crawled_ids)
            self.progress["total_crawled"] = len(self.crawled_ids)
            self.progress["last_run"] = datetime.now().isoformat()

            if self.count % 10 == 0:
                save_progress(self.progress)
                self.console.print(
                    f"[cyan]进度: {self.count} | "
                    f"总计: {self.progress['total_crawled']} | "
                    f"[言情] {novel['title']}[/]"
                )

    def get_novel_item(self, response) -> dict | None:
        """提取小说元数据"""
        title = get_novel_title(response, is_mobile_pages=False)
        if title is None:
            return None

        platform_id = re.findall(r"\d+", response.url)[0]

        page_title = response.css("title::text").get()
        if re.findall("小树苗", page_title):
            return None

        author = response.css("a[href*='oneauthor']::text").get(default="").strip()
        author_link = response.css("a[href*='oneauthor']::attr(href)").get()
        author_id = ""
        if author_link:
            author_match = re.findall(r"authorid=(\d+)", author_link)
            author_id = author_match[0] if author_match else ""

        genre_text = response.css(".rightul span::text")
        genre = genre_text[1].get().strip() if len(genre_text) > 1 else ""
        genre_parts = genre.split("-")

        category = {"channel": "", "sub_channel": ""}
        if len(genre_parts) >= 2:
            category["channel"] = genre_parts[1]
        if len(genre_parts) >= 3:
            category["sub_channel"] = genre_parts[2]

        word_count_text = response.xpath("//span[@itemprop='wordCount']/text()").get()
        word_count = int(word_count_text[:-1]) if word_count_text else 0

        raw_tags = response.css("div.smallreadbody span a::text").getall()

        smallreadbody = response.css("div.smallreadbody span::text")
        oneliner = smallreadbody[-2].get().strip() if len(smallreadbody) >= 2 else ""
        meaning = smallreadbody[-1].get().strip() if smallreadbody else ""

        intro = process_desc(response.xpath('//*[@id="novelintro"]/node()'))
        if intro:
            intro = "\n".join(intro) if isinstance(intro, list) else str(intro)

        status = response.css("span.novelstatus::text").get(default="").strip()

        vip = "VIP" in (response.css("span.novelstatus::text").get(default="") +
                        response.css(".rightul span::text").getall().__str__())
        free = "免费" in genre or "免费" in status

        metrics = {}
        score_text = response.css("span[property='v:average']::text").get(default="").strip()
        collects_text = response.css("span[property='v:reviews']::text").get(default="").strip()
        if score_text:
            metrics["评分"] = score_text
        if collects_text:
            metrics["收藏"] = collects_text

        cover_url = response.css("img.novelimage::attr(src)").get(default="")
        if cover_url and not cover_url.startswith("http"):
            cover_url = f"https://www.jjwxc.net{cover_url}"

        update_time = response.css("span[itemprop='dateModified']::text").get(default="").strip()

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
        self.console.print(f"[bold green]爬取完成！（言情）[/]")
        self.console.print(f"[bold]本次爬取: {self.count} 本[/]")
        self.console.print(f"[bold]总计爬取: {self.progress['total_crawled']} 本[/]")
        self.console.print(f"[bold]当前页码: 第 {self.current_page} 页[/]")
        self.console.print(f"[bold]数据目录: {self.output_dir}[/]")
        self.console.print(f"[bold green]{'=' * 50}[/]\n")
