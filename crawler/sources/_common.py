"""三個爬蟲來源共用的 RSS 讀取與資料轉換工具。"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree


USER_AGENT = "ChineseLearnDailyInfoBot/1.0 (personal academic news reader)"


def fetch_rss_items(feed_url, *, department, source_name, limit=10):
    """讀取 RSS 或 Atom feed，轉成 papers.json 使用的統一欄位。

    網站格式可能隨時改變，因此網路與 XML 錯誤會交給 main.py 記錄，
    而不是產生空資料並覆蓋現有 papers.json。
    """
    request = Request(feed_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            xml_data = response.read()
    except URLError as error:
        raise RuntimeError(f"無法讀取 {feed_url}：{error.reason}") from error

    try:
        root = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError as error:
        raise RuntimeError(f"{feed_url} 回傳的內容不是有效 RSS／Atom XML。") from error

    # RSS 使用 item，Atom 使用 entry；支援兩種常見格式。
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    if not entries:
        raise RuntimeError(f"{feed_url} 沒有找到可讀取的項目。")

    items = []
    for entry in entries[:limit]:
        item = _entry_to_item(entry, department=department, source_name=source_name)
        if item:
            items.append(item)
    return items


def _entry_to_item(entry, *, department, source_name):
    """將一筆 RSS 或 Atom 項目安全地轉成網站使用的 schema。"""
    title = _text(entry, "title") or _text(entry, "{http://www.w3.org/2005/Atom}title")
    if not title:
        return None
    link = _text(entry, "link") or _text(entry, "{http://www.w3.org/2005/Atom}link")
    atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
    if atom_link is not None:
        link = atom_link.get("href") or link
    description = (
        _text(entry, "description")
        or _text(entry, "{http://www.w3.org/2005/Atom}summary")
        or _text(entry, "{http://www.w3.org/2005/Atom}content")
        or ""
    )
    published = (
        _text(entry, "pubDate")
        or _text(entry, "{http://www.w3.org/2005/Atom}updated")
        or _text(entry, "{http://www.w3.org/2005/Atom}published")
    )
    date = _normalise_date(published)
    tags = [_text(category, "") for category in entry.findall("category") if _text(category, "")]
    return {
        "title": unescape(title).strip(),
        "authors": [],
        "type": "news",
        "department": department,
        "journal": "",
        "volume": "",
        "issue": "",
        "year": int(date[:4]),
        "date": date,
        "keywords": [],
        "tags": tags or ["系所公告"],
        "abstract": _strip_html(unescape(description))[:500],
        "url": link or "",
        "pdf": "",
        "doi": "",
        "source": source_name,
    }


def _text(element, tag):
    """取出 XML 子元素文字；tag 為空字串時讀取元素本身。"""
    target = element if not tag else element.find(tag)
    return (target.text or "").strip() if target is not None else ""


def _normalise_date(raw_date):
    """將 RSS 的日期轉成 YYYY-MM-DD；缺少日期時使用今天。"""
    if raw_date:
        try:
            return parsedate_to_datetime(raw_date).date().isoformat()
        except (TypeError, ValueError):
            try:
                return datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                pass
    return datetime.now().date().isoformat()


def _strip_html(text):
    """RSS 摘要常含 HTML；以最簡單的方式移除標記，保留可閱讀文字。"""
    output = []
    inside_tag = False
    for character in text:
        if character == "<":
            inside_tag = True
        elif character == ">":
            inside_tag = False
        elif not inside_tag:
            output.append(character)
    return " ".join("".join(output).split())
