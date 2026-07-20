"""台文系起始來源：國立臺灣文學館新聞公告 RSS。"""

from _common import fetch_rss_items


SOURCE_NAME = "國立臺灣文學館"
RSS_URL = "https://www.nmtl.gov.tw/rss.xml"


def collect():
    """回傳最新臺灣文學公告，並統一標示為台文系。"""
    return fetch_rss_items(RSS_URL, department="台文系", source_name=SOURCE_NAME)
