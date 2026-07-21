"""開放取用期刊 (DOAJ) 論文來源：彙整中文系、國文系與台文系相關開放論文。"""

from _common import fetch_doaj_articles


def collect():
    """分別檢索三個領域的 DOAJ 開放期刊論文。"""
    items = []
    # 1. 中文系領域
    try:
        items.extend(fetch_doaj_articles("Chinese literature", department="中文系", limit=5))
    except Exception as e:
        print(f"DOAJ (中文系) 讀取跳過: {e}")

    # 2. 國文系領域
    try:
        items.extend(fetch_doaj_articles("Classical Chinese literature", department="國文系", limit=5))
    except Exception as e:
        print(f"DOAJ (國文系) 讀取跳過: {e}")

    # 3. 台文系領域
    try:
        items.extend(fetch_doaj_articles("Taiwan literature", department="台文系", limit=5))
    except Exception as e:
        print(f"DOAJ (台文系) 讀取跳過: {e}")

    return items
