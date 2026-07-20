"""在本機提供網站與筆記儲存功能的最小工具。

執行此檔案後，瀏覽器中的新增筆記表單會把資料寫回同資料夾的 notes.json。
只綁定本機網址，因此不會讓其他裝置連線或修改你的筆記。
"""

import json
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


# 所有檔案都以這個程式所在的專案資料夾為準，避免從別處啟動時找不到 notes.json。
PROJECT_DIRECTORY = Path(__file__).resolve().parent
NOTES_FILE = PROJECT_DIRECTORY / "notes.json"
ALLOWED_DEPARTMENTS = {"中文系", "國文系", "台文系"}


class NoteEditorHandler(SimpleHTTPRequestHandler):
    """提供靜態檔案，並額外處理新增筆記的 API 請求。"""

    def __init__(self, *args, **kwargs):
        # directory 參數讓首頁與 JSON 一律從專案資料夾讀取。
        super().__init__(*args, directory=str(PROJECT_DIRECTORY), **kwargs)

    def send_json(self, status, data):
        """回傳 JSON 給網頁，讓前端能知道儲存是否成功。"""
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_POST(self):
        """只接受寫入筆記的 /api/notes 請求。"""
        if self.path != "/api/notes":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "找不到此功能。"})
            return

        try:
            payload = self.read_payload()
            note = self.create_note(payload)
            notes = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            # 新筆記放最前面，首頁會優先看到最新內容。
            notes.insert(0, note)
            NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.send_json(HTTPStatus.CREATED, {"note": note})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except OSError:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "無法寫入 notes.json，請確認檔案沒有被其他程式鎖定。"})

    def do_PUT(self):
        """依筆記 id 覆寫既有筆記，並保留原本的 id 與日期。"""
        note_id = self.note_id_from_path()
        if not note_id:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "找不到此筆記。"})
            return
        try:
            payload = self.read_payload()
            notes = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            for index, existing_note in enumerate(notes):
                if existing_note.get("id") == note_id:
                    updated_note = self.create_note(payload)
                    updated_note["id"] = existing_note["id"]
                    updated_note["date"] = existing_note["date"]
                    notes[index] = updated_note
                    NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    self.send_json(HTTPStatus.OK, {"note": updated_note})
                    return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "找不到此筆記。"})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except OSError:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "無法寫入 notes.json，請確認檔案沒有被其他程式鎖定。"})

    def do_DELETE(self):
        """依筆記 id 刪除一筆資料；前端已先顯示確認提示。"""
        note_id = self.note_id_from_path()
        if not note_id:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "找不到此筆記。"})
            return
        try:
            notes = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            remaining_notes = [note for note in notes if note.get("id") != note_id]
            if len(remaining_notes) == len(notes):
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "找不到此筆記。"})
                return
            NOTES_FILE.write_text(json.dumps(remaining_notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.send_json(HTTPStatus.OK, {"message": "筆記已刪除。"})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except OSError:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "無法寫入 notes.json，請確認檔案沒有被其他程式鎖定。"})

    def read_payload(self):
        """讀取並檢查前端送來的 JSON，三種寫入操作共用。"""
        content_length = int(self.headers.get("Content-Length", "0"))
        # 限制請求大小，避免意外寫入過大的文字。
        if content_length > 10_000:
            raise ValueError("筆記內容過長，請縮短後再試。")
        return json.loads(self.rfile.read(content_length).decode("utf-8"))

    def note_id_from_path(self):
        """從 /api/notes/<id> 取出筆記 id；其他路徑一律視為無效。"""
        prefix = "/api/notes/"
        if not self.path.startswith(prefix):
            return None
        note_id = unquote(self.path[len(prefix):])
        return note_id or None

    @staticmethod
    def create_note(payload):
        """檢查表單輸入，轉換為 notes.json 所使用的資料格式。"""
        title = str(payload.get("title", "")).strip()
        content = str(payload.get("content", "")).strip()
        department = str(payload.get("department", "")).strip()
        tags = [tag.strip() for tag in str(payload.get("tags", "")).split(",") if tag.strip()]
        if not content:
            raise ValueError("請填寫筆記內容。")
        if department not in ALLOWED_DEPARTMENTS:
            raise ValueError("請選擇正確的領域。")
        if not tags:
            raise ValueError("請至少填寫一個標籤。")
        now = datetime.now()
        return {
            "id": now.strftime("%Y-%m-%d-%H%M%S"),
            "date": now.strftime("%Y-%m-%d"),
            "title": title,
            "content": content,
            "department": department,
            "tags": tags,
        }


if __name__ == "__main__":
    # 127.0.0.1 代表只有這台電腦能開啟網站，避免意外對外公開寫入功能。
    server = ThreadingHTTPServer(("127.0.0.1", 8000), NoteEditorHandler)
    print("筆記工具已啟動：請開啟 http://127.0.0.1:8000")
    print("停止工具：回到這個視窗，按 Ctrl + C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n筆記工具已停止。")
    finally:
        server.server_close()
