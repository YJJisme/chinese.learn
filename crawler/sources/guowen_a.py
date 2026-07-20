"""國文系起始來源：國立臺灣師範大學國文學系公告 RSS。"""

from _common import fetch_rss_items


SOURCE_NAME = "國立臺灣師範大學國文學系"
RSS_URL = "https://www.chinese.ntnu.edu.tw/?feed=rss2"


def collect():
    """回傳最新國文系公告，並統一標示為國文系。"""
    return fetch_rss_items(RSS_URL, department="國文系", source_name=SOURCE_NAME)
