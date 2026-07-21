"""台文系論文來源：Crossref 的臺灣文學論文書目。"""

from _common import fetch_crossref_works


QUERY = "Taiwan literature"


def collect():
    """回傳最新臺灣文學論文，並統一標示為台文系。"""
    return fetch_crossref_works(QUERY, department="台文系")
