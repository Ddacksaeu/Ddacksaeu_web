from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 0. Configuration
# ============================================================
DATA_DIR = Path("./data")
DEPARTMENTS_PATH = DATA_DIR / "departments.csv"
LABS_PATH = DATA_DIR / "labs.csv"
OVERRIDES_PATH = DATA_DIR / "site_overrides.json"
BACKUP_DIR = DATA_DIR / "backups"
RAW_DIR = DATA_DIR / "raw_stage2"
LOG_PATH = DATA_DIR / "stage2_crawl_log.jsonl"

REQUEST_DELAY_SECONDS = 0.55
TIMEOUT_SECONDS = 30
MAX_DEPARTMENT_PAGES = 12
MAX_DEPTH = 2
CHECKPOINT_EVERY = 1
SAVE_RAW_HTML = False
RESPECT_ROBOTS = True

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 "
    "POSTECH-Lab-Hackathon-Stage2/0.2"
)

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I
)
PHONE_RE = re.compile(
    r"(?:\+?82[\s-]?)?(?:0?54)[\s-]?\d{3}[\s-]?\d{4}", re.I
)
ROOM_RE = re.compile(
    r"(?:[A-Za-z가-힣]+(?:관|동|센터|연구소|Building|Bldg\.?)[\s,]*)?"
    r"(?:[A-Za-z]?\d{1,4}(?:호|\s*(?:Room|Rm\.?))|"
    r"(?:Room|Rm\.?)\s*[A-Za-z]?\d{1,4})",
    re.I,
)

FACULTY_LINK_TERMS = (
    "faculty",
    "professor",
    "professors",
    "people",
    "member",
    "members",
    "staff",
    "교수",
    "교수진",
    "구성원",
    "연구진",
    "참여교수",
    "전임교수",
    "겸임교수",
    "연구실",
    "laboratory",
    "labs",
)

RESEARCH_LINK_TERMS = (
    "research",
    "research area",
    "research areas",
    "research field",
    "연구분야",
    "연구 분야",
    "연구영역",
    "연구실소개",
)

EXCLUDE_LINK_TERMS = (
    "notice",
    "news",
    "board",
    "seminar",
    "admission",
    "apply",
    "recruit",
    "gallery",
    "download",
    "login",
    "privacy",
    "공지",
    "소식",
    "행사",
    "세미나",
    "입학",
    "채용",
    "자료실",
)

FIELD_LABELS = (
    "연구분야",
    "연구 분야",
    "전문분야",
    "전문 분야",
    "연구영역",
    "연구 영역",
    "전공분야",
    "전공 분야",
    "전공",
    "research area",
    "research areas",
    "research field",
    "research fields",
    "research interest",
    "research interests",
    "specialty",
    "major",
)

LOCATION_LABELS = (
    "연구실",
    "사무실",
    "위치",
    "office",
    "location",
    "room",
)

HOMEPAGE_LABELS = (
    "homepage",
    "home page",
    "website",
    "web site",
    "lab",
    "laboratory",
    "연구실",
    "홈페이지",
)

CONTACT_STOP_LABELS = (
    "email",
    "e-mail",
    "메일",
    "전화",
    "phone",
    "tel",
    "fax",
    "office",
    "location",
    "연구실",
    "사무실",
    "학력",
    "education",
    "career",
    "경력",
)

SOCIAL_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "x.com",
    "twitter.com",
    "www.youtube.com",
    "youtube.com",
    "linkedin.com",
    "kr.linkedin.com",
    "github.com",
}

GENERIC_LINK_TEXTS = {
    "more",
    "view more",
    "detail",
    "자세히",
    "자세히보기",
    "바로가기",
    "홈페이지",
    "homepage",
    "website",
    "link",
    "web",
}

PLACEHOLDER_LAB_RE = re.compile(r"^.{2,20}\s*교수\s*연구실$")
LAB_NAME_RE = re.compile(
    r"(?:"
    r"[A-Za-z0-9&+,.()'’\-\s]{2,90}(?:Lab(?:oratory)?|Research Group|Group)"
    r"|[가-힣A-Za-z0-9&+,.()'’\-\s]{2,90}(?:연구실|연구그룹|연구센터)"
    r")",
    re.I,
)


# ============================================================
# 1. CSV schemas
# ============================================================
BASE_DEPARTMENT_FIELDS = [
    "department_id",
    "department_name_kor",
    "department_name_eng",
    "department_type",
    "location",
    "phone",
    "fax",
    "email",
    "homepage_url",
    "detail_url",
    "description",
    "core_fields",
    "research_centers",
    "source_url",
    "crawled_at",
]

STAGE2_DEPARTMENT_FIELDS = [
    "faculty_page_urls",
    "faculty_match_count",
    "enrichment_status",
    "enrichment_message",
    "enriched_at",
]

BASE_LAB_FIELDS = [
    "lab_id",
    "researcher_id",
    "department_id",
    "department_name",
    "department_name_raw",
    "department_match_status",
    "lab_name_kor",
    "lab_name_eng",
    "professor_name",
    "professor_title",
    "email",
    "phone",
    "location",
    "lab_url",
    "professor_profile_url",
    "profile_image_url",
    "research_summary",
    "keywords",
    "recruiting_status",
    "degree_options",
    "publication_count",
    "patent_count",
    "award_count",
    "crawl_status",
    "crawl_message",
    "source_url",
    "crawled_at",
]

STAGE2_LAB_FIELDS = [
    "department_type",
    "affiliated_programs",
    "primary_field",
    "department_page_url",
    "enrichment_source_urls",
    "enrichment_status",
    "enrichment_message",
    "data_quality_status",
    "enriched_at",
]


# ============================================================
# 2. Common utilities
# ============================================================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_multiline(value: object) -> str:
    if value is None:
        return ""
    lines = [clean_text(line) for line in str(value).splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_email(value: str) -> str:
    return clean_text(value).lower().replace("mailto:", "").split("?", 1)[0]


def normalize_name(value: str) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"(?:교수|부교수|조교수|professor|associate|assistant|ph\.?d\.?)", "", text)
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def normalize_url(url: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return parsed._replace(path=path).geturl()


def absolute_url(base_url: str, href: str) -> str:
    href = clean_text(href)
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""
    return normalize_url(urljoin(base_url, href))



def anchor_target_url(base_url: str, anchor: Tag) -> str:
    candidates = [
        clean_text(anchor.get("href", "")),
        clean_text(anchor.get("data-href", "")),
        clean_text(anchor.get("data-url", "")),
    ]
    onclick = clean_text(anchor.get("onclick", ""))
    if onclick:
        candidates.extend(
            match.group(1)
            for match in re.finditer(r"['\"]([^'\"]+)['\"]", onclick)
        )

    for raw in candidates:
        if not raw:
            continue
        if raw.startswith("javascript:"):
            quoted = re.search(r"['\"]([^'\"]+)['\"]", raw)
            raw = quoted.group(1) if quoted else ""
        url = absolute_url(base_url, raw)
        if url:
            return url
    return ""

def hostname(url: str) -> str:
    return urlparse(url).netloc.lower().split(":", 1)[0]


def root_host(host: str) -> str:
    parts = host.lower().split(".")
    if len(parts) >= 3 and parts[-2:] == ["ac", "kr"]:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def same_site(url_a: str, url_b: str) -> bool:
    host_a = hostname(url_a)
    host_b = hostname(url_b)
    return bool(host_a and host_b and root_host(host_a) == root_host(host_b))


def stable_id(prefix: str, *parts: str, length: int = 12) -> str:
    raw = "||".join(clean_text(part).lower() for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length].upper()
    return f"{prefix}_{digest}"


def split_multi(value: str) -> list[str]:
    return [clean_text(x) for x in re.split(r"[;|\n]+", clean_text(value)) if clean_text(x)]


def merge_multi(*values: object, limit: Optional[int] = None) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            items = [clean_text(x) for x in value]
        else:
            items = split_multi(str(value))
        for item in items:
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                merged.append(item)
                if limit is not None and len(merged) >= limit:
                    return ";".join(merged)
    return ";".join(merged)


def looks_placeholder_lab_name(value: str) -> bool:
    text = clean_text(value)
    return not text or bool(PLACEHOLDER_LAB_RE.fullmatch(text))


def is_probable_lab_name(value: str) -> bool:
    text = clean_text(value)
    if not (3 <= len(text) <= 120):
        return False
    lowered = text.lower()
    if lowered in GENERIC_LINK_TEXTS:
        return False
    if any(word in lowered for word in ("copyright", "privacy", "postech", "department of")) and not any(
        token in lowered for token in (" lab", "laboratory", "research group", "연구실")
    ):
        return False
    return bool(LAB_NAME_RE.search(text))


def strip_site_suffix(value: str) -> str:
    text = clean_text(value)
    chunks = re.split(r"\s*[|·–—]\s*|\s+-\s+", text)
    for chunk in chunks:
        if is_probable_lab_name(chunk):
            return clean_text(chunk)
    return text


def read_csv_rows(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV 파일이 없습니다: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def ensure_fields(existing: list[str], preferred: list[str]) -> list[str]:
    fields = list(existing)
    for field_name in preferred:
        if field_name not in fields:
            fields.append(field_name)
    return fields


def backup_file(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destination = BACKUP_DIR / f"{path.stem}_before_stage2_{timestamp_slug()}{path.suffix}"
    shutil.copy2(path, destination)
    return destination


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def classify_department_label(value: str) -> str:
    mapping = {
        "department": "학과",
        "division": "학부",
        "graduate_school": "대학원",
        "program": "전공",
    }
    return mapping.get(clean_text(value), clean_text(value) or "미분류")


def extract_yearless_sentences(text: str) -> list[str]:
    text = clean_text(text)
    chunks = re.split(r"(?<=[.!?。])\s+|\s*[•·]\s*", text)
    return [clean_text(chunk) for chunk in chunks if 20 <= len(clean_text(chunk)) <= 600]


# ============================================================
# 3. HTTP client + optional browser fallback
# ============================================================
@dataclass
class PageResult:
    url: str
    html: str
    method: str
    status_code: int = 200

    @property
    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(self.html, "lxml")


@dataclass
class RespectfulClient:
    delay_seconds: float = REQUEST_DELAY_SECONDS
    timeout_seconds: int = TIMEOUT_SECONDS
    browser_fallback: bool = False
    allow_insecure: bool = False
    respect_robots: bool = RESPECT_ROBOTS
    _robots: dict[str, RobotFileParser] = field(default_factory=dict)
    _cache: dict[str, PageResult] = field(default_factory=dict)

    def __post_init__(self) -> None:
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._last_request_at = 0.0

    def _sleep_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

    def _robots_allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots:
            parser = RobotFileParser()
            robots_url = f"{base}/robots.txt"
            parser.set_url(robots_url)
            try:
                self._sleep_if_needed()
                response = self.session.get(
                    robots_url,
                    timeout=min(self.timeout_seconds, 12),
                    verify=not self.allow_insecure,
                )
                self._last_request_at = time.monotonic()
                if response.ok:
                    parser.parse(response.text.splitlines())
                else:
                    parser.parse([])
            except requests.RequestException:
                parser.parse([])
            self._robots[base] = parser
        return self._robots[base].can_fetch(USER_AGENT, url)

    def _static_fetch(self, url: str) -> PageResult:
        if not self._robots_allowed(url):
            raise PermissionError(f"robots.txt가 접근을 허용하지 않습니다: {url}")
        self._sleep_if_needed()
        response = self.session.get(
            url,
            timeout=self.timeout_seconds,
            verify=not self.allow_insecure,
            allow_redirects=True,
        )
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type and "xml" not in content_type and content_type:
            raise ValueError(f"HTML이 아닌 응답입니다: {content_type}")
        if not response.encoding or response.encoding.lower() in {"ascii", "iso-8859-1"}:
            response.encoding = response.apparent_encoding or "utf-8"
        return PageResult(response.url, response.text, "requests", response.status_code)

    def _browser_fetch(self, url: str) -> PageResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright가 설치되지 않았습니다. "
                "pip install playwright 후 playwright install chromium을 실행하세요."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT, locale="ko-KR")
            page.goto(url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)
            html = page.content()
            final_url = page.url
            browser.close()
        return PageResult(final_url, html, "playwright", 200)

    @staticmethod
    def _needs_browser(html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")
        text = clean_text(soup.get_text(" ", strip=True))
        script_count = len(soup.find_all("script"))
        return len(text) < 250 and script_count >= 5

    def fetch(self, url: str, force_browser: bool = False) -> PageResult:
        url = normalize_url(url)
        if not url:
            raise ValueError("유효하지 않은 URL")
        cache_key = f"browser:{url}" if force_browser else f"auto:{url}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            result = self._static_fetch(url)
            if (force_browser or self._needs_browser(result.html)) and self.browser_fallback:
                result = self._browser_fetch(result.url)
        except PermissionError:
            raise
        except Exception:
            if not self.browser_fallback:
                raise
            result = self._browser_fetch(url)

        self._cache[cache_key] = result
        return result


# ============================================================
# 4. Site discovery
# ============================================================
def page_link_score(anchor_text: str, href: str) -> int:
    haystack = f"{clean_text(anchor_text).lower()} {href.lower()}"
    score = 0
    for term in FACULTY_LINK_TERMS:
        if term in haystack:
            score += 7
    for term in RESEARCH_LINK_TERMS:
        if term in haystack:
            score += 3
    for term in EXCLUDE_LINK_TERMS:
        if term in haystack:
            score -= 7
    if re.search(r"(?:faculty|professor|people|member|교수|구성원)", href, re.I):
        score += 5
    if href.lower().endswith((".pdf", ".zip", ".hwp", ".doc", ".docx", ".xls", ".xlsx")):
        score -= 100
    return score


def page_content_score(soup: BeautifulSoup) -> int:
    text = clean_text(soup.get_text(" ", strip=True)).lower()
    score = 0
    score += min(len(EMAIL_RE.findall(text)), 15) * 3
    score += sum(3 for term in FACULTY_LINK_TERMS if term in text)
    score += sum(1 for term in RESEARCH_LINK_TERMS if term in text)
    return score


def save_raw_html(department_id: str, page_index: int, result: PageResult) -> None:
    if not SAVE_RAW_HTML:
        return
    folder = RAW_DIR / department_id
    folder.mkdir(parents=True, exist_ok=True)
    host = re.sub(r"[^0-9A-Za-z._-]", "_", hostname(result.url))
    path = folder / f"{page_index:02d}_{host}_{stable_id('P', result.url, length=8)}.html"
    path.write_text(result.html, encoding="utf-8")


def load_overrides(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError("site_overrides.json 최상위 값은 객체여야 합니다.")
    return payload


def discover_department_pages(
    client: RespectfulClient,
    department: dict,
    override: dict,
    max_pages: int,
    max_depth: int,
) -> list[PageResult]:
    homepage = normalize_url(department.get("homepage_url", ""))
    forced_urls = [normalize_url(x) for x in override.get("faculty_urls", [])]
    forced_urls = [x for x in forced_urls if x]
    if not homepage and not forced_urls:
        return []

    queue: list[tuple[int, int, str]] = []
    visited: set[str] = set()
    queued: set[str] = set()
    results: list[PageResult] = []

    def push(url: str, score: int, depth: int) -> None:
        url = normalize_url(url)
        if not url or url in visited or url in queued:
            return
        queued.add(url)
        heapq.heappush(queue, (-score, depth, url))

    for url in forced_urls:
        push(url, 1000, 0)
    if homepage:
        push(homepage, 100, 0)

    primary_host = hostname(homepage or forced_urls[0])

    while queue and len(results) < max_pages:
        neg_score, depth, url = heapq.heappop(queue)
        queued.discard(url)
        if url in visited:
            continue
        visited.add(url)

        try:
            force_browser = url in set(forced_urls) and bool(override.get("render", False))
            result = client.fetch(url, force_browser=force_browser)
        except Exception as exc:
            append_jsonl(
                LOG_PATH,
                {
                    "timestamp": now_iso(),
                    "level": "warning",
                    "department_id": department.get("department_id", ""),
                    "department": department.get("department_name_kor", ""),
                    "url": url,
                    "message": str(exc),
                },
            )
            continue

        results.append(result)
        save_raw_html(department.get("department_id", "UNKNOWN"), len(results), result)

        soup = result.soup
        content_score = page_content_score(soup)
        print(
            f"    [PAGE] {len(results):02d}/{max_pages:02d} | "
            f"내용점수={content_score:02d} | {result.method} | {result.url}"
        )

        if depth >= max_depth:
            continue

        for anchor in soup.find_all("a", href=True):
            href = anchor_target_url(result.url, anchor)
            if not href:
                continue
            host = hostname(href)
            if not host or root_host(host) != root_host(primary_host):
                continue
            score = page_link_score(anchor.get_text(" ", strip=True), href)
            if score < 3:
                continue
            push(href, score, depth + 1)

    return results


# ============================================================
# 5. Faculty-card extraction
# ============================================================
def node_lines(node: Tag) -> list[str]:
    return [clean_text(x) for x in node.stripped_strings if clean_text(x)]


def email_count(node: Tag) -> int:
    return len(set(normalize_email(x) for x in EMAIL_RE.findall(node.get_text(" ", strip=True))))


def find_person_container(node: Tag, person_name: str, email: str) -> Tag:
    current: Optional[Tag] = node if isinstance(node, Tag) else node.parent
    best: Optional[Tag] = None
    normalized_person = normalize_name(person_name)

    for _ in range(10):
        if not isinstance(current, Tag):
            break
        text = clean_text(current.get_text(" ", strip=True))
        if len(text) > 8000:
            break
        emails = email_count(current)
        has_identity = (
            normalize_email(email) in {normalize_email(x) for x in EMAIL_RE.findall(text)}
            or normalized_person in normalize_name(text)
        )
        if has_identity and emails <= 4 and 30 <= len(text) <= 5000:
            best = current
            if current.name in {"li", "tr", "article", "section"}:
                break
        current = current.parent

    if best is not None:
        return best
    return node if isinstance(node, Tag) else node.parent


def find_email_nodes(soup: BeautifulSoup) -> dict[str, Tag]:
    found: dict[str, Tag] = {}
    for anchor in soup.find_all("a", href=True):
        href = clean_text(anchor.get("href", ""))
        if href.lower().startswith("mailto:"):
            email = normalize_email(href)
            if EMAIL_RE.fullmatch(email):
                found[email] = anchor

    for text_node in soup.find_all(string=EMAIL_RE):
        if not isinstance(text_node, NavigableString):
            continue
        for email in EMAIL_RE.findall(str(text_node)):
            normalized = normalize_email(email)
            if normalized not in found and isinstance(text_node.parent, Tag):
                found[normalized] = text_node.parent
    return found


def find_name_node(soup: BeautifulSoup, name: str) -> Optional[Tag]:
    if not name:
        return None
    pattern = re.compile(rf"(?<![가-힣A-Za-z]){re.escape(name)}(?:\s*교수)?(?![가-힣A-Za-z])")
    for text_node in soup.find_all(string=pattern):
        if isinstance(text_node, NavigableString) and isinstance(text_node.parent, Tag):
            return text_node.parent
    return None


def extract_labeled_text(lines: list[str], labels: tuple[str, ...], max_following: int = 3) -> str:
    ordered_labels = sorted(
        (re.sub(r"\s+", " ", label).strip() for label in labels),
        key=len,
        reverse=True,
    )
    for index, line in enumerate(lines):
        normalized_line = re.sub(r"\s+", " ", line).strip()
        for label in ordered_labels:
            if normalized_line.lower() == label.lower() and index + 1 < len(lines):
                values: list[str] = []
                for follow in lines[index + 1 : index + 1 + max_following]:
                    follow_low = follow.lower()
                    if any(follow_low.startswith(stop) for stop in CONTACT_STOP_LABELS):
                        break
                    if EMAIL_RE.search(follow) or PHONE_RE.search(follow):
                        break
                    if 2 <= len(follow) <= 500:
                        values.append(follow)
                return "; ".join(values)

            pattern = re.compile(
                rf"^\s*{re.escape(label)}\s*[:：-]?\s*(?P<value>.+?)\s*$",
                re.I,
            )
            match = pattern.match(normalized_line)
            if match:
                return clean_text(match.group("value"))
    return ""


def extract_location(lines: list[str]) -> str:
    labeled = extract_labeled_text(lines, LOCATION_LABELS, max_following=1)
    if labeled and not EMAIL_RE.search(labeled) and len(labeled) <= 160:
        return labeled
    for line in lines:
        match = ROOM_RE.search(line)
        if match and len(line) <= 180:
            return clean_text(line)
    return ""


def candidate_lab_name_from_lines(lines: list[str], professor_name: str) -> str:
    candidates: list[str] = []
    for line in lines:
        if professor_name and normalize_name(line) == normalize_name(professor_name):
            continue
        for match in LAB_NAME_RE.finditer(line):
            candidate = clean_text(match.group(0))
            if is_probable_lab_name(candidate):
                candidates.append(candidate)
    candidates.sort(key=lambda x: ("lab" not in x.lower() and "연구실" not in x, len(x)))
    return candidates[0] if candidates else ""


def anchor_url_score(anchor: Tag, page_url: str, professor_name: str) -> int:
    href = anchor_target_url(page_url, anchor)
    if not href:
        return -999
    host = hostname(href)
    if host in SOCIAL_HOSTS or root_host(host) in SOCIAL_HOSTS:
        return -999
    text = clean_text(anchor.get_text(" ", strip=True)).lower()
    haystack = f"{text} {href.lower()}"
    score = 0
    if any(label in haystack for label in HOMEPAGE_LABELS):
        score += 10
    if any(token in haystack for token in ("lab", "laboratory", "research-group", "research_group", "연구실")):
        score += 8
    if not same_site(href, page_url):
        score += 5
    if professor_name and normalize_name(professor_name) in normalize_name(text):
        score += 2
    if any(token in haystack for token in ("publication", "paper", "doi.org", "scholar", "orcid", "profile", "researcher-search")):
        score -= 8
    if href.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".gif")):
        score -= 20
    return score


def extract_lab_url(block: Tag, page_url: str, professor_name: str) -> str:
    candidates: list[tuple[int, str]] = []
    for anchor in block.find_all("a", href=True):
        href = anchor_target_url(page_url, anchor)
        score = anchor_url_score(anchor, page_url, professor_name)
        if score > 0 and href:
            candidates.append((score, href))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: (-x[0], len(x[1])))
    return candidates[0][1]


def extract_image_url(block: Tag, page_url: str, professor_name: str) -> str:
    images = block.find_all("img", src=True)
    if not images:
        return ""
    scored: list[tuple[int, str]] = []
    for image in images:
        src = absolute_url(page_url, image.get("src", ""))
        if not src:
            continue
        alt = clean_text(image.get("alt", ""))
        score = 1
        if professor_name and professor_name in alt:
            score += 5
        if any(token in src.lower() for token in ("prof", "faculty", "member", "people")):
            score += 2
        scored.append((score, src))
    scored.sort(reverse=True)
    return scored[0][1] if scored else ""


def extract_primary_field(lines: list[str]) -> str:
    value = extract_labeled_text(lines, FIELD_LABELS, max_following=3)
    value = re.sub(r"^(?:분야|area|field)\s*[:：-]?\s*", "", value, flags=re.I)
    return clean_text(value)[:600]


def keyword_phrases(*texts: str, limit: int = 12) -> str:
    phrases: list[str] = []
    seen: set[str] = set()
    stop = {
        "research",
        "research area",
        "research fields",
        "연구",
        "연구분야",
        "교수",
        "professor",
        "postech",
    }
    for text in texts:
        if not text:
            continue
        chunks = re.split(r"[;,/|•·\n]+|\s{2,}", text)
        if len(chunks) == 1 and 5 <= len(text) <= 100:
            chunks = [text]
        for chunk in chunks:
            phrase = clean_text(re.sub(r"^[#\-–—:：]+|[#\-–—:：]+$", "", chunk))
            phrase = re.sub(
                r"^(?:research(?: areas?| fields?| interests?)?|연구\s*(?:분야|영역)?|전문\s*분야|전공\s*분야)\s*[:：-]?\s*",
                "",
                phrase,
                flags=re.I,
            )
            if not (2 <= len(phrase) <= 90):
                continue
            key = phrase.lower()
            if key in stop or key in seen or EMAIL_RE.search(phrase) or PHONE_RE.search(phrase):
                continue
            seen.add(key)
            phrases.append(phrase)
            if len(phrases) >= limit:
                return ";".join(phrases)
    return ";".join(phrases)


def extract_card_data(block: Tag, page_url: str, lab: dict) -> dict:
    lines = node_lines(block)
    primary_field = extract_primary_field(lines)
    lab_name = candidate_lab_name_from_lines(lines, lab.get("professor_name", ""))
    lab_url = extract_lab_url(block, page_url, lab.get("professor_name", ""))
    location = extract_location(lines)
    phone_match = PHONE_RE.search(" ".join(lines))
    phone = clean_text(phone_match.group(0)) if phone_match else ""
    image_url = extract_image_url(block, page_url, lab.get("professor_name", ""))

    summary = ""
    for line in lines:
        low = line.lower()
        if 30 <= len(line) <= 500 and any(
            token in low
            for token in (
                "연구",
                "focus",
                "research",
                "develop",
                "investigate",
                "study",
            )
        ):
            if not EMAIL_RE.search(line) and not PHONE_RE.search(line):
                summary = line
                break
    if not summary and primary_field:
        summary = f"주요 연구 분야: {primary_field}"

    return {
        "lab_name_kor": lab_name,
        "lab_url": lab_url,
        "location": location,
        "phone": phone,
        "profile_image_url": image_url,
        "primary_field": primary_field,
        "research_summary": summary,
        "keywords": keyword_phrases(primary_field),
        "department_page_url": page_url,
        "enrichment_source_urls": page_url,
    }


def page_matches(
    result: PageResult,
    labs_by_email: dict[str, dict],
    labs_by_name: dict[str, list[dict]],
) -> list[tuple[dict, Tag, str]]:
    soup = result.soup
    matches: dict[str, tuple[dict, Tag, str]] = {}
    email_nodes = find_email_nodes(soup)

    for email, node in email_nodes.items():
        lab = labs_by_email.get(email)
        if lab is None:
            continue
        block = find_person_container(node, lab.get("professor_name", ""), email)
        matches[lab["lab_id"]] = (lab, block, "email")

    page_text = clean_text(soup.get_text(" ", strip=True))
    for normalized_name, candidate_labs in labs_by_name.items():
        if not normalized_name:
            continue
        for lab in candidate_labs:
            if lab["lab_id"] in matches:
                continue
            name = clean_text(lab.get("professor_name", ""))
            if not name or name not in page_text:
                continue
            node = find_name_node(soup, name)
            if node is None:
                continue
            block = find_person_container(node, name, lab.get("email", ""))
            block_text = clean_text(block.get_text(" ", strip=True)).lower()
            identity_context = any(
                token in block_text
                for token in ("교수", "professor", "research", "연구", "faculty", "전문 분야")
            )
            if not identity_context:
                continue
            matches[lab["lab_id"]] = (lab, block, "name")

    return list(matches.values())


# ============================================================
# 6. Lab-homepage enrichment
# ============================================================
def meta_content(soup: BeautifulSoup, names: tuple[str, ...]) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"name": re.compile(rf"^{re.escape(name)}$", re.I)})
        if tag and tag.get("content"):
            return clean_text(tag.get("content"))
        tag = soup.find("meta", attrs={"property": re.compile(rf"^{re.escape(name)}$", re.I)})
        if tag and tag.get("content"):
            return clean_text(tag.get("content"))
    return ""


def extract_homepage_lab_name(soup: BeautifulSoup) -> str:
    candidates: list[str] = []
    for selector in ("h1", "header h2", ".site-title", ".logo", "title"):
        for node in soup.select(selector):
            text = strip_site_suffix(node.get_text(" ", strip=True))
            if is_probable_lab_name(text):
                candidates.append(text)
    candidates.sort(key=len)
    return candidates[0] if candidates else ""


def extract_homepage_summary(soup: BeautifulSoup) -> str:
    description = meta_content(soup, ("description", "og:description", "twitter:description"))
    if 30 <= len(description) <= 700:
        low = description.lower()
        if any(token in low for token in ("research", "연구", "laboratory", "lab", "science", "engineering")):
            return description

    selectors = (
        "main p",
        "article p",
        ".about p",
        ".research p",
        "#about p",
        "#research p",
    )
    candidates: list[str] = []
    for selector in selectors:
        for paragraph in soup.select(selector):
            text = clean_text(paragraph.get_text(" ", strip=True))
            low = text.lower()
            if 40 <= len(text) <= 700 and any(
                token in low
                for token in ("research", "연구", "develop", "focus", "investigate", "study")
            ):
                candidates.append(text)
    candidates.sort(key=lambda x: (len(x) > 450, -len(x)))
    return candidates[0] if candidates else ""


def detect_recruiting_status(text: str) -> str:
    low = clean_text(text).lower()
    negative_patterns = (
        "not recruiting",
        "no open position",
        "currently closed",
        "현재 모집하지",
        "모집 마감",
    )
    positive_patterns = (
        "we are recruiting",
        "open position",
        "open positions",
        "join us",
        "prospective students",
        "대학원생 모집",
        "연구원 모집",
        "학생 모집",
        "지원 바랍니다",
    )
    if any(pattern in low for pattern in negative_patterns):
        return "closed"
    if any(pattern in low for pattern in positive_patterns):
        return "open"
    return "unknown"


def enrich_from_lab_homepage(client: RespectfulClient, lab: dict) -> dict:
    lab_url = normalize_url(lab.get("lab_url", ""))
    if not lab_url:
        return {}
    result = client.fetch(lab_url)
    soup = result.soup
    page_text = clean_text(soup.get_text(" ", strip=True))

    name = extract_homepage_lab_name(soup)
    summary = extract_homepage_summary(soup)
    meta_keywords = meta_content(soup, ("keywords",))
    location = ""
    lines = [clean_text(x) for x in soup.stripped_strings if clean_text(x)]
    location = extract_location(lines)

    return {
        "lab_name_kor": name,
        "research_summary": summary,
        "keywords": keyword_phrases(
            lab.get("primary_field", ""),
            meta_keywords,
            summary,
            limit=12,
        ),
        "location": location,
        "recruiting_status": detect_recruiting_status(page_text),
        "enrichment_source_urls": result.url,
    }


# ============================================================
# 7. Merge and quality rules
# ============================================================
def text_quality(field_name: str, value: str) -> int:
    text = clean_text(value)
    if not text:
        return 0
    if field_name == "lab_name_kor":
        if looks_placeholder_lab_name(text):
            return 1
        return 10 if is_probable_lab_name(text) else 4
    if field_name == "lab_url":
        return 8 if normalize_url(text) else 0
    if field_name == "primary_field":
        return 7 if 3 <= len(text) <= 600 else 2
    if field_name == "research_summary":
        return min(8, 2 + len(text) // 80)
    if field_name == "keywords":
        return min(8, len(split_multi(text)))
    if field_name == "location":
        return 5 if ROOM_RE.search(text) else 2
    if field_name == "profile_image_url":
        return 3 if normalize_url(text) else 0
    if field_name == "phone":
        return 3 if PHONE_RE.search(text) else 1
    if field_name == "recruiting_status":
        return 3 if text in {"open", "closed", "always_open"} else 1
    return 1


def merge_lab_update(lab: dict, update: dict, affiliation: str) -> tuple[dict, list[str]]:
    changed: list[str] = []
    merged = dict(lab)

    if affiliation:
        old = merged.get("affiliated_programs", "") or merged.get("department_name", "")
        new_value = merge_multi(old, affiliation)
        if new_value != clean_text(merged.get("affiliated_programs", "")):
            merged["affiliated_programs"] = new_value
            changed.append("affiliated_programs")

    merge_fields = (
        "lab_name_kor",
        "lab_name_eng",
        "lab_url",
        "location",
        "phone",
        "profile_image_url",
        "primary_field",
        "research_summary",
        "keywords",
        "recruiting_status",
        "department_page_url",
    )

    for field_name in merge_fields:
        incoming = clean_text(update.get(field_name, ""))
        if not incoming:
            continue
        current = clean_text(merged.get(field_name, ""))
        if text_quality(field_name, incoming) > text_quality(field_name, current):
            merged[field_name] = incoming
            changed.append(field_name)
        elif field_name == "keywords" and incoming:
            combined = merge_multi(current, incoming, limit=12)
            if combined != current:
                merged[field_name] = combined
                changed.append(field_name)

    source_urls = merge_multi(
        merged.get("enrichment_source_urls", ""),
        update.get("enrichment_source_urls", ""),
        update.get("department_page_url", ""),
    )
    if source_urls != clean_text(merged.get("enrichment_source_urls", "")):
        merged["enrichment_source_urls"] = source_urls
        changed.append("enrichment_source_urls")

    return merged, list(dict.fromkeys(changed))


def data_quality_status(lab: dict) -> str:
    actual_name = not looks_placeholder_lab_name(lab.get("lab_name_kor", ""))
    has_url = bool(normalize_url(lab.get("lab_url", "")))
    has_research = bool(clean_text(lab.get("primary_field", "")) or clean_text(lab.get("research_summary", "")))
    has_keywords = len(split_multi(lab.get("keywords", ""))) >= 2
    score = sum((actual_name, has_url, has_research, has_keywords))
    if score >= 4:
        return "complete"
    if score >= 2:
        return "partial"
    return "basic_only"


def apply_manual_overrides(labs_by_id: dict[str, dict], override_root: dict) -> int:
    changed_count = 0
    for department_override in override_root.values():
        if not isinstance(department_override, dict):
            continue
        lab_overrides = department_override.get("lab_overrides", {})
        if not isinstance(lab_overrides, dict):
            continue
        for key, values in lab_overrides.items():
            if not isinstance(values, dict):
                continue
            normalized_key = normalize_email(key)
            target = next(
                (
                    lab
                    for lab in labs_by_id.values()
                    if normalize_email(lab.get("email", "")) == normalized_key
                    or lab.get("lab_id") == key
                ),
                None,
            )
            if target is None:
                continue
            merged, changed = merge_lab_update(
                target,
                {**values, "enrichment_source_urls": "manual_override"},
                values.get("affiliated_programs", ""),
            )
            if changed:
                merged["enrichment_status"] = "manual_override"
                merged["enrichment_message"] = "수동 override 적용: " + ", ".join(changed)
                merged["enriched_at"] = now_iso()
                merged["data_quality_status"] = data_quality_status(merged)
                labs_by_id[target["lab_id"]] = merged
                changed_count += 1
    return changed_count


# ============================================================
# 8. Checkpointing
# ============================================================
def save_checkpoint(
    departments: list[dict],
    labs_by_id: dict[str, dict],
    department_fields: list[str],
    lab_fields: list[str],
    dry_run: bool,
) -> None:
    if dry_run:
        return
    departments_sorted = sorted(
        departments,
        key=lambda row: (row.get("department_type", ""), row.get("department_name_kor", "")),
    )
    labs_sorted = sorted(
        labs_by_id.values(),
        key=lambda row: (row.get("department_name", ""), row.get("professor_name", "")),
    )
    write_csv(DEPARTMENTS_PATH, departments_sorted, department_fields)
    write_csv(LABS_PATH, labs_sorted, lab_fields)


# ============================================================
# 9. Main stage-2 pipeline
# ============================================================
def run_stage2(args: argparse.Namespace) -> None:
    global SAVE_RAW_HTML
    SAVE_RAW_HTML = args.save_raw_html

    departments, department_existing_fields = read_csv_rows(DEPARTMENTS_PATH)
    labs, lab_existing_fields = read_csv_rows(LABS_PATH)
    department_fields = ensure_fields(
        department_existing_fields or BASE_DEPARTMENT_FIELDS,
        STAGE2_DEPARTMENT_FIELDS,
    )
    lab_fields = ensure_fields(
        lab_existing_fields or BASE_LAB_FIELDS,
        STAGE2_LAB_FIELDS,
    )

    if not args.dry_run:
        backup_labs = backup_file(LABS_PATH)
        backup_departments = backup_file(DEPARTMENTS_PATH)
        print(f"[BACKUP] labs.csv        → {backup_labs}")
        print(f"[BACKUP] departments.csv → {backup_departments}")

    overrides = load_overrides(Path(args.overrides))
    labs_by_id = {row["lab_id"]: row for row in labs if clean_text(row.get("lab_id", ""))}
    department_by_id = {
        clean_text(row.get("department_id", "")): row
        for row in departments
        if clean_text(row.get("department_id", ""))
    }
    labs_by_email = {
        normalize_email(row.get("email", "")): row
        for row in labs_by_id.values()
        if normalize_email(row.get("email", ""))
    }
    labs_by_name: dict[str, list[dict]] = {}
    for row in labs_by_id.values():
        labs_by_name.setdefault(normalize_name(row.get("professor_name", "")), []).append(row)
        primary_department = department_by_id.get(clean_text(row.get("department_id", "")), {})
        if not clean_text(row.get("department_type", "")):
            row["department_type"] = clean_text(primary_department.get("department_type", ""))
        row.setdefault("affiliated_programs", row.get("department_name", ""))
        row.setdefault("primary_field", "")
        row.setdefault("department_page_url", "")
        row.setdefault("enrichment_source_urls", "")
        row.setdefault("enrichment_status", "pending")
        row.setdefault("enrichment_message", "")
        row.setdefault("data_quality_status", data_quality_status(row))
        row.setdefault("enriched_at", "")

    client = RespectfulClient(
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        browser_fallback=args.browser_fallback,
        allow_insecure=args.allow_insecure,
        respect_robots=not args.ignore_robots,
    )

    selected_departments = departments
    if args.department:
        needle = args.department.lower()
        selected_departments = [
            row
            for row in selected_departments
            if needle in clean_text(row.get("department_name_kor", "")).lower()
            or needle == clean_text(row.get("department_id", "")).lower()
        ]
    if args.test_limit is not None:
        selected_departments = selected_departments[: args.test_limit]

    print("=" * 96)
    print("POSTECH LAB DATABASE — STAGE 2 ENRICHER")
    print("=" * 96)
    print(f"대학원/학과/학부/전공: {len(selected_departments)}개")
    print(f"기존 연구실 레코드    : {len(labs_by_id)}개")
    print(f"페이지 상한           : 학과당 {args.max_pages}개, 깊이 {args.max_depth}")
    print(f"브라우저 fallback     : {args.browser_fallback}")
    print(f"robots.txt 준수       : {not args.ignore_robots}")
    print()

    run_started_at = now_iso()
    touched_lab_ids: set[str] = set()

    for department_index, department in enumerate(selected_departments, start=1):
        department_id = clean_text(department.get("department_id", ""))
        department_name = clean_text(department.get("department_name_kor", ""))
        department_type = clean_text(department.get("department_type", ""))
        type_label = classify_department_label(department_type)
        homepage = clean_text(department.get("homepage_url", ""))

        if (
            not args.force
            and clean_text(department.get("enrichment_status", "")) == "success"
        ):
            print(
                f"[SKIP-DEPT] {department_index:02d}/{len(selected_departments):02d} | "
                f"구분={type_label} | 학부/학과={department_name} | 이전 성공"
            )
            continue

        print()
        print("-" * 96)
        print(
            f"[DEPT] {department_index:02d}/{len(selected_departments):02d} | "
            f"구분={type_label} | 학부/학과={department_name} | {homepage or 'URL 없음'}"
        )

        override = overrides.get(department_id, {})
        try:
            pages = discover_department_pages(
                client,
                department,
                override if isinstance(override, dict) else {},
                max_pages=args.max_pages,
                max_depth=args.max_depth,
            )
        except Exception as exc:
            department["enrichment_status"] = "failed"
            department["enrichment_message"] = str(exc)
            department["enriched_at"] = now_iso()
            print(f"[FAIL-DEPT] {department_name} | {exc}")
            save_checkpoint(
                departments,
                labs_by_id,
                department_fields,
                lab_fields,
                args.dry_run,
            )
            continue

        department_match_ids: set[str] = set()
        faculty_pages: set[str] = set()
        field_update_counts: dict[str, int] = {}

        for result in pages:
            matches = page_matches(result, labs_by_email, labs_by_name)
            if not matches:
                continue
            faculty_pages.add(result.url)

            for original_lab, block, match_method in matches:
                current = labs_by_id[original_lab["lab_id"]]
                update = extract_card_data(block, result.url, current)
                merged, changed_fields = merge_lab_update(current, update, department_name)
                merged["enriched_at"] = now_iso()

                if changed_fields:
                    merged["enrichment_status"] = "success"
                    merged["enrichment_message"] = (
                        f"{department_name} 페이지에서 {match_method} 매칭; "
                        f"갱신: {', '.join(changed_fields)}"
                    )
                    touched_lab_ids.add(merged["lab_id"])
                    for field_name in changed_fields:
                        field_update_counts[field_name] = field_update_counts.get(field_name, 0) + 1
                elif merged.get("enrichment_status") in {"", "pending"}:
                    merged["enrichment_status"] = "matched_no_change"
                    merged["enrichment_message"] = f"{department_name}에서 {match_method} 매칭되었으나 새 필드 없음"

                merged["data_quality_status"] = data_quality_status(merged)
                labs_by_id[merged["lab_id"]] = merged
                department_match_ids.add(merged["lab_id"])

                display_lab_name = clean_text(merged.get("lab_name_kor", ""))
                display_field = clean_text(merged.get("primary_field", ""))
                print(
                    f"    [MATCH] 구분={type_label} | 학부/학과={department_name} | "
                    f"랩={display_lab_name or '-'} | 교수={merged.get('professor_name', '-')} | "
                    f"방식={match_method} | 분야={display_field[:70] or '-'}"
                )

        # 발견된 랩 홈페이지를 한 번만 열어 연구실명/설명/키워드를 보완한다.
        if not args.skip_lab_homepages:
            for lab_id in sorted(department_match_ids):
                lab = labs_by_id[lab_id]
                if not normalize_url(lab.get("lab_url", "")):
                    continue
                if (
                    not args.force
                    and not looks_placeholder_lab_name(lab.get("lab_name_kor", ""))
                    and clean_text(lab.get("research_summary", ""))
                    and len(split_multi(lab.get("keywords", ""))) >= 2
                ):
                    continue
                try:
                    homepage_update = enrich_from_lab_homepage(client, lab)
                except Exception as exc:
                    lab["enrichment_message"] = merge_multi(
                        lab.get("enrichment_message", ""),
                        f"랩 홈페이지 보완 실패: {exc}",
                    )
                    continue
                merged, changed = merge_lab_update(lab, homepage_update, department_name)
                if changed:
                    merged["enrichment_status"] = "success"
                    merged["enrichment_message"] = merge_multi(
                        merged.get("enrichment_message", ""),
                        "랩 홈페이지 보완: " + ", ".join(changed),
                    )
                    merged["enriched_at"] = now_iso()
                    merged["data_quality_status"] = data_quality_status(merged)
                    labs_by_id[lab_id] = merged
                    touched_lab_ids.add(lab_id)
                    for field_name in changed:
                        field_update_counts[field_name] = field_update_counts.get(field_name, 0) + 1
                    print(
                        f"    [LAB] 학부/학과={department_name} | "
                        f"랩={merged.get('lab_name_kor', '-')} | 교수={merged.get('professor_name', '-')} | "
                        f"홈페이지 보완={', '.join(changed)}"
                    )

        department["faculty_page_urls"] = merge_multi(sorted(faculty_pages))
        department["faculty_match_count"] = str(len(department_match_ids))
        department["enriched_at"] = now_iso()
        if department_match_ids:
            department["enrichment_status"] = "success"
            summary = ", ".join(f"{key}={value}" for key, value in sorted(field_update_counts.items()))
            department["enrichment_message"] = (
                f"교수/랩 {len(department_match_ids)}명 매칭"
                + (f"; {summary}" if summary else "")
            )
        else:
            department["enrichment_status"] = "no_match"
            department["enrichment_message"] = "교수/랩 카드 또는 기존 교수와의 매칭을 찾지 못함"

        print(
            f"[DONE-DEPT] 구분={type_label} | 학부/학과={department_name} | "
            f"매칭={len(department_match_ids)} | 교수페이지={len(faculty_pages)}"
        )

        if department_index % CHECKPOINT_EVERY == 0:
            save_checkpoint(
                departments,
                labs_by_id,
                department_fields,
                lab_fields,
                args.dry_run,
            )

    manual_count = apply_manual_overrides(labs_by_id, overrides)
    if manual_count:
        print(f"[OVERRIDE] 수동 보정 적용: {manual_count}개 연구실")

    # 건드리지 못한 레코드의 상태와 품질도 명시한다.
    for lab in labs_by_id.values():
        if lab.get("enrichment_status") in {"", "pending"}:
            lab["enrichment_status"] = "no_match"
            lab["enrichment_message"] = "2차 크롤러에서 매칭되지 않음"
        lab["data_quality_status"] = data_quality_status(lab)
        if not lab.get("affiliated_programs"):
            lab["affiliated_programs"] = lab.get("department_name", "")

    save_checkpoint(
        departments,
        labs_by_id,
        department_fields,
        lab_fields,
        args.dry_run,
    )

    quality_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for lab in labs_by_id.values():
        quality = clean_text(lab.get("data_quality_status", "")) or "unknown"
        status = clean_text(lab.get("enrichment_status", "")) or "unknown"
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    append_jsonl(
        LOG_PATH,
        {
            "timestamp": now_iso(),
            "level": "summary",
            "run_started_at": run_started_at,
            "departments_processed": len(selected_departments),
            "labs_total": len(labs_by_id),
            "labs_touched": len(touched_lab_ids),
            "manual_overrides": manual_count,
            "quality_counts": quality_counts,
            "status_counts": status_counts,
            "dry_run": args.dry_run,
        },
    )

    print()
    print("=" * 96)
    print("STAGE 2 COMPLETE")
    print("=" * 96)
    print(f"갱신된 연구실 수: {len(touched_lab_ids)}")
    print(f"수동 보정 수    : {manual_count}")
    print(f"품질 상태       : {quality_counts}")
    print(f"수집 상태       : {status_counts}")
    if args.dry_run:
        print("DRY RUN이므로 CSV에는 기록하지 않았습니다.")
    else:
        print(f"저장: {LABS_PATH}")
        print(f"저장: {DEPARTMENTS_PATH}")
        print(f"로그: {LOG_PATH}")


# ============================================================
# 10. CLI
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "POSTECH 2차 크롤러: 학과/대학원 홈페이지에서 기존 labs.csv를 "
            "실제 연구실명, 연구분야, URL, 위치, 키워드, 소속 프로그램으로 보완합니다."
        )
    )
    parser.add_argument("--department", help="특정 학과명 또는 department_id만 실행")
    parser.add_argument("--test-limit", type=int, help="앞에서 N개 학과만 테스트")
    parser.add_argument("--max-pages", type=int, default=MAX_DEPARTMENT_PAGES)
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH)
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SECONDS)
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SECONDS)
    parser.add_argument("--force", action="store_true", help="이전 성공 상태도 다시 수집")
    parser.add_argument("--dry-run", action="store_true", help="CSV를 수정하지 않고 로그만 출력")
    parser.add_argument("--skip-lab-homepages", action="store_true", help="개별 랩 홈페이지 보완 생략")
    parser.add_argument("--browser-fallback", action="store_true", help="정적 HTML 부족 시 Playwright 사용")
    parser.add_argument("--allow-insecure", action="store_true", help="SSL 인증서 검증 실패 사이트 허용")
    parser.add_argument("--ignore-robots", action="store_true", help="robots.txt 검사 생략")
    parser.add_argument("--save-raw-html", action="store_true", help="수집 HTML을 data/raw_stage2에 저장")
    parser.add_argument(
        "--overrides",
        default=str(OVERRIDES_PATH),
        help="사이트별 보정 JSON 경로",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.max_pages < 1:
        parser.error("--max-pages는 1 이상이어야 합니다.")
    if args.max_depth < 0:
        parser.error("--max-depth는 0 이상이어야 합니다.")
    run_stage2(args)


if __name__ == "__main__":
    main()
