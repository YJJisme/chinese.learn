"""輔助消息來源：國立臺灣文學館官方新聞公告。"""

from _common import fetch_html_news


SOURCE_NAME = "國立臺灣文學館"
NEWS_URL = "https://www.nmtl.gov.tw/News.aspx?n=3891&sms=13121"


def collect():
    """回傳最新臺灣文學消息，並標示為台文系。"""
    return fetch_html_news(NEWS_URL, department="台文系", source_name=SOURCE_NAME, url_marker="News_Content.aspx")
