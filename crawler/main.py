from datetime import datetime
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
    """
    用 url 欄位作為唯一識別依據；
    如果沒有 url，退而用「標題 + 期刊/來源 + 年份」組合當作識別。
    """
    url = item.get("url", "").strip()
    if url:
        return url

    title = item.get("title", "").strip()
    source = item.get("journal", "").strip() or item.get("source", "").strip()
    year = str(item.get("year", "")).strip()
    return f"{title}|{source}|{year}"


def validate_item(item):
    """確認來源提供的項目至少具備前端需要的欄位。"""
    missing = REQUIRED_FIELDS - item.keys()
    if missing:
        raise ValueError(f"缺少欄位：{', '.join(sorted(missing))}")
    if item["department"] not in {"中文系", "國文系", "台文系"}:
        raise ValueError("department 必須是中文系、國文系或台文系。")


def merge_updates(existing, scraped):
    """將抓到的新內容合併至現有項目中，如果有更有價值的新增欄位，回傳 True 表示有更新。"""
    updated = False
    fields_to_check = ["title", "authors", "type", "department", "journal", "volume", "issue", "year", "date", "keywords", "tags", "abstract", "url", "pdf", "doi", "source"]
    for field in fields_to_check:
        new_val = scraped.get(field)
        old_val = existing.get(field)

        if new_val:
            if isinstance(new_val, str):
                old_str = old_val or ""
                if new_val.strip() != old_str.strip() and len(new_val.strip()) > len(old_str.strip()):
                    existing[field] = new_val
                    updated = True
            elif isinstance(new_val, list):
                old_list = old_val or []
                if len(new_val) > len(old_list):
                    existing[field] = new_val
                    updated = True
            else:
                if new_val != old_val:
                    existing[field] = new_val
                    updated = True
    return updated


def run():
    """執行所有來源，保留舊資料、更新內容，並只加入尚未存在的新項目。"""
    papers = load_existing_papers()
    papers_map = {item_key(item): item for item in papers}
    new_items = []
    updated_any = False
    today = datetime.now().date().isoformat()

    for source_name, collect in discover_sources():
        try:
            source_items = collect()
            added_count = 0
            updated_count = 0
            for item in source_items:
                validate_item(item)
                key = item_key(item)
                if key not in papers_map:
                    # 這是全新項目，加上 first_seen 欄位
                    item["first_seen"] = today
                    new_items.append(item)
                    papers_map[key] = item
                    added_count += 1
                else:
                    # 項目已存在，檢查是否需要合併更新內容（保留原 first_seen）
                    if merge_updates(papers_map[key], item):
                        updated_count += 1
                        updated_any = True
            print(f"{source_name}：讀取 {len(source_items)} 筆，新增 {added_count} 筆，更新 {updated_count} 筆。")
        except Exception as error:  # 單一來源失敗不應阻止其他來源更新。
            print(f"{source_name}：略過，原因：{error}")

    if new_items or updated_any:
        # 最新抓取的全新資料排在最前面，舊有資料順序保留（已在 papers 串列中就地修改）
        all_papers = new_items + papers
        PAPERS_FILE.write_text(json.dumps(all_papers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"完成：共新增 {len(new_items)} 筆，有更新既有項目：{updated_any}。")


if __name__ == "__main__":
    run()
