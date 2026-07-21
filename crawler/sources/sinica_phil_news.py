"""學術消息來源：中央研究院中國文哲研究所最新公告與演講。"""

from _common import fetch_html_news

SOURCE_NAME = "中央研究院中國文哲研究所"
NEWS_URL = "https://www.litphil.sinica.edu.tw/news"


def collect():
    """回傳最新中研院文哲所學術活動與公告，並標示為中文系消息。"""
    return fetch_html_news(NEWS_URL, department="中文系", source_name=SOURCE_NAME, url_marker="sinica.edu.tw")
