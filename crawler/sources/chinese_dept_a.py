"""中文系論文來源：Crossref 的中文文學論文書目。"""

from _common import fetch_crossref_works


QUERY = "Chinese literature"


def collect():
    """回傳最新中文文學論文，並統一標示為中文系。"""
    return fetch_crossref_works(QUERY, department="中文系")
