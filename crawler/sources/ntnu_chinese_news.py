"""系所消息來源：國立臺灣師範大學國文學系最新公告。"""

from _common import fetch_html_news

SOURCE_NAME = "國立臺灣師範大學國文學系"
NEWS_URL = "https://ch.ntnu.edu.tw"


def collect():
    """回傳最新師大國文系公告，並標示為國文系消息。"""
    return fetch_html_news(NEWS_URL, department="國文系", source_name=SOURCE_NAME, url_marker="ntnu.edu.tw")
