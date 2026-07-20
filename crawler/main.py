"""自動執行 crawler/sources 中的所有來源，並合併寫入 papers.json。

新增來源時，只要在 sources 資料夾建立一個含 collect() 函式的 .py 檔，
不需要修改這個主程式。
"""

import importlib.util
import json
import sys
from pathlib import Path


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
SOURCES_DIRECTORY = Path(__file__).resolve().parent / "sources"
PAPERS_FILE = PROJECT_DIRECTORY / "papers.json"
REQUIRED_FIELDS = {"title", "type", "department", "year", "date", "tags", "abstract", "url", "source"}


def discover_sources():
    """載入 sources 資料夾中所有非底線開頭的 Python 模組。"""
    for source_path in sorted(SOURCES_DIRECTORY.glob("*.py")):
        if source_path.name.startswith("_"):
            continue
        module_name = f"crawler_source_{source_path.stem}"
        # 讓來源檔可以匯入同資料夾的 _common.py。
        sys.path.insert(0, str(SOURCES_DIRECTORY))
        try:
            spec = importlib.util.spec_from_file_location(module_name, source_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not callable(getattr(module, "collect", None)):
                print(f"略過 {source_path.name}：缺少 collect() 函式。")
                continue
            yield source_path.stem, module.collect
        finally:
            sys.path.pop(0)


def load_existing_papers():
    """讀取既有資料；不存在或格式錯誤時停止，避免意外覆寫。"""
    if not PAPERS_FILE.exists():
        return []
    data = json.loads(PAPERS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("papers.json 必須是物件陣列。")
    return data


def item_key(item):
    """以來源網址優先去重；沒有網址時以來源、標題與日期組合辨識。"""
    return item.get("url") or "|".join([item.get("source", ""), item.get("title", ""), item.get("date", "")])


def validate_item(item):
    """確認來源提供的項目至少具備前端需要的欄位。"""
    missing = REQUIRED_FIELDS - item.keys()
    if missing:
        raise ValueError(f"缺少欄位：{', '.join(sorted(missing))}")
    if item["department"] not in {"中文系", "國文系", "台文系"}:
        raise ValueError("department 必須是中文系、國文系或台文系。")


def run():
    """執行所有來源，保留舊資料並只加入尚未存在的新項目。"""
    papers = load_existing_papers()
    known_keys = {item_key(item) for item in papers}
    new_items = []

    for source_name, collect in discover_sources():
        try:
            source_items = collect()
            added_count = 0
            for item in source_items:
                validate_item(item)
                key = item_key(item)
                if key not in known_keys:
                    new_items.append(item)
                    known_keys.add(key)
                    added_count += 1
            print(f"{source_name}：讀取 {len(source_items)} 筆，新增 {added_count} 筆。")
        except Exception as error:  # 單一來源失敗不應阻止其他來源更新。
            print(f"{source_name}：略過，原因：{error}")

    if new_items:
        # 最新抓取的資料優先顯示，既有資料與手動測試資料都會保留。
        PAPERS_FILE.write_text(json.dumps(new_items + papers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完成：共新增 {len(new_items)} 筆資料。")


if __name__ == "__main__":
    run()
