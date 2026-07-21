"""每日摘要通知腳本：彙整當日新抓取的論文／消息，並發送 Web Push 摘要。

只會篩選 first_seen 欄位為今天日期的全新項目進行推播，避免重複通知舊內容。
"""

from datetime import datetime
import json
import os
from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
PAPERS_FILE = PROJECT_DIRECTORY / "papers.json"


def main():
    print("開始執行每日摘要通知流程...")

    if not PAPERS_FILE.exists():
        print("未偵測到 papers.json，取消摘要發送。")
        return

    try:
        papers = json.loads(PAPERS_FILE.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"讀取 papers.json 失敗：{error}")
        return

    # 篩選今日新抓取的項目 (first_seen 等於今天)
    today = datetime.now().date().isoformat()
    today_items = [item for item in papers if item.get("first_seen") == today]

    print(f"今日新抓取的項目共 {len(today_items)} 筆（篩選條件 first_seen = {today}）。")

    if not today_items:
        print("今日無全新抓取項目，發送「今日無更新」通知。")
        message_title = "中文／國文／台文系每日資訊站"
        message_content = "今日無新論文或系所消息更新。祝您有美好的一天！"
    else:
        # 分類統計與彙整摘要文字
        papers_count = len([i for i in today_items if i.get("type") == "paper"])
        news_count = len([i for i in today_items if i.get("type") == "news"])
        message_title = f"今日新增 {len(today_items)} 筆學術消息！"
        message_content = f"新增 {papers_count} 篇論文期刊、{news_count} 則系所消息公告。點擊此處立即查看！"

        print("摘要明細：")
        for index, item in enumerate(today_items, 1):
            print(f"  {index}. [{item.get('type')}] {item.get('title')} ({item.get('source')})")

    # 發送 Web Push 推播
    app_id = os.environ.get("ONESIGNAL_APP_ID")
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY")

    if not app_id or not api_key:
        print("未偵測到 OneSignal 金鑰 (ONESIGNAL_APP_ID / ONESIGNAL_REST_API_KEY)，跳過 API 發送。")
        print(f"模擬推播主旨：{message_title}")
        print(f"模擬推播內容：{message_content}")
        return

    print("正在呼叫 OneSignal API 發送推播...")
    # 未來階段整合 OneSignal REST API 呼叫


if __name__ == "__main__":
    main()
