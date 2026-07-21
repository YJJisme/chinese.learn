"""系所消息來源：國立臺灣大學中國文學系最新公告。"""

from _common import fetch_html_news

SOURCE_NAME = "國立臺灣大學中國文學系"
NEWS_URL = "https://www.cl.ntu.edu.tw/web/news/news.jsp"


def collect():
    """回傳最新台大中文系公告，並標示為中文系消息。"""
    return fetch_html_news(NEWS_URL, department="中文系", source_name=SOURCE_NAME, url_marker="news_in.jsp")
