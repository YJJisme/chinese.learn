"""三個爬蟲來源共用的 RSS 讀取與資料轉換工具。"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.parse import urlencode
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


def fetch_html_news(page_url, *, department, source_name, url_marker, limit=10):
    """從沒有 RSS 的官方公告頁擷取公告連結。

    只收集網址中有指定識別字的連結，避免將網站選單或聯絡資訊誤當新聞。
    公告頁未提供統一日期格式時，date 記錄本次擷取日期；來源網址仍用於去重。
    """
    request = Request(page_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except URLError as error:
        raise RuntimeError(f"無法讀取 {page_url}：{error.reason}") from error

    parser = _NewsLinkParser()
    parser.feed(html)
    today = datetime.now().date().isoformat()
    items = []
    seen_urls = set()
    for href, title in parser.links:
        absolute_url = urljoin(page_url, href)
        if url_marker not in absolute_url or absolute_url in seen_urls or len(title) < 8:
            continue
        seen_urls.add(absolute_url)
        items.append({
            "title": title,
            "authors": [],
            "type": "news",
            "department": department,
            "journal": "",
            "volume": "",
            "issue": "",
            "year": int(today[:4]),
            "date": today,
            "keywords": [],
            "tags": ["系所公告"],
            "abstract": "",
            "url": absolute_url,
            "pdf": "",
            "doi": "",
            "source": source_name,
        })
        if len(items) >= limit:
            break
    if not items:
        raise RuntimeError(f"{page_url} 沒有找到可辨識的公告連結。")
    return items


def fetch_crossref_works(query, *, department, limit=10):
    """從 Crossref 公開 API 取得學術論文書目。

    Crossref 提供 DOI、作者、期刊與出版日期等書目資料，不保證每筆都有全文。
    不傳送個人資料，也不需要帳號或 API 金鑰。
    """
    parameters = {
        "query.bibliographic": query,
        "filter": "type:journal-article",
        "sort": "published",
        "order": "desc",
        "rows": limit,
    }
    api_url = "https://api.crossref.org/works?" + urlencode(parameters)
    request = Request(api_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as error:
        raise RuntimeError(f"無法讀取 Crossref：{error.reason}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Crossref 回傳的內容不是有效 JSON。") from error

    works = payload.get("message", {}).get("items", [])
    if not works:
        raise RuntimeError(f"Crossref 沒有找到「{query}」的論文。")
    items = []
    for work in works:
        title = (work.get("title") or [""])[0].strip()
        if not title:
            continue
        date = _crossref_date(work)
        doi = work.get("DOI", "")
        authors = []
        for author in work.get("author", []):
            name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
            if name:
                authors.append(name)
        items.append({
            "title": title,
            "authors": authors,
            "type": "paper",
            "department": department,
            "journal": (work.get("container-title") or [""])[0],
            "volume": work.get("volume", ""),
            "issue": work.get("issue", ""),
            "year": int(date[:4]),
            "date": date,
            "keywords": [query],
            "tags": [query, "Crossref"],
            "abstract": _strip_html(work.get("abstract", ""))[:500],
            "url": work.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
            "pdf": "",
            "doi": doi,
            "source": "Crossref",
        })
    return items


class _NewsLinkParser(HTMLParser):
    """擷取 HTML 頁面中每個連結的可見文字與網址。"""

    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attributes):
        if tag == "a":
            self._href = dict(attributes).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            title = " ".join("".join(self._text).split())
            self.links.append((self._href, title))
            self._href = None
            self._text = []


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


def _crossref_date(work):
    """讀取 Crossref 最可靠的日期欄位，轉成 YYYY-MM-DD。"""
    for field in ("published", "published-online", "published-print", "issued", "created"):
        parts = work.get(field, {}).get("date-parts", [[]])[0]
        if parts:
            year = parts[0]
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            return f"{year:04d}-{month:02d}-{day:02d}"
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
