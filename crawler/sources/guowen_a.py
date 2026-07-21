"""國文系論文來源：Crossref 的古典中文文學論文書目。"""

from _common import fetch_crossref_works


QUERY = "classical Chinese literature"


def collect():
    """回傳最新古典中文文學論文，並統一標示為國文系。"""
    return fetch_crossref_works(QUERY, department="國文系")
