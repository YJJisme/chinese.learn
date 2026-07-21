"""每日摘要通知腳本：彙整當日新抓取的論文／消息，並發送 Web Push 摘要。

當前階段：驗證版。若未設定 OneSignal 金鑰，將印出摘要內容並安全跳過。
"""

import os
import sys
from pathlib import Path


def main():
    print("開始執行每日摘要通知流程...")
    app_id = os.environ.get("ONESIGNAL_APP_ID")
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY")

    if not app_id or not api_key:
        print("未偵測到 OneSignal API 金鑰 (ONESIGNAL_APP_ID / ONESIGNAL_REST_API_KEY)，將跳過推播發送。")
        return

    print("已設定 OneSignal 金鑰，準備發送推播...")
    # 未來階段呼叫 OneSignal API 推播發送邏輯


if __name__ == "__main__":
    main()
