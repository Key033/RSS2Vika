import feedparser
from vika import Vika
import requests
import re
from datetime import datetime, timezone, timedelta
from dateutil import parser

now = datetime.now(timezone.utc).timestamp()
delete_day = 14  # 删除14天前的内容
delete_timestamp = (now - delete_day * 86400) * 1000  # 毫秒时间戳
load_day = 10  # 导入10天内的内容
load_time = load_day * 86400


def parse_rss(rss_info: dict):
    entries = []
    try:
        res = requests.get(
            rss_info.get("url"),
            headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36 Edg/96.0.1054.34"},
        )
        feed = feedparser.parse(res.text)
    except requests.exceptions.ProxyError or requests.exceptions.SSLError or ConnectionResetError:
        print("加载失败")
        return [1]
    except requests.exceptions.ConnectTimeout:
        print("加载超时")
        return [1]
    for entry in feed.entries:
        if entry.get("published"):
            published_time = parser.parse(entry.get("published"))
        else:
            published_time = datetime.now(timezone.utc)
        if not published_time.tzinfo:
            published_time = published_time.replace(tzinfo=timezone(timedelta(hours=8)))
        if now - published_time.timestamp() < load_time:
            entries.append(
                {
                    "title": entry.get("title"),
                    "link": entry.get("link"),
                    "time": published_time.timestamp() * 1000,
                    "summary": re.sub(r"<.*?>|\n*", "", entry.get("summary")),
                    "rss": rss_info,
                }
            )
    return entries


def read_rss(api):
    for rss in api.query_open_rss():
        print(f"☆ 加载 {rss.get('title')}")
        entries = parse_rss(rss)
        if len(entries) == 0:
            print(f"{load_day} 天内无新内容")
            continue
        elif entries[0] == 1:
            continue
        records = Vika(api.vika).datasheet(api.clipper).records.filter(来源=entries[0].get("rss").get("title"))
        urls = [x.json()["链接"] for x in records]
        repeat_flag = 0
        for entry in entries:
            if entry.get("link") not in urls:
                data = {
                    "标题": entry.get("title"),
                    "链接": entry.get("link"),
                    "来源": entry.get("rss").get("title"),
                    "发布时间": entry.get("time"),
                    "摘要": entry.get("summary"),
                }
                Vika(api.vika).datasheet(api.clipper).records.create([data])
                urls += [entry.get("link")]
            else:
                repeat_flag += 1
        print(f"读取到 {len(entries)} 篇内容，其中重复 {repeat_flag} 篇。")


class VikaApi:
    def __init__(self, api, clipper, feeds) -> None:
        self.vika = api
        self.clipper = clipper
        self.feeds = feeds
        self.delete_rss()

    def delete_rss(self):
        records = Vika(self.vika).datasheet(self.clipper).records.filter(已读=True)
        counter = 0
        for record in records:
            if record.发布时间 < delete_timestamp:
                record.delete()
                counter += 1
            if counter > 9:
                records = Vika(self.vika).datasheet(self.clipper).records.filter(已读=True)
                counter = 0

    def query_open_rss(self):
        records = Vika(self.vika).datasheet(self.feeds).records.filter(启用=True)
        rss_list = [
            {
                "url": r.json()["网站"],
                "title": r.json()["标题"],
            }
            for r in records
        ]
        return rss_list
