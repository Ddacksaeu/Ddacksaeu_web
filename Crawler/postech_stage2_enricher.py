from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import os
import re
import shutil
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence
from urllib.parse import parse_qs, urldefrag, urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 0. Version and defaults
# ============================================================
ENRICHER_VERSION = "0.7.1-data-audit"

DEFAULT_DATA_DIR = Path("./data")
DEFAULT_REQUEST_DELAY_SECONDS = 0.55
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_DEPARTMENT_PAGES = 12
DEFAULT_MAX_DEPTH = 2
DEFAULT_CHECKPOINT_EVERY = 1
DEFAULT_RESPECT_ROBOTS = True
MAX_SUMMARY_CHARS = 1200
MAX_PRIMARY_FIELD_CHARS = 600
MAX_KEYWORDS = 12
MAX_ENRICHMENT_SOURCE_URLS = 8

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 "
    f"POSTECH-Lab-Hackathon-Stage2/{ENRICHER_VERSION}"
)


# ============================================================
# 1. Patterns and vocabularies
# ============================================================
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)

# POSTECH commonly uses 279-XXXX internally, and some pages expose full numbers.
PHONE_RE = re.compile(
    r"(?:"
    r"(?:\+?82[\s().-]*)?(?:0?54)[\s().-]*279[\s().-]*\d{4}"
    r"|(?<!\d)279[\s.-]*\d{4}(?!\d)"
    r")",
    re.I,
)

ROOM_RE = re.compile(
    r"(?:"
    r"(?:[A-Za-z가-힣0-9]+(?:관|동|센터|연구소|Building|Bldg\.?|Center))[\s,/-]*"
    r"(?:[A-Za-z]?\d{1,4}(?:호)?|(?:Room|Rm\.?)\s*[A-Za-z]?\d{1,4})"
    r"|(?:Room|Rm\.?)\s*[A-Za-z]?\d{1,4}"
    r"|(?<![A-Za-z0-9])[A-Za-z]\d{1,2}[\s-]+\d{2,4}호?(?!\d)"
    r"|(?<!\d)[A-Za-z]?\d{3,4}호(?!\d)"
    r")",
    re.I,
)

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
URL_RE = re.compile(r"(?i)(?:https?://|www\.)[^\s;|,<>\]\[()]+")
BARE_DOMAIN_RE = re.compile(
    r"(?i)(?<![@A-Za-z0-9_-])(?:[A-Za-z0-9-]+\.)+(?:ac\.kr|co\.kr|go\.kr|or\.kr|com|org|net|edu|io|ai|kr)(?:/[^\s;|,<>]*)?"
)
KOREAN_NAME_RE = re.compile(r"^[가-힣]{2,5}$")
ENGLISH_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z.'’-]*(?:\s+[A-Za-z][A-Za-z.'’-]*){1,4}$")
ENGLISH_COMMA_NAME_RE = re.compile(
    r"^[A-Za-z][A-Za-z.'’-]*,\s*[A-Za-z][A-Za-z.'’-]*(?:\s+[A-Za-z][A-Za-z.'’-]*){0,3}$"
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

# The Korean token "공지" is intentionally not included as a raw substring.
# It is handled through boundary-aware checks so "인공지능" is not penalized.
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
    "연구실 위치",
    "사무실 위치",
    "연구실",
    "사무실",
    "위치",
    "office",
    "location",
    "room",
)

HOMEPAGE_LABELS_STRONG = (
    "연구실 홈페이지",
    "랩 홈페이지",
    "lab homepage",
    "laboratory homepage",
    "lab website",
    "laboratory website",
)

HOMEPAGE_LABELS_WEAK = (
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
    "publication",
    "논문",
)

CARD_CLASS_HINTS = (
    "faculty",
    "professor",
    "people",
    "member",
    "staff",
    "person",
    "teacher",
    "교수",
    "구성원",
)

PROFILE_PATH_HINTS = (
    "faculty",
    "professor",
    "people",
    "member",
    "profile",
    "person",
    "교수",
)

LAB_PATH_HINTS = (
    "lab",
    "laboratory",
    "research-group",
    "research_group",
    "researchgroup",
    "연구실",
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

FORBIDDEN_LAB_URL_HOSTS = {
    "scholar.google.com",
    "orcid.org",
    "www.orcid.org",
    "doi.org",
    "dx.doi.org",
    "researcherid.com",
    "www.researcherid.com",
    "scopus.com",
    "www.scopus.com",
    "publons.com",
    "www.researchgate.net",
}

FORBIDDEN_LAB_URL_TOKENS = (
    "scholar.google",
    "orcid.org",
    "doi.org",
    "publication",
    "publications",
    "paper",
    "papers",
    "researcher-search",
    "researcher_search",
    "researcher/profile",
    "researcherprofile",
    "news",
    "notice",
    "seminar",
    "admission",
    "recruitment",
    "award",
    "press",
)

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

NOISE_EXACT = {
    "",
    ".",
    ":",
    "-",
    "–",
    "—",
    "이름",
    "소개",
    "정보",
    "홈페이지",
    "검색",
    "검색어",
    "필수",
    "page",
    "https",
    "http",
    "email",
    "e-mail",
    "전화",
    "교수 소개 홈페이지",
    "postech 재직중",
    "최신연구",
    "산학협력",
    "성과통계",
    "뉴스",
    "수상 소식",
    "채용 공고",
    "pseudo-lab",
    "pseudo lab",
    "본 연구실",
}

NOISE_SUBSTRINGS = (
    "copyright",
    "all rights reserved",
    "개인정보처리방침",
    "개인정보 처리방침",
    "교원 채용",
    "채용 공고",
    "수상 소식",
    "학과 행사",
    "공지사항",
    "보도자료",
    "관련사이트",
    "family site",
    "skip to content",
    "navigation",
)

SUMMARY_NOISE_PATTERNS = (
    re.compile(r"\b(?:news|notice|award|recruitment|job opening|press release)\b", re.I),
    re.compile(r"(?:교원|교수|연구원|직원)\s*채용", re.I),
    re.compile(r"(?:수상|선정|개최|세미나|워크숍|행사|소식|공지사항)", re.I),
    re.compile(r"\b(?:20\d{2})[./-]\d{1,2}[./-]\d{1,2}\b"),
)

# Strong event/citation signals are rejected even when the sentence contains
# generic words such as "research". This prevents news articles, paper
# abstracts and recruiting notices from being stored as lab introductions.
STRONG_SUMMARY_NOISE_PATTERNS = (
    re.compile(
        r"\b(?:is selected for|has been selected|paper accepted|has been accepted|"
        r"accepted\s*:|congratulations?|is now published|published as|"
        r"open positions?|positions? are open|fellowship|spotlight)\b",
        re.I,
    ),
    re.compile(r"(?:수상|선정|게재되|게재됐|게재하|신입생\s*모집|대학원생\s*모집|"
               r"모집합니다|연락바랍니다|연구장려금|채용\s*공고)"),
    re.compile(r"\bdoi\s*:\s*10\.\d{4,9}/\S+", re.I),
    re.compile(r"\bvol\.?\s*\d+(?:\s*\(|\b)", re.I),
    re.compile(r"\b(?:journal of|transactions on|proceedings of)\b", re.I),
)

CITATION_LIKE_RE = re.compile(
    r"(?:\bdoi\s*:|\bvol\.?\s*\d|\bjournal of\b|\btransactions on\b|"
    r"\bproceedings of\b|[\"“][^\"”]{20,}[\"”].{0,160}\b(?:19|20)\d{2}\b)",
    re.I,
)

ADDRESS_NOISE_RE = re.compile(
    r"(?:\b(?:pohang|gyeong(?:sang)?|nam-?gu|cheongam-ro|jigok-ro|republic of korea)\b|"
    r"\bcontact\s+room\b|\b(?:postal|zip)\s*code\b|\[\d{5}\])",
    re.I,
)

COMPACT_ROOM_CODE_RE = re.compile(
    r"^(?P<building>[A-Za-z]{1,3}\d{1,2})\s*[-,/ ]\s*"
    r"(?P<room>[A-Za-z]?\d{2,4})(?P<suffix>호)?$",
    re.I,
)

FIELD_NOISE_EXACT = {
    "논문",
    "연구논문",
    "수상소식",
    "게시판",
    "포항공대 수학과",
    "포항공과대학교 수학과",
}

KEYWORD_NOISE_PATTERNS = (
    re.compile(
        r"\b(?:selected for|paper accepted|open positions?|associate professor|"
        r"assistant professor|contact room|about me|located in postech|since\s+(?:19|20)\d{2}|"
        r"congratulations?|supervisor)\b",
        re.I,
    ),
    re.compile(r"(?:수상소식|게시판|연구장려금|신입생\s*(?:모집|선발)|대학원생\s*모집|"
               r"대학원생.*연구참여인턴|박사과정.*T\.?O|(?:석사|박사|통합)과정\s*\d+\s*명|"
               r"모집합니다|연락바랍니다|게재되|교수\s*연구팀|선정된\s*과제)"),
    re.compile(r"\b(?:please visit.*web page|publications? web page)\b", re.I),
    re.compile(r"^(?:19|20)\d{2}\s*[~\-]\s*(?:현재|present)$", re.I),
)

PLACEHOLDER_LAB_RE = re.compile(r"^.{2,40}\s*교수\s*연구실$")
LAB_NAME_RE = re.compile(
    r"(?:"
    r"[A-Za-z0-9&+,.()'’\-\s]{2,100}(?:Lab(?:oratory)?|Research Group|Research Center)"
    r"|[가-힣A-Za-z0-9&+,.()'’\-\s]{2,100}(?:연구실|연구그룹|연구센터)"
    r")",
    re.I,
)

IMAGE_NOISE_TOKENS = (
    "logo",
    "icon",
    "favicon",
    "banner",
    "sprite",
    "button",
    "_btn",
    "-btn",
    "/btn",
    "more_btn",
    "profile_mail",
    "mail.png",
    "mail.gif",
    "no_image",
    "no-image",
    "noimage",
    "placeholder",
    "default_profile",
    "default-image",
    "avatar_default",
)

PROFESSOR_NAME_NOISE = {
    "교수",
    "교수진",
    "전임교수",
    "겸임교수",
    "명예교수",
    "학과",
    "대학원",
    "학부",
    "전공",
    "faculty",
    "professor",
    "professors",
    "people",
    "member",
    "members",
    "staff",
}

INLINE_NOISE_TOKENS = {
    "page",
    "홈페이지",
    "교수 소개 홈페이지",
    "이메일",
    "email",
    "e-mail",
    "구성원",
    "전임교수",
    "겸임교수",
    "구술과목 시험범위",
}

NOTICE_BOUNDARY_RE = re.compile(r"(?:^|[\s/_-])공지(?:사항)?(?:$|[\s/_-])", re.I)

COMMON_FACULTY_PATHS = (
    "faculty",
    "faculty/",
    "professor",
    "professor/",
    "professors",
    "people",
    "people/",
    "members",
    "members/",
    "member",
    "staff",
    "research/faculty",
    "about/faculty",
    "sub/faculty",
    "html/people/professor.php",
    "html/major/professor.php",
)

PROFILE_DETAIL_QUERY_KEYS = {
    "idx",
    "wr_id",
    "articleNo",
    "article_no",
    "member_id",
    "professor_id",
    "person_id",
    "code",
}

PROFILE_DETAIL_PATH_RE = re.compile(
    r"(?:faculty|professor|people|member|staff).*(?:view|detail)|"
    r"(?:view|detail).*(?:faculty|professor|people|member)|"
    r"/(?:faculty|professor|people|member)/[^/]+/?$",
    re.I,
)

PAGINATION_TEXT_RE = re.compile(r"^(?:next|previous|prev|다음|이전|[0-9]{1,3}|[>»›<«‹]+)$", re.I)

# Conservative official candidates. They are only queued; a page must still
# contain known professor identities before data is merged.
DEFAULT_FACULTY_URLS_BY_NAME = {
    "IT융합공학과": [
        "https://cite.postech.ac.kr/bbs/board.php?bo_table=sub2_1_a",
        "https://cite.postech.ac.kr/bbs/board.php?bo_table=sub2_1_b",
        "https://cite.postech.ac.kr/bbs/board.php?bo_table=sub2_1_e",
    ],
    "생명과학과": [
        "https://life.postech.ac.kr/html/professor/professor01.php",
        "https://life.postech.ac.kr/eng/html/professor/professor01.php",
    ],
    "수학과": [
        "https://math.postech.ac.kr/bbs/board.php?bo_table=m02_01&page=1",
        "https://math.postech.ac.kr/bbs/board.php?bo_table=m02_01&page=2",
        "https://math.postech.ac.kr/en/bbs/board.php?bo_table=m02_01&page=1",
        "https://math.postech.ac.kr/en/bbs/board.php?bo_table=m02_01&page=2",
    ],
    "시스템생명공학부": [
        "https://ibio.postech.ac.kr/web/?depart=1&position=1&sub=professor&top=member",
        "https://ibio.postech.ac.kr/web/?depart=1&position=2&sub=professor&top=member",
    ],
    "첨단재료과학부": [
        "https://gscst.postech.ac.kr/web/?depart=2&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=2&position=2&sub=professor&top=member",
    ],
    "의과학전공": [
        "https://emed.postech.ac.kr/web/?depart=1&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=11&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=11&position=2&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=11&position=3&sub=professor&top=member",
    ],
    "국방과학기술전공": [
        "https://dst.postech.ac.kr/",
        "https://gscst.postech.ac.kr/web/?depart=14&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=14&position=2&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=14&position=3&sub=professor&top=member",
    ],
    "경영과학전공": [
        "https://gscst.postech.ac.kr/web/?depart=15&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=15&position=2&sub=professor&top=member",
    ],
    "푸드테크융합전공": [
        "https://foodtech.postech.ac.kr/foodtech/abo/contact.do",
        "https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=16&position=2&sub=professor&top=member",
    ],
    "양자정보과학전공": [
        "https://quantum.postech.ac.kr/",
        "https://gscst.postech.ac.kr/web/?depart=17&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=17&position=2&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=17&position=3&sub=professor&top=member",
    ],
    "산업데이터사이언스전공": [
        "https://ids.postech.ac.kr/faculty",
        "https://ids.postech.ac.kr/faculty_en",
        "https://gscst.postech.ac.kr/web/?depart=18&position=1&sub=professor&top=member",
        "https://gscst.postech.ac.kr/web/?depart=18&position=2&sub=professor&top=member",
    ],
}



# ============================================================
# 2. CSV schemas
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
    "enricher_version",
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
    "keyword_source",
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
    "primary_department_id",
    "department_type",
    "affiliated_programs",
    "primary_field",
    "department_page_url",
    "enrichment_source_urls",
    "enrichment_status",
    "enrichment_message",
    "data_quality_status",
    "enriched_at",
    "lab_url_status",
    "enricher_version",
]

ALLOWED_LAB_URL_STATUSES = {
    "verified_card",
    "verified_homepage",
    "candidate_card",
    "manual",
    "unverified",
    "invalid",
}

TRUSTED_LAB_URL_STATUSES = {
    "verified_card",
    "verified_homepage",
    "manual",
}


# ============================================================
# 3. Runtime paths and data classes
# ============================================================
@dataclass(frozen=True)
class RuntimePaths:
    data_dir: Path
    departments: Path
    labs: Path
    overrides: Path
    backups: Path
    raw: Path
    log: Path

    @classmethod
    def from_args(cls, data_dir: Path, overrides: Optional[Path]) -> "RuntimePaths":
        data_dir = data_dir.expanduser().resolve()
        override_path = overrides.expanduser().resolve() if overrides else data_dir / "site_overrides.json"
        return cls(
            data_dir=data_dir,
            departments=data_dir / "departments.csv",
            labs=data_dir / "labs.csv",
            overrides=override_path,
            backups=data_dir / "backups",
            raw=data_dir / "raw_stage2",
            log=data_dir / "stage2_crawl_log.jsonl",
        )


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
class MatchResult:
    lab_id: str
    block: Tag
    method: str
    page_url: str


@dataclass
class CleanReport:
    changed_rows: int = 0
    changed_fields: Counter[str] = field(default_factory=Counter)
    blanked_noise: Counter[str] = field(default_factory=Counter)
    duplicate_noise: Counter[str] = field(default_factory=Counter)
    invalid_urls: int = 0


@dataclass
class RespectfulClient:
    delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    browser_fallback: bool = False
    allow_insecure: bool = False
    respect_robots: bool = DEFAULT_RESPECT_ROBOTS
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
            parser.set_url(f"{base}/robots.txt")
            try:
                self._sleep_if_needed()
                response = self.session.get(
                    f"{base}/robots.txt",
                    timeout=min(self.timeout_seconds, 12),
                    verify=not self.allow_insecure,
                )
                self._last_request_at = time.monotonic()
                parser.parse(response.text.splitlines() if response.ok else [])
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
        if content_type and "html" not in content_type and "xml" not in content_type:
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
        return len(text) < 250 and len(soup.find_all("script")) >= 5

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
# 4. Common utilities
# ============================================================
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


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
    text = clean_text(value).lower().replace("mailto:", "").split("?", 1)[0]
    match = EMAIL_RE.search(text)
    return match.group(0).lower() if match else ""


def normalize_name(value: str) -> str:
    text = clean_text(value).lower()
    text = re.sub(
        r"(?:교수|부교수|조교수|석좌교수|명예교수|professor|associate|assistant|emeritus|ph\.?d\.?)",
        "",
        text,
        flags=re.I,
    )
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def normalized_department_name(value: str) -> str:
    return re.sub(r"\s+", "", clean_text(value)).lower()


def normalize_url(url: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    netloc = parsed.netloc.lower().rstrip(".")
    if not netloc or "." not in (parsed.hostname or ""):
        return ""
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    parsed = parsed._replace(scheme=parsed.scheme.lower(), netloc=netloc, path=path)
    return urlunparse(parsed)


def absolute_url(base_url: str, href: str) -> str:
    href = clean_text(href)
    if not href or href.startswith(("mailto:", "tel:", "#")):
        return ""
    if href.startswith("javascript:"):
        quoted = re.search(r"['\"]([^'\"]+)['\"]", href)
        href = quoted.group(1) if quoted else ""
    return normalize_url(urljoin(base_url, href)) if href else ""


def anchor_target_url(base_url: str, anchor: Tag) -> str:
    candidates = [
        clean_text(anchor.get("href", "")),
        clean_text(anchor.get("data-href", "")),
        clean_text(anchor.get("data-url", "")),
        clean_text(anchor.get("data-link", "")),
    ]
    onclick = clean_text(anchor.get("onclick", ""))
    if onclick:
        candidates.extend(match.group(1) for match in re.finditer(r"['\"]([^'\"]+)['\"]", onclick))
    for raw in candidates:
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
        items = [clean_text(x) for x in value] if isinstance(value, (list, tuple, set)) else split_multi(str(value))
        for item in items:
            key = item.casefold()
            if item and key not in seen:
                seen.add(key)
                merged.append(item)
                if limit is not None and len(merged) >= limit:
                    return ";".join(merged)
    return ";".join(merged)


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = clean_text(value)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def classify_department_label(value: str) -> str:
    mapping = {
        "department": "학과",
        "division": "학부",
        "graduate_school": "대학원",
        "program": "전공",
    }
    return mapping.get(clean_text(value), clean_text(value) or "미분류")


def ensure_fields(existing: list[str], preferred: list[str]) -> list[str]:
    fields = list(existing)
    for field_name in preferred:
        if field_name not in fields:
            fields.append(field_name)
    return fields


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV 파일이 없습니다: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader], list(reader.fieldnames or [])


def atomic_write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    target_mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with temp_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temp_path, target_mode)
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def backup_file(path: Path, backup_dir: Path, run_slug: str) -> Optional[Path]:
    if not path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"{path.stem}_before_stage2_{run_slug}{path.suffix}"
    shutil.copy2(path, destination)
    return destination


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_overrides(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError("site_overrides.json 최상위 값은 객체여야 합니다.")
    return payload


def is_noise_exact(value: str) -> bool:
    return clean_text(value).casefold() in NOISE_EXACT


def strip_urls(value: str) -> str:
    text = clean_text(value)
    text = URL_RE.sub(" ", text)
    text = BARE_DOMAIN_RE.sub(" ", text)
    return clean_text(re.sub(r"\s*([;|,])\s*(?=\1|$)", "", text))


def looks_urlish_text(value: str) -> bool:
    text = clean_text(value)
    if not text:
        return False
    return bool(URL_RE.search(text) or BARE_DOMAIN_RE.search(text))


def clean_professor_name(value: str, department_name: str = "") -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = re.sub(
        r"(?i)^(?:prof(?:essor)?\.?|associate professor|assistant professor|교수|부교수|조교수|석좌교수|명예교수)\s*[:：-]?\s*",
        "",
        text,
    )
    text = re.sub(
        r"(?i)\s*(?:prof(?:essor)?\.?|associate professor|assistant professor|교수|부교수|조교수|석좌교수|명예교수)$",
        "",
        text,
    )
    text = re.sub(r"\s*\((?:학과장|주임교수|department chair|chair)\)\s*$", "", text, flags=re.I)
    text = clean_text(text)

    # Official pages frequently use bilingual forms such as
    # "이기예(Qirui Li)" or "Qirui Li (이기예)". Prefer the Korean
    # display name when one is explicitly supplied.
    bilingual = re.fullmatch(r"(?P<left>[^()]{2,80})\s*\((?P<right>[^()]{2,80})\)", text)
    if bilingual:
        left = clean_text(bilingual.group("left"))
        right = clean_text(bilingual.group("right"))
        if KOREAN_NAME_RE.fullmatch(left):
            text = left
        elif KOREAN_NAME_RE.fullmatch(right):
            text = right
        elif ENGLISH_NAME_RE.fullmatch(left) or ENGLISH_COMMA_NAME_RE.fullmatch(left):
            text = left
        elif ENGLISH_NAME_RE.fullmatch(right) or ENGLISH_COMMA_NAME_RE.fullmatch(right):
            text = right

    low = text.casefold()
    department_low = clean_text(department_name).casefold()
    if not text or low in PROFESSOR_NAME_NOISE:
        return ""
    if department_low and low == department_low:
        return ""
    if any(token in low for token in ("연구실", "laboratory", " lab", "department", "university", "postech")):
        return ""
    if KOREAN_NAME_RE.fullmatch(text):
        return text
    if ENGLISH_NAME_RE.fullmatch(text) or ENGLISH_COMMA_NAME_RE.fullmatch(text):
        return text
    return ""


def professor_name_quality(value: str, department_name: str = "") -> int:
    cleaned = clean_professor_name(value, department_name)
    if not cleaned:
        return 0
    return 10 if KOREAN_NAME_RE.fullmatch(cleaned) else 7


def contains_noise_phrase(value: str) -> bool:
    low = clean_text(value).casefold()
    return any(token.casefold() in low for token in NOISE_SUBSTRINGS)


def looks_placeholder_lab_name(value: str) -> bool:
    text = clean_text(value)
    return not text or bool(PLACEHOLDER_LAB_RE.fullmatch(text))


def is_probable_lab_name(value: str) -> bool:
    text = clean_text(value)
    if not (3 <= len(text) <= 140) or is_noise_exact(text) or contains_noise_phrase(text):
        return False
    low = text.casefold()
    if low in GENERIC_LINK_TEXTS:
        return False
    if re.match(r"^\s*\d+[.)]\s*", text):
        return False
    if low.startswith(("welcome to ", "recent publication", "selected publication")):
        text = re.sub(r"(?i)^welcome\s+to\s+", "", text).strip(" .:-")
        low = text.casefold()
    if "department of" in low and not any(token in low for token in (" lab", "laboratory", "research group")):
        return False
    if len(text.split()) > 16:
        return False
    return bool(LAB_NAME_RE.fullmatch(text) or LAB_NAME_RE.search(text))


def strip_site_suffix(value: str) -> str:
    text = clean_text(value)
    chunks = re.split(r"\s*[|·–—]\s*|\s+-\s+", text)
    for chunk in chunks:
        if is_probable_lab_name(chunk):
            return clean_text(chunk)
    return text


def canonical_phone(value: str) -> str:
    match = PHONE_RE.search(clean_text(value))
    if not match:
        return ""
    digits = re.sub(r"\D", "", match.group(0))
    if digits.startswith("82"):
        digits = "0" + digits[2:]
    if len(digits) == 7 and digits.startswith("279"):
        return f"279-{digits[-4:]}"
    if len(digits) == 10 and digits.startswith("054279"):
        return f"054-279-{digits[-4:]}"
    return clean_text(match.group(0))


def valid_image_url(url: str) -> bool:
    url = normalize_url(url)
    if not url:
        return False
    low = url.casefold()
    if any(token in low for token in IMAGE_NOISE_TOKENS):
        return False
    suffix = Path(urlparse(url).path).suffix.casefold()
    if suffix and suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
        return False
    return True


def url_query_has_board(url: str) -> bool:
    query = parse_qs(urlparse(url).query)
    return "bo_table" in query or "board" in query


def is_forbidden_lab_url(url: str, professor_profile_url: str = "") -> bool:
    url = normalize_url(url)
    if not url:
        return True
    if normalize_url(professor_profile_url) == url:
        return True
    host = hostname(url)
    low = url.casefold()
    if host in SOCIAL_HOSTS or root_host(host) in SOCIAL_HOSTS:
        return True
    if host in FORBIDDEN_LAB_URL_HOSTS or root_host(host) in FORBIDDEN_LAB_URL_HOSTS:
        return True
    if any(token in low for token in FORBIDDEN_LAB_URL_TOKENS):
        return True
    path_low = urlparse(url).path.casefold()
    if any(token in path_low for token in ("/faculty", "/professor", "/profile", "/researcher")) and not any(
        token in path_low for token in LAB_PATH_HINTS
    ):
        return True
    if url_query_has_board(url) or re.search(r"/(?:bbs|board)(?:/|\.php|$)", path_low, re.I):
        return True
    if low.endswith((".pdf", ".hwp", ".doc", ".docx", ".xls", ".xlsx", ".zip")):
        return True
    return False


def lab_url_status_rank(status: str) -> int:
    return {
        "invalid": 0,
        "unverified": 1,
        "candidate_card": 2,
        "verified_card": 3,
        "verified_homepage": 4,
        "manual": 5,
    }.get(clean_text(status), 1)


def normalize_lab_url_status(value: str, url: str) -> str:
    status = clean_text(value)
    if not normalize_url(url):
        return "invalid" if status == "invalid" else "unverified"
    return status if status in ALLOWED_LAB_URL_STATUSES else "unverified"


def selector_values(node: Tag, selectors: Sequence[str], attr: Optional[str] = None) -> list[str]:
    values: list[str] = []
    for selector in selectors:
        try:
            selected = node.select(selector)
        except Exception:
            continue
        for item in selected:
            if attr:
                value = clean_text(item.get(attr, ""))
            else:
                value = clean_text(item.get_text(" ", strip=True))
            if value:
                values.append(value)
    return unique_preserve_order(values)


# ============================================================
# 5. Cleaning and contamination detection
# ============================================================
def clean_lab_name(value: str, professor_name: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if looks_placeholder_lab_name(text):
        expected = f"{clean_text(professor_name)} 교수 연구실" if clean_text(professor_name) else ""
        return text if expected and text == expected else ""
    if is_noise_exact(text) or contains_noise_phrase(text):
        return ""
    text = re.sub(r"(?i)^welcome\s+to\s+", "", text).strip(" .:-")
    if len(text) > 140:
        text = strip_site_suffix(text)
    match = LAB_NAME_RE.search(text)
    if match and match.group(0) != text:
        candidate = clean_text(match.group(0)).strip(" .:-")
        if is_probable_lab_name(candidate):
            text = candidate
    return text if is_probable_lab_name(text) else ""


def clean_location_value(value: str) -> str:
    text = clean_text(value)
    if not text or is_noise_exact(text) or contains_noise_phrase(text):
        return ""
    low = text.casefold()
    if EMAIL_RE.search(text) or len(text) > 180:
        return ""
    if any(token in low for token in ("accepted to", "publication", "conference", "work on", "award", "news", "display 20")):
        return ""

    # POSTECH pages frequently use compact building codes such as "C5 309".
    # These are valid locations even without the Korean "호" suffix.
    compact = COMPACT_ROOM_CODE_RE.fullmatch(text)
    if compact:
        suffix = compact.group("suffix") or ""
        return f"{compact.group('building').upper()} {compact.group('room').upper()}{suffix}"

    match = ROOM_RE.search(text)
    if match:
        candidate = clean_text(match.group(0))
        if re.search(
            r"(?:관|동|센터|연구소|building|bldg\.?|center|room|rm\.?|호|^[A-Za-z]{1,3}\d{1,2}\s)",
            candidate,
            re.I,
        ):
            return candidate
    # Keep a labeled building/room phrase only if the location token is explicit.
    if re.search(r"(?:관|동|센터|연구소)[^;]{0,35}\d", text):
        return text
    if re.search(r"\b(?:building|bldg\.?|center|room|rm\.?)\b[^;]{0,35}\d", text, re.I):
        return text
    return ""


def clean_primary_field_value(value: str) -> str:
    text = clean_text(value)
    if not text or is_noise_exact(text) or contains_noise_phrase(text):
        return ""
    if EMAIL_RE.search(text) or PHONE_RE.search(text):
        return ""
    low = text.casefold()
    forbidden = (
        "postech 재직중",
        "assistant professor@",
        "교수 소개 홈페이지",
        "응용데이터과학; 정보",
    )
    if any(token in low for token in forbidden):
        return ""
    result: list[str] = []
    for raw_chunk in re.split(r"[;|•·\n]+", text):
        chunk = strip_urls(raw_chunk).strip(" .,:;|-/")
        chunk_low = chunk.casefold()
        if not chunk or is_noise_exact(chunk) or contains_noise_phrase(chunk):
            continue
        if chunk_low in INLINE_NOISE_TOKENS or looks_urlish_text(chunk):
            continue
        if chunk_low in FIELD_NOISE_EXACT:
            continue
        if re.fullmatch(r"(?i)(?:view|site|home|index|faculty|member|professor)", chunk):
            continue
        if re.fullmatch(r"(?i)(?:19|20)\d{2}\s*[~\-]\s*(?:현재|present)", chunk):
            continue
        if any(pattern.search(chunk) for pattern in KEYWORD_NOISE_PATTERNS):
            continue
        if 2 <= len(chunk) <= 160:
            result.append(chunk)
    return "; ".join(unique_preserve_order(result))[:MAX_PRIMARY_FIELD_CHARS]


RECRUITMENT_ONLY_RE = re.compile(
    r"(?is)^(?:open positions?|we are (?:hiring|recruiting)|join us|"
    r"대학원생|학부연구생|연구원|박사과정|석박사통합과정).{0,900}"
    r"(?:모집|지원|contact|position|candidate)"
)

PUBLICATION_ANNOUNCEMENT_RE = re.compile(
    r"(?is)^(?:\d+\s+papers?\s+(?:was\s+|were\s+|has\s+been\s+)?accepted"
    r"|(?:new|recent)\s+paper\s+(?:accepted|published)"
    r"|논문\s*\d*\s*편?\s*(?:게재|채택|발표)"
    r"|(?:본|해당|이번)\s*논문.{0,500}(?:게재|채택|발표))"
)

SUBSTANTIVE_RESEARCH_RE = re.compile(
    r"(?i)(?:개발|분석|규명|설계|모델링|최적화|합성|측정|탐구|시뮬레이션|"
    r"focus(?:es|ed|ing)?\s+on|develop(?:s|ed|ing|ment)?|"
    r"investigat(?:e|es|ed|ing|ion)|analy[sz](?:e|es|ed|ing|is)|"
    r"model(?:s|ed|ing)?|design(?:s|ed|ing)?|simulate(?:s|d|ing|ion)?)"
)


def summary_has_news_noise(text: str) -> bool:
    return any(pattern.search(text) for pattern in SUMMARY_NOISE_PATTERNS)


def summary_has_strong_noise(text: str) -> bool:
    return any(pattern.search(text) for pattern in STRONG_SUMMARY_NOISE_PATTERNS)


def clean_summary_value(value: str) -> str:
    text = clean_text(value)
    if not text or is_noise_exact(text) or contains_noise_phrase(text):
        return ""
    if EMAIL_RE.search(text):
        return ""

    text = strip_urls(text)
    if PUBLICATION_ANNOUNCEMENT_RE.search(text):
        return ""
    if RECRUITMENT_ONLY_RE.search(text) and not SUBSTANTIVE_RESEARCH_RE.search(text):
        return ""

    text = re.sub(
        r"(?is)\s*[;|]\s*(?:연구논문|논문|publications?)\s*[;:]?.*$",
        "",
        text,
    )
    text = re.sub(
        r"(?is)\s*(?:for further (?:description|information).*|please visit (?:our )?.*)$",
        "",
        text,
    )

    # Keep substantive research prose while trimming a trailing publication,
    # award or recruiting sentence. This avoids deleting a valid long summary
    # merely because its final sentence says that the work was published.
    trailing_noise_patterns = (
        r"\s+(?:본|해당|이번)\s*연구(?:\s*결과)?는[^.。]{0,500}(?:게재|발표|선정|수상)[^.。]*(?:[.。]|$)\s*$",
        r"\s+(?:this|the)\s+(?:work|study|research)[^.]{0,500}(?:was|is|has been)\s+(?:published|accepted|selected)[^.]*[.]?\s*$",
        r"\s+congratulations?[^.]*[.]?\s*$",
    )
    for pattern in trailing_noise_patterns:
        text = re.sub(pattern, "", text, flags=re.I)

    chunks: list[str] = []
    for chunk in re.split(r"[;|\n]+", text):
        candidate = clean_text(chunk).strip(" .,:;|-/")
        candidate_low = candidate.casefold()
        if not candidate or candidate_low in INLINE_NOISE_TOKENS or is_noise_exact(candidate):
            continue
        if candidate_low in FIELD_NOISE_EXACT:
            continue
        chunks.append(candidate)
    text = "; ".join(unique_preserve_order(chunks))
    if not text:
        return ""

    low = text.casefold()
    research_context = bool(
        re.search(
            r"(?:연구(?:를|하|분야|목표|주제)|개발|분석|탐구|규명|수행|"
            r"\b(?:researches|researching|develop(?:s|ed|ing|ment)?|"
            r"focus(?:es|ed|ing)?|investigat(?:e|es|ed|ing|ion)|"
            r"stud(?:y|ies|ied|ying)|analy[sz](?:e|es|ed|ing|is)|model(?:s|ed|ing)?)\b|"
            r"\bresearch\s+(?:at|in|on)\b.{0,160}\b(?:address(?:es|ed)?|"
            r"focus(?:es|ed)?|investigat(?:e|es|ed)?|stud(?:y|ies|ied)|develop(?:s|ed)?)\b|"
            r"\b(?:conduct|pursue|perform)\s+(?:our\s+)?research\b)",
            low,
            re.I,
        )
    )
    career_context = any(
        token in low
        for token in ("주요경력", "경력", "학력", "education", "career", "박사후 연구원", "방문교수")
    )
    if career_context and not research_context:
        return ""

    # Citation-only, award-only and recruiting-only text is rejected. If valid
    # research prose remains after the trailing-noise trim, publication words
    # alone no longer invalidate the whole summary.
    if CITATION_LIKE_RE.search(text) and not research_context:
        return ""
    if summary_has_strong_noise(text) and not research_context:
        return ""
    if summary_has_news_noise(text) and not research_context:
        return ""
    if ADDRESS_NOISE_RE.search(text) and not research_context:
        return ""

    minimum_length = 10 if text.startswith("주요 연구 분야:") else 25
    if len(text) < minimum_length:
        return ""
    return text[:MAX_SUMMARY_CHARS]


def keyword_item_is_noise(item: str) -> bool:
    text = clean_text(item)
    low = text.casefold()
    if low in FIELD_NOISE_EXACT:
        return True
    if any(pattern.search(text) for pattern in KEYWORD_NOISE_PATTERNS):
        return True
    if CITATION_LIKE_RE.search(text):
        return True
    if ADDRESS_NOISE_RE.search(text):
        return True
    if re.search(r"\b(?:pohang|south korea|republic of korea|nam-gu|gyeongsangbuk-do)\b", text, re.I):
        return True
    if re.search(
        r"\b(?:postdoc|ph\.?d\.?|m\.?s\.?|b\.?s\.?|mentor|advisor|curriculum vitae)\b|"
        r"(?:주요경력|박사후\s*연구원|방문교수|부교수|조교수|겸임교수|참여교수|JA겸임교수)",
        text,
        re.I,
    ):
        return True
    if re.search(r"(?:대학교?|대학)\s*[A-Za-z가-힣& ]{0,40}(?:학과|대학원|연구소|센터)$", text):
        return True
    if re.fullmatch(r"[a-z]+(?:-[a-z]+)?\s+[a-z]+", text):
        return True
    if re.search(r"\b(?:19|20)\d{2}[./-]\d{1,2}[./-]\d{1,2}\b", text):
        return True
    if re.fullmatch(r"\d+\s*\(\s*\d+\s*\)", text):
        return True
    if re.match(r"(?i)^and\s+[A-Z][A-Za-z-]+$", text):
        return True
    if re.search(r"\b(?:journal|communications|transactions|proceedings|volume|issue)\b|\badv\.?\s*sci\.?", text, re.I):
        return True
    if re.search(r"(?:설계경험|평가인프라|집적공정|기술융합센터|나노융합기술원)", text):
        return True
    if len(text) > 55 and re.search(
        r"(?:가능하며|달성하는|선정된\s*과제|"
        r"\b(?:is|are|was|were|has|have|before joining)\b)",
        text,
        re.I,
    ):
        return True
    return False


def clean_keywords_value(value: str) -> str:
    stop = {
        "page",
        "https",
        "http",
        "홈페이지",
        "교수 소개 홈페이지",
        "이메일",
        "email",
        "assistant professor@postech",
        "postech 재직중",
        "검색",
        "검색어",
        "필수",
        "구성원",
        "전임교수",
        "겸임교수",
        "구술과목 시험범위",
        "view",
        "site",
        "home",
        "index",
        "논문",
        "연구논문",
        "수상소식",
        "게시판",
        "포항공대 수학과",
        "포항공과대학교 수학과",
        "통합",
        "or",
        "and",
        "the",
    }
    raw_items = [clean_text(x) for x in re.split(r"[;|,•·\n]+", clean_text(value))]
    skip_indexes: set[int] = set()
    for index, raw_item in enumerate(raw_items):
        if not looks_urlish_text(raw_item):
            continue
        skip_indexes.add(index)
        for following in range(index + 1, min(index + 4, len(raw_items))):
            token = raw_items[following].strip(" ./")
            if re.fullmatch(r"(?i)[~a-z0-9_.-]{2,40}", token):
                skip_indexes.add(following)
            else:
                break

    result: list[str] = []
    citation_mode = 0
    for index, raw_item in enumerate(raw_items):
        if index in skip_indexes:
            continue
        item = strip_urls(raw_item)
        item = clean_text(re.sub(r"^[#\-–—:：]+|[#\-–—:：]+$", "", item)).strip(" ./")
        item = re.sub(r"(?i)^introduction\s+(?:the\s+)?", "", item).strip()
        acronym_match = re.fullmatch(r"[A-Za-z0-9_-]{2,20}\((.+)", item)
        if acronym_match:
            item = acronym_match.group(1).strip()
        low = item.casefold()

        if low in {"논문", "연구논문", "publication", "publications"}:
            citation_mode = 6
            continue
        if citation_mode:
            if re.search(r"[가-힣]", item) and not keyword_item_is_noise(item):
                citation_mode = 0
            else:
                citation_mode -= 1
                continue

        if not (2 <= len(item) <= 90):
            continue
        if low in stop or is_noise_exact(item) or contains_noise_phrase(item):
            continue
        if keyword_item_is_noise(item):
            continue
        if EMAIL_RE.search(item) or PHONE_RE.search(item) or looks_urlish_text(item):
            continue
        if re.fullmatch(r"(?i)(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/.*)?", item):
            continue
        result.append(item)
    return ";".join(unique_preserve_order(result)[:MAX_KEYWORDS])


def clean_profile_image_url(value: str) -> str:
    return normalize_url(value) if valid_image_url(value) else ""


PROVENANCE_NOISE_RE = re.compile(
    r"(?i)(?:"
    r"/(?:news|notice|admission|recruit|award|seminar|event|gallery)(?:/|$)"
    r"|facultyapplication\.postech\.ac\.kr"
    r"|postechian\.org/alumni"
    r"|/invitation/"
    r")"
)


def sanitize_enrichment_source_urls(
    row: dict[str, str],
    extra_values: Iterable[str] = (),
) -> str:
    """Keep only compact, identity-relevant provenance URLs.

    Discovery pages are useful while crawling, but unrelated news, recruiting,
    alumni and navigation links should not accumulate in labs.csv.
    """
    anchor_fields = (
        "source_url",
        "professor_profile_url",
        "department_page_url",
        "lab_url",
    )
    anchors = [normalize_url(row.get(field_name, "")) for field_name in anchor_fields]
    anchor_set = {url for url in anchors if url}

    candidates: list[str] = []
    candidates.extend(split_multi(row.get("enrichment_source_urls", "")))
    for value in extra_values:
        candidates.extend(split_multi(value))
    candidates.extend(url for url in anchors if url)

    department_url = normalize_url(row.get("department_page_url", ""))
    department_host = hostname(department_url)
    kept: list[str] = []
    for candidate in candidates:
        url = normalize_url(candidate)
        if not url:
            continue
        if url in anchor_set:
            kept.append(url)
            continue
        if PROVENANCE_NOISE_RE.search(url):
            continue
        if department_host and hostname(url) == department_host:
            low = url.casefold()
            query = parse_qs(urlparse(url).query)
            identity_like = any(
                token in low
                for token in (
                    "faculty",
                    "professor",
                    "people",
                    "member",
                    "researcher-search",
                    "m02_01",
                    "교수",
                )
            )
            detail_like = any(
                key in query
                for key in ("wr_id", "articleNo", "idx", "id", "mode")
            )
            if identity_like or detail_like:
                kept.append(url)

    return ";".join(unique_preserve_order(kept)[:MAX_ENRICHMENT_SOURCE_URLS])


def clean_existing_lab_row(row: dict[str, str], report: CleanReport) -> dict[str, str]:
    original = dict(row)
    cleaned = dict(row)

    original_professor_name = clean_text(cleaned.get("professor_name", ""))
    professor_name = clean_professor_name(
        original_professor_name,
        cleaned.get("department_name", "") or cleaned.get("department_name_raw", ""),
    )
    cleaned["professor_name"] = professor_name
    cleaned["email"] = normalize_email(cleaned.get("email", ""))
    cleaned["phone"] = canonical_phone(cleaned.get("phone", ""))
    cleaned["location"] = clean_location_value(cleaned.get("location", ""))
    cleaned["primary_field"] = clean_primary_field_value(cleaned.get("primary_field", ""))
    cleaned["keywords"] = clean_keywords_value(cleaned.get("keywords", ""))
    cleaned["research_summary"] = clean_summary_value(cleaned.get("research_summary", ""))
    cleaned["profile_image_url"] = clean_profile_image_url(cleaned.get("profile_image_url", ""))

    old_lab_name = clean_text(cleaned.get("lab_name_kor", ""))
    new_lab_name = clean_lab_name(old_lab_name, professor_name)
    if not professor_name and looks_placeholder_lab_name(old_lab_name):
        new_lab_name = ""
    if professor_name and not new_lab_name:
        new_lab_name = f"{professor_name} 교수 연구실"
    cleaned["lab_name_kor"] = new_lab_name

    lab_url = normalize_url(cleaned.get("lab_url", ""))
    status = normalize_lab_url_status(cleaned.get("lab_url_status", ""), lab_url)
    if lab_url and is_forbidden_lab_url(lab_url, cleaned.get("professor_profile_url", "")):
        lab_url = ""
        status = "invalid"
        report.invalid_urls += 1
    # Invalid URLs are kept in enrichment_source_urls/logs, not in the
    # user-facing lab_url column.
    if status == "invalid":
        lab_url = ""
    cleaned["lab_url"] = lab_url
    cleaned["lab_url_status"] = status

    if clean_text(cleaned.get("recruiting_status", "")) not in {"open", "closed", "always_open", "unknown"}:
        cleaned["recruiting_status"] = "unknown"

    cleaned["affiliated_programs"] = merge_multi(
        cleaned.get("affiliated_programs", ""),
        cleaned.get("department_name", ""),
    )
    cleaned["primary_department_id"] = clean_text(
        cleaned.get("primary_department_id", "") or cleaned.get("department_id", "")
    )
    cleaned["enrichment_source_urls"] = sanitize_enrichment_source_urls(cleaned)
    cleaned["enricher_version"] = ENRICHER_VERSION

    for field_name, value in cleaned.items():
        if clean_text(original.get(field_name, "")) != clean_text(value):
            report.changed_fields[field_name] += 1
            if clean_text(original.get(field_name, "")) and not clean_text(value):
                report.blanked_noise[field_name] += 1
    if any(clean_text(original.get(k, "")) != clean_text(cleaned.get(k, "")) for k in cleaned):
        report.changed_rows += 1
    return cleaned


def repeated_cross_department_values(
    rows: Sequence[dict[str, str]],
    field_name: str,
    min_rows: int,
    min_departments: int,
) -> set[str]:
    value_rows: defaultdict[str, int] = defaultdict(int)
    value_departments: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        value = clean_text(row.get(field_name, ""))
        if not value:
            continue
        key = value.casefold()
        value_rows[key] += 1
        value_departments[key].add(
            normalized_department_name(row.get("department_name", "") or row.get("department_id", ""))
        )
    return {
        key
        for key, count in value_rows.items()
        if count >= min_rows and len(value_departments[key]) >= min_departments
    }


def remove_duplicate_lab_urls(rows: list[dict[str, str]], report: CleanReport) -> None:
    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        url = normalize_url(row.get("lab_url", ""))
        if url:
            groups[url.casefold()].append(row)

    for group in groups.values():
        departments = {
            normalized_department_name(row.get("department_name", "") or row.get("department_id", ""))
            for row in group
        }
        if len(group) < 2 or len(departments) <= 1:
            continue

        manual_rows = [row for row in group if row.get("lab_url_status") == "manual"]
        if manual_rows:
            keep_ids = {row.get("lab_id", "") for row in manual_rows}
        else:
            ranked = sorted(
                group,
                key=lambda row: (
                    lab_url_status_rank(row.get("lab_url_status", "")),
                    professor_name_quality(row.get("professor_name", ""), row.get("department_name", "")),
                    bool(clean_text(row.get("email", ""))),
                ),
                reverse=True,
            )
            best_rank = lab_url_status_rank(ranked[0].get("lab_url_status", ""))
            best = [row for row in ranked if lab_url_status_rank(row.get("lab_url_status", "")) == best_rank]
            keep_ids = {best[0].get("lab_id", "")} if best_rank >= lab_url_status_rank("verified_card") and len(best) == 1 else set()

        for row in group:
            if row.get("lab_id", "") in keep_ids:
                continue
            row["lab_url"] = ""
            row["lab_url_status"] = "invalid"
            report.duplicate_noise["lab_url"] += 1
            report.changed_fields["lab_url"] += 1
            report.changed_fields["lab_url_status"] += 1


def remove_duplicate_profile_images(rows: list[dict[str, str]], report: CleanReport) -> None:
    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        url = normalize_url(row.get("profile_image_url", ""))
        if url:
            groups[url.casefold()].append(row)
    for group in groups.values():
        professor_ids = {
            normalize_email(row.get("email", "")) or row.get("researcher_id", "")
            for row in group
        }
        if len(professor_ids) < 2:
            continue

        # profile_image_url is a professor portrait, not a lab/group image.
        # The exact same file assigned to different professors is therefore
        # safer to blank than to expose as a potentially incorrect portrait.
        for row in group:
            row["profile_image_url"] = ""
            report.duplicate_noise["profile_image_url"] += 1
            report.changed_fields["profile_image_url"] += 1


def remove_professor_name_keywords(rows: list[dict[str, str]], report: CleanReport) -> None:
    known_names = {
        normalize_name(row.get("professor_name", ""))
        for row in rows
        if clean_professor_name(row.get("professor_name", ""), row.get("department_name", ""))
    }
    known_names.discard("")
    for row in rows:
        value = clean_text(row.get("keywords", ""))
        if not value:
            continue
        kept: list[str] = []
        removed = False
        for item in split_multi(value):
            if normalize_name(item) in known_names:
                removed = True
                continue
            kept.append(item)
        new_value = ";".join(unique_preserve_order(kept)[:MAX_KEYWORDS])
        if removed and new_value != value:
            row["keywords"] = new_value
            report.duplicate_noise["keywords_professor_name"] += 1
            report.changed_fields["keywords"] += 1


def remove_cross_department_contamination(rows: list[dict[str, str]], report: CleanReport) -> None:
    thresholds = {
        "research_summary": (6, 3),
        "primary_field": (10, 4),
        "location": (8, 4),
        "lab_name_kor": (6, 3),
        "lab_url": (5, 3),
    }
    repeated = {
        field_name: repeated_cross_department_values(rows, field_name, *threshold)
        for field_name, threshold in thresholds.items()
    }

    for row in rows:
        for field_name, bad_values in repeated.items():
            value = clean_text(row.get(field_name, ""))
            if not value or value.casefold() not in bad_values:
                continue
            # A stage-1 placeholder can legitimately appear only once per professor,
            # so a cross-department repetition still indicates contamination.
            row[field_name] = ""
            report.duplicate_noise[field_name] += 1
            report.changed_fields[field_name] += 1
            if field_name == "lab_url":
                row["lab_url_status"] = "invalid"
            if field_name == "lab_name_kor":
                professor = clean_text(row.get("professor_name", ""))
                row["lab_name_kor"] = f"{professor} 교수 연구실" if professor else ""


def clean_all_labs(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], CleanReport]:
    originals = {clean_text(row.get("lab_id", "")): dict(row) for row in rows}
    report = CleanReport()
    cleaned = [clean_existing_lab_row(row, report) for row in rows]
    remove_duplicate_lab_urls(cleaned, report)
    remove_duplicate_profile_images(cleaned, report)
    remove_professor_name_keywords(cleaned, report)
    remove_cross_department_contamination(cleaned, report)
    for row in cleaned:
        row["data_quality_status"] = data_quality_status(row)
        row["enricher_version"] = ENRICHER_VERSION

    # Recompute final change counts from the actual output. Earlier stages may
    # touch the same field more than once, so incremental counters can overcount.
    final_changed_fields: Counter[str] = Counter()
    final_changed_rows = 0
    for row in cleaned:
        lab_id = clean_text(row.get("lab_id", ""))
        original = originals.get(lab_id, {})
        row_changed = False
        for field_name in set(original) | set(row):
            if clean_text(original.get(field_name, "")) != clean_text(row.get(field_name, "")):
                final_changed_fields[field_name] += 1
                row_changed = True
        if row_changed:
            final_changed_rows += 1
    report.changed_fields = final_changed_fields
    report.changed_rows = final_changed_rows
    return cleaned, report


# ============================================================
# 6. Discovery
# ============================================================
def korean_notice_term_present(text: str) -> bool:
    return bool(NOTICE_BOUNDARY_RE.search(clean_text(text)))


def page_link_score(anchor_text: str, href: str) -> int:
    text = clean_text(anchor_text).casefold()
    href_low = href.casefold()
    haystack = f"{text} {href_low}"
    score = 0
    for term in FACULTY_LINK_TERMS:
        if term.casefold() in haystack:
            score += 7
    for term in RESEARCH_LINK_TERMS:
        if term.casefold() in haystack:
            score += 3
    for term in EXCLUDE_LINK_TERMS:
        if term.casefold() in haystack:
            score -= 7
    if korean_notice_term_present(haystack):
        score -= 7
    if re.search(r"(?:faculty|professor|people|member|교수|구성원)", href, re.I):
        score += 5
    if "bo_table" in href_low and any(term in text for term in ("교수", "faculty", "professor")):
        score += 7
    if href_low.endswith((".pdf", ".zip", ".hwp", ".doc", ".docx", ".xls", ".xlsx")):
        score -= 100
    return score


def page_content_score(soup: BeautifulSoup, known_names: Optional[set[str]] = None) -> int:
    text = clean_text(soup.get_text(" ", strip=True))
    low = text.casefold()
    score = min(len(set(normalize_email(x) for x in EMAIL_RE.findall(text))), 15) * 3
    score += sum(3 for term in FACULTY_LINK_TERMS if term.casefold() in low)
    score += sum(1 for term in RESEARCH_LINK_TERMS if term.casefold() in low)
    if known_names:
        normalized_page = normalize_name(text)
        score += min(sum(1 for name in known_names if name and name in normalized_page), 12) * 2
    return score


def faculty_identity_counts(
    soup: BeautifulSoup,
    known_names: Optional[set[str]] = None,
) -> tuple[int, int]:
    text = clean_text(soup.get_text(" ", strip=True))
    email_count = len({normalize_email(x) for x in EMAIL_RE.findall(text) if normalize_email(x)})
    name_count = 0
    if known_names:
        normalized_page = normalize_name(text)
        name_count = sum(1 for name in known_names if name and name in normalized_page)
    return email_count, name_count


def is_faculty_hub_page(soup: BeautifulSoup, known_names: Optional[set[str]] = None) -> bool:
    email_count, name_count = faculty_identity_counts(soup, known_names)
    text = clean_text(soup.get_text(" ", strip=True)).casefold()
    faculty_context = any(term.casefold() in text for term in FACULTY_LINK_TERMS)
    return (email_count >= 2) or (name_count >= 2) or (faculty_context and (email_count + name_count) >= 1)


def is_pagination_link(anchor: Tag, current_url: str, href: str) -> bool:
    if not href or not same_site(current_url, href):
        return False
    text = clean_text(anchor.get_text(" ", strip=True))
    rel = " ".join(clean_text(x) for x in anchor.get("rel", []))
    if rel.casefold() in {"next", "prev", "previous"}:
        return True
    if text and PAGINATION_TEXT_RE.fullmatch(text):
        current = urlparse(current_url)
        target = urlparse(href)
        if current.path == target.path:
            target_query = parse_qs(target.query)
            if any(key in target_query for key in ("page", "present_page_num", "offset", "article.offset")):
                return True
    return False


def is_profile_detail_link(
    anchor: Tag,
    href: str,
    known_names: Optional[set[str]] = None,
) -> bool:
    if not href:
        return False
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if PROFILE_DETAIL_PATH_RE.search(parsed.path):
        return True
    if any(key in query for key in PROFILE_DETAIL_QUERY_KEYS):
        haystack = f"{clean_text(anchor.get_text(' ', strip=True))} {parsed.path} {parsed.query}".casefold()
        if any(token in haystack for token in PROFILE_PATH_HINTS):
            return True
        # Many official board-style faculty pages use only wr_id/idx plus a professor name.
        if known_names:
            normalized_anchor = normalize_name(anchor.get_text(" ", strip=True))
            if any(name and name in normalized_anchor for name in known_names):
                return True
    return False


def iter_iframe_urls(soup: BeautifulSoup, page_url: str) -> Iterator[str]:
    for frame in soup.find_all(("iframe", "frame")):
        src = absolute_url(page_url, frame.get("src", ""))
        if src:
            yield src


def default_candidate_urls(department: dict[str, str]) -> list[str]:
    homepage = normalize_url(department.get("homepage_url", ""))
    department_name = clean_text(department.get("department_name_kor", ""))
    result = list(DEFAULT_FACULTY_URLS_BY_NAME.get(department_name, []))
    if homepage:
        parsed = urlparse(homepage)
        origin = f"{parsed.scheme}://{parsed.netloc}/"
        for path in COMMON_FACULTY_PATHS:
            result.append(normalize_url(urljoin(origin, path)))
    return unique_preserve_order([x for x in result if x])


def save_raw_html(paths: RuntimePaths, department_id: str, page_index: int, result: PageResult, enabled: bool) -> None:
    if not enabled:
        return
    folder = paths.raw / (department_id or "UNKNOWN")
    folder.mkdir(parents=True, exist_ok=True)
    host = re.sub(r"[^0-9A-Za-z._-]", "_", hostname(result.url))
    path = folder / f"{page_index:02d}_{host}_{stable_id('P', result.url, length=8)}.html"
    path.write_text(result.html, encoding="utf-8")


def resolve_department_override(overrides: dict, department: dict[str, str]) -> dict:
    candidates = (
        clean_text(department.get("department_id", "")),
        clean_text(department.get("department_name_kor", "")),
        clean_text(department.get("department_name_eng", "")),
    )
    for key in candidates:
        value = overrides.get(key)
        if isinstance(value, dict):
            return value
    return {}


def discover_department_pages(
    client: RespectfulClient,
    department: dict[str, str],
    override: dict,
    max_pages: int,
    max_depth: int,
    known_names: set[str],
    paths: RuntimePaths,
    save_raw: bool,
) -> list[PageResult]:
    homepage = normalize_url(department.get("homepage_url", ""))
    forced_urls = [normalize_url(x) for x in override.get("faculty_urls", []) if normalize_url(x)]
    candidate_urls = default_candidate_urls(department)
    named_candidate_urls = {
        normalize_url(url)
        for url in DEFAULT_FACULTY_URLS_BY_NAME.get(
            clean_text(department.get("department_name_kor", "")), []
        )
        if normalize_url(url)
    }
    if not homepage and not forced_urls and not candidate_urls:
        return []

    queue: list[tuple[int, int, str]] = []
    visited: set[str] = set()
    queued: set[str] = set()
    results: list[PageResult] = []
    forced_set = set(forced_urls)

    allowed_hosts = {hostname(homepage)} if homepage else set()
    allowed_hosts.update(hostname(url) for url in forced_urls)
    allowed_hosts.update(hostname(url) for url in candidate_urls)
    allowed_hosts.update(clean_text(x).lower() for x in override.get("allowed_hosts", []) if clean_text(x))
    allowed_hosts.discard("")

    def host_allowed(url: str) -> bool:
        host = hostname(url)
        if not host:
            return False
        normalized_host = host.removeprefix("www.")
        for allowed in allowed_hosts:
            allowed = clean_text(allowed).lower()
            if not allowed:
                continue
            if allowed.startswith("*."):
                base = allowed[2:].removeprefix("www.")
                if normalized_host == base or normalized_host.endswith("." + base):
                    return True
            elif normalized_host == allowed.removeprefix("www."):
                return True
        return False

    def push(url: str, score: int, depth: int) -> None:
        url = normalize_url(url)
        if not url or url in visited or url in queued or not host_allowed(url):
            return
        queued.add(url)
        heapq.heappush(queue, (-score, depth, url))

    for url in forced_urls:
        push(url, 2000, 0)
    if homepage:
        push(homepage, 500, 0)
    for url in candidate_urls:
        push(url, 900 if url in named_candidate_urls else 50, 1)

    local_max_depth = int(override.get("max_depth", max_depth))
    attempts = 0
    max_attempts = max(max_pages * 6, max_pages + 12)

    while queue and len(results) < max_pages and attempts < max_attempts:
        neg_score, depth, url = heapq.heappop(queue)
        attempts += 1
        queued.discard(url)
        if url in visited:
            continue
        visited.add(url)

        try:
            force_browser = bool(override.get("render", False)) and url in forced_set
            result = client.fetch(url, force_browser=force_browser)
        except Exception as exc:
            append_jsonl(
                paths.log,
                {
                    "timestamp": now_iso(),
                    "level": "warning",
                    "department_id": department.get("department_id", ""),
                    "department_type": department.get("department_type", ""),
                    "department": department.get("department_name_kor", ""),
                    "url": url,
                    "message": str(exc),
                    "enricher_version": ENRICHER_VERSION,
                },
            )
            continue

        results.append(result)
        save_raw_html(paths, department.get("department_id", "UNKNOWN"), len(results), result, save_raw)
        soup = result.soup
        content_score = page_content_score(soup, known_names)
        print(
            f"    [PAGE] {len(results):02d}/{max_pages:02d} | "
            f"내용점수={content_score:02d} | {result.method} | {result.url}"
        )

        if depth >= local_max_depth:
            continue

        for iframe_url in iter_iframe_urls(soup, result.url):
            if host_allowed(iframe_url):
                push(iframe_url, 900, depth + 1)

        faculty_hub = is_faculty_hub_page(soup, known_names)
        for anchor in soup.find_all("a"):
            href = anchor_target_url(result.url, anchor)
            if not href or not host_allowed(href):
                continue
            score = page_link_score(anchor.get_text(" ", strip=True), href)
            if faculty_hub and is_profile_detail_link(anchor, href, known_names):
                score = max(score, 24)
            elif faculty_hub and is_pagination_link(anchor, result.url, href):
                score = max(score, 18)
            if score >= 3:
                push(href, score, depth + 1)

    return results


# ============================================================
# 7. Faculty-card matching
# ============================================================
def node_lines(node: Tag) -> list[str]:
    return [clean_text(x) for x in node.stripped_strings if clean_text(x)]


def node_emails(node: Tag) -> set[str]:
    return {normalize_email(x) for x in EMAIL_RE.findall(node.get_text(" ", strip=True)) if normalize_email(x)}


def class_hint_score(node: Tag) -> int:
    attrs = " ".join(
        [node.name or "", clean_text(node.get("id", ""))]
        + [clean_text(x) for x in node.get("class", [])]
    ).casefold()
    return sum(1 for hint in CARD_CLASS_HINTS if hint.casefold() in attrs)


def visible_identity_count(text: str, normalized_known_names: set[str]) -> int:
    normalized = normalize_name(text)
    return sum(1 for name in normalized_known_names if name and name in normalized)


def find_person_container(
    node: Tag,
    person_name: str,
    email: str,
    normalized_known_names: set[str],
) -> Tag:
    current: Optional[Tag] = node if isinstance(node, Tag) else node.parent
    candidates: list[tuple[int, int, Tag]] = []
    normalized_person = normalize_name(person_name)
    normalized_email = normalize_email(email)

    for depth in range(8):
        if not isinstance(current, Tag):
            break
        text = clean_text(current.get_text(" ", strip=True))
        text_len = len(text)
        if text_len > 4500:
            break
        emails = node_emails(current)
        identity_count = visible_identity_count(text, normalized_known_names)
        has_identity = (
            (normalized_email and normalized_email in emails)
            or (normalized_person and normalized_person in normalize_name(text))
        )
        if has_identity and 20 <= text_len <= 3500 and len(emails) <= 2 and identity_count <= 2:
            semantic = class_hint_score(current)
            structural = 3 if current.name in {"li", "tr", "article"} else 1 if current.name in {"section", "div"} else 0
            score = semantic * 5 + structural * 3 - depth - max(0, identity_count - 1) * 4
            candidates.append((score, -text_len, current))
        current = current.parent

    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]
    return node if isinstance(node, Tag) else node.parent


def find_email_nodes(soup: BeautifulSoup) -> dict[str, Tag]:
    found: dict[str, Tag] = {}
    for anchor in soup.find_all("a"):
        href = clean_text(anchor.get("href", ""))
        if href.casefold().startswith("mailto:"):
            email = normalize_email(href)
            if email:
                found[email] = anchor
    for text_node in soup.find_all(string=EMAIL_RE):
        if not isinstance(text_node, NavigableString) or not isinstance(text_node.parent, Tag):
            continue
        for email in EMAIL_RE.findall(str(text_node)):
            normalized = normalize_email(email)
            found.setdefault(normalized, text_node.parent)
    return found


def find_name_node(soup: BeautifulSoup, name: str) -> Optional[Tag]:
    if not clean_text(name):
        return None
    pattern = re.compile(rf"(?<![가-힣A-Za-z]){re.escape(clean_text(name))}(?:\s*교수)?(?![가-힣A-Za-z])")
    for text_node in soup.find_all(string=pattern):
        if isinstance(text_node, NavigableString) and isinstance(text_node.parent, Tag):
            return text_node.parent
    return None


def override_card_nodes(soup: BeautifulSoup, override: dict) -> list[Tag]:
    selectors = override.get("faculty_card_selectors", [])
    if isinstance(selectors, str):
        selectors = [selectors]
    result: list[Tag] = []
    for selector in selectors:
        try:
            result.extend(node for node in soup.select(selector) if isinstance(node, Tag))
        except Exception:
            continue
    return result


def card_candidate_names(card: Tag, name_selectors: Sequence[str]) -> list[str]:
    names = selector_values(card, name_selectors) if name_selectors else []
    if not names:
        for selector in ("h1", "h2", "h3", "h4", ".name", ".title", "strong", "b"):
            try:
                for node in card.select(selector):
                    value = clean_text(node.get_text(" ", strip=True))
                    if 2 <= len(value) <= 80:
                        names.append(value)
            except Exception:
                continue
    return unique_preserve_order(names)


def card_candidate_emails(card: Tag, email_selectors: Sequence[str]) -> set[str]:
    emails = set(node_emails(card))
    for value in selector_values(card, email_selectors):
        email = normalize_email(value)
        if email:
            emails.add(email)
    return emails


def extract_professor_name_from_card(block: Tag, current: dict[str, str], override: dict) -> str:
    department_name = current.get("department_name", "")
    current_name = clean_professor_name(current.get("professor_name", ""), department_name)
    selectors = override.get("name_selectors", [])
    if isinstance(selectors, str):
        selectors = [selectors]
    candidates = selector_values(block, selectors)
    candidates.extend(card_candidate_names(block, []))
    candidates.extend(node_lines(block)[:8])
    for candidate in unique_preserve_order(candidates):
        cleaned = clean_professor_name(candidate, department_name)
        if not cleaned:
            continue
        if current_name and normalize_name(cleaned) != normalize_name(current_name):
            continue
        return cleaned
    return ""


def build_page_matches(
    result: PageResult,
    override: dict,
    labs_by_id: dict[str, dict[str, str]],
    labs_by_email: dict[str, str],
    eligible_name_to_lab_id: dict[str, str],
    normalized_known_names: set[str],
) -> list[MatchResult]:
    soup = result.soup
    matches: dict[str, MatchResult] = {}

    cards = override_card_nodes(soup, override)
    name_selectors = override.get("name_selectors", [])
    email_selectors = override.get("email_selectors", [])
    if isinstance(name_selectors, str):
        name_selectors = [name_selectors]
    if isinstance(email_selectors, str):
        email_selectors = [email_selectors]

    for card in cards:
        emails = card_candidate_emails(card, email_selectors)
        matched_lab_id = next((labs_by_email[email] for email in emails if email in labs_by_email), "")
        method = "email_selector" if matched_lab_id else ""
        if not matched_lab_id:
            for candidate in card_candidate_names(card, name_selectors):
                normalized = normalize_name(candidate)
                if normalized in eligible_name_to_lab_id:
                    matched_lab_id = eligible_name_to_lab_id[normalized]
                    method = "name_unique_selector"
                    break
        if matched_lab_id:
            matches[matched_lab_id] = MatchResult(matched_lab_id, card, method, result.url)

    email_nodes = find_email_nodes(soup)
    for email, node in email_nodes.items():
        lab_id = labs_by_email.get(email)
        if not lab_id or lab_id in matches:
            continue
        lab = labs_by_id[lab_id]
        block = find_person_container(
            node,
            lab.get("professor_name", ""),
            email,
            normalized_known_names,
        )
        matches[lab_id] = MatchResult(lab_id, block, "email", result.url)

    # Name-only matching is allowed only when the normalized professor name is
    # globally unique in labs.csv. This avoids automatic matching of homonyms.
    page_text = clean_text(soup.get_text(" ", strip=True))
    normalized_page_text = normalize_name(page_text)
    for normalized_name, lab_id in eligible_name_to_lab_id.items():
        if not normalized_name or normalized_name not in normalized_page_text or lab_id in matches:
            continue
        lab = labs_by_id[lab_id]
        name = clean_text(lab.get("professor_name", ""))
        node = find_name_node(soup, name)
        if node is None:
            continue
        block = find_person_container(node, name, lab.get("email", ""), normalized_known_names)
        block_text = clean_text(block.get_text(" ", strip=True))
        block_low = block_text.casefold()
        identity_context = any(
            token in block_low
            for token in ("교수", "professor", "research", "연구", "faculty", "전문 분야", "연구분야")
        )
        if not identity_context or visible_identity_count(block_text, normalized_known_names) > 2:
            continue
        matches[lab_id] = MatchResult(lab_id, block, "name_unique", result.url)

    return list(matches.values())


# ============================================================
# 8. Card extraction
# ============================================================
def extract_labeled_text(lines: list[str], labels: tuple[str, ...], max_following: int = 3) -> str:
    ordered_labels = sorted((clean_text(label) for label in labels), key=len, reverse=True)
    for index, line in enumerate(lines):
        normalized_line = clean_text(line)
        for label in ordered_labels:
            if normalized_line.casefold() == label.casefold() and index + 1 < len(lines):
                values: list[str] = []
                for follow in lines[index + 1 : index + 1 + max_following]:
                    follow_low = follow.casefold()
                    if any(follow_low.startswith(stop.casefold()) for stop in CONTACT_STOP_LABELS):
                        break
                    if EMAIL_RE.search(follow) or PHONE_RE.search(follow):
                        break
                    if 2 <= len(follow) <= 500:
                        values.append(follow)
                return "; ".join(values)
            match = re.match(rf"^\s*{re.escape(label)}\s*[:：-]?\s*(?P<value>.+?)\s*$", normalized_line, re.I)
            if match:
                return clean_text(match.group("value"))
    return ""


def extract_location(lines: list[str], selector_value: str = "") -> str:
    if selector_value:
        cleaned = clean_location_value(selector_value)
        if cleaned:
            return cleaned
    labeled = clean_location_value(extract_labeled_text(lines, LOCATION_LABELS, max_following=1))
    if labeled:
        return labeled
    for line in lines:
        cleaned = clean_location_value(line)
        if cleaned:
            return cleaned
    return ""


def candidate_lab_name_from_lines(lines: list[str], professor_name: str) -> str:
    candidates: list[str] = []
    professor_normalized = normalize_name(professor_name)
    for line in lines:
        if professor_normalized and normalize_name(line) == professor_normalized:
            continue
        for match in LAB_NAME_RE.finditer(line):
            candidate = clean_text(match.group(0))
            if is_probable_lab_name(candidate):
                candidates.append(candidate)
    candidates = unique_preserve_order(candidates)
    candidates.sort(key=lambda x: (not any(token in x.casefold() for token in ("lab", "laboratory", "연구실")), len(x)))
    return candidates[0] if candidates else ""


def anchor_url_score(anchor: Tag, page_url: str, professor_name: str, professor_profile_url: str) -> tuple[int, str]:
    href = anchor_target_url(page_url, anchor)
    if not href or is_forbidden_lab_url(href, professor_profile_url):
        return -999, "invalid"
    text = clean_text(anchor.get_text(" ", strip=True)).casefold()
    aria = clean_text(anchor.get("aria-label", "")).casefold()
    title = clean_text(anchor.get("title", "")).casefold()
    haystack = f"{text} {aria} {title} {href.casefold()}"

    score = 0
    status = "candidate_card"
    if any(label.casefold() in haystack for label in HOMEPAGE_LABELS_STRONG):
        score += 30
        status = "verified_card"
    elif any(label.casefold() in haystack for label in HOMEPAGE_LABELS_WEAK):
        score += 12

    if any(token in haystack for token in LAB_PATH_HINTS):
        score += 10
    if not same_site(href, page_url):
        score += 5
    if professor_name and normalize_name(professor_name) in normalize_name(text):
        score += 2
    if url_query_has_board(href):
        score -= 12 if status == "verified_card" else 30
    if any(token in haystack for token in PROFILE_PATH_HINTS) and not any(token in haystack for token in LAB_PATH_HINTS):
        score -= 25
    return score, status


def extract_lab_url(
    block: Tag,
    page_url: str,
    professor_name: str,
    professor_profile_url: str,
    override: dict,
) -> tuple[str, str]:
    candidates: list[tuple[int, int, str, str]] = []
    selectors = override.get("lab_link_selectors", [])
    if isinstance(selectors, str):
        selectors = [selectors]

    selected_anchors: list[Tag] = []
    for selector in selectors:
        try:
            selected_anchors.extend(node for node in block.select(selector) if isinstance(node, Tag))
        except Exception:
            continue

    all_anchors = unique_tag_list(selected_anchors + list(block.find_all("a")))
    selected_ids = {id(anchor) for anchor in selected_anchors}
    for anchor in all_anchors:
        href = anchor_target_url(page_url, anchor)
        score, status = anchor_url_score(anchor, page_url, professor_name, professor_profile_url)
        if id(anchor) in selected_ids:
            score += 20
            if score > 0:
                status = "verified_card"
        if score > 0 and href:
            candidates.append((score, -len(href), href, status))

    if not candidates:
        return "", "unverified"
    candidates.sort(reverse=True)
    _, _, url, status = candidates[0]
    return url, status


def unique_tag_list(nodes: Sequence[Tag]) -> list[Tag]:
    result: list[Tag] = []
    seen: set[int] = set()
    for node in nodes:
        if id(node) not in seen:
            seen.add(id(node))
            result.append(node)
    return result


def extract_image_url(block: Tag, page_url: str, professor_name: str, override: dict) -> str:
    selectors = override.get("image_selectors", [])
    if isinstance(selectors, str):
        selectors = [selectors]
    images: list[Tag] = []
    for selector in selectors:
        try:
            images.extend(node for node in block.select(selector) if isinstance(node, Tag))
        except Exception:
            continue
    images.extend(block.find_all("img"))

    scored: list[tuple[int, str]] = []
    for image in unique_tag_list(images):
        raw = image.get("src") or image.get("data-src") or image.get("data-original") or ""
        src = absolute_url(page_url, raw)
        if not valid_image_url(src):
            continue
        alt = clean_text(image.get("alt", ""))
        score = 1
        if professor_name and normalize_name(professor_name) in normalize_name(alt):
            score += 5
        if any(token in src.casefold() for token in ("prof", "faculty", "member", "people")):
            score += 2
        scored.append((score, src))
    scored.sort(reverse=True)
    return scored[0][1] if scored else ""


def extract_primary_field(lines: list[str], selector_value: str = "") -> str:
    value = selector_value or extract_labeled_text(lines, FIELD_LABELS, max_following=4)
    value = re.sub(r"^(?:분야|area|field)\s*[:：-]?\s*", "", value, flags=re.I)
    return clean_primary_field_value(value)


def keyword_phrases(*texts: str, limit: int = MAX_KEYWORDS) -> str:
    raw = ";".join(text for text in texts if text)
    return ";".join(split_multi(clean_keywords_value(raw))[:limit])


def line_is_summary_candidate(line: str) -> bool:
    text = clean_text(line)
    low = text.casefold()
    if not (30 <= len(text) <= MAX_SUMMARY_CHARS):
        return False
    if EMAIL_RE.search(text) or PHONE_RE.search(text) or summary_has_news_noise(text):
        return False
    if contains_noise_phrase(text):
        return False
    return any(token in low for token in ("연구", "focus", "research", "develop", "investigate", "study", "explore"))


def extract_research_summary(lines: list[str], selector_values_list: Sequence[str], primary_field: str) -> str:
    for value in selector_values_list:
        cleaned = clean_summary_value(value)
        if cleaned:
            return cleaned
    candidates = [clean_text(line) for line in lines if line_is_summary_candidate(line)]
    if candidates:
        candidates.sort(key=lambda value: (len(value) < 80, -len(value)))
        return clean_summary_value(candidates[0])
    return f"주요 연구 분야: {primary_field}" if primary_field else ""


def explicit_selector_first(block: Tag, selectors: object, attr: Optional[str] = None) -> str:
    if isinstance(selectors, str):
        selectors = [selectors]
    if not isinstance(selectors, list):
        return ""
    values = selector_values(block, selectors, attr=attr)
    return values[0] if values else ""


def extract_card_data(block: Tag, page_url: str, lab: dict[str, str], override: dict) -> dict[str, str]:
    lines = node_lines(block)
    professor_name = extract_professor_name_from_card(block, lab, override)
    primary_field = extract_primary_field(lines, explicit_selector_first(block, override.get("field_selectors", [])))

    identity_name = professor_name or lab.get("professor_name", "")
    lab_name = explicit_selector_first(block, override.get("lab_name_selectors", []))
    lab_name = clean_lab_name(lab_name, identity_name) or candidate_lab_name_from_lines(
        lines, identity_name
    )

    lab_url, lab_url_status = extract_lab_url(
        block,
        page_url,
        identity_name,
        lab.get("professor_profile_url", ""),
        override,
    )

    location = extract_location(lines, explicit_selector_first(block, override.get("location_selectors", [])))
    phone = canonical_phone(explicit_selector_first(block, override.get("phone_selectors", [])) or " ".join(lines))
    image_url = extract_image_url(block, page_url, identity_name, override)
    summary_selector_values = selector_values(
        block,
        override.get("summary_selectors", []) if isinstance(override.get("summary_selectors", []), list) else [override.get("summary_selectors", "")],
    )
    summary = extract_research_summary(lines, summary_selector_values, primary_field)

    keywords = keyword_phrases(
        primary_field,
        explicit_selector_first(block, override.get("keyword_selectors", [])),
    )

    return {
        "professor_name": professor_name,
        "lab_name_kor": lab_name,
        "lab_url": lab_url,
        "lab_url_status": lab_url_status,
        "location": location,
        "phone": phone,
        "profile_image_url": image_url,
        "primary_field": primary_field,
        "research_summary": summary,
        "keywords": keywords,
        "keyword_source": "department_page" if keywords else "",
        "department_page_url": page_url,
        "enrichment_source_urls": page_url,
    }


# ============================================================
# 9. Lab-homepage validation and enrichment
# ============================================================
def meta_content(soup: BeautifulSoup, names: tuple[str, ...]) -> str:
    for name in names:
        for attr_name in ("name", "property"):
            tag = soup.find("meta", attrs={attr_name: re.compile(rf"^{re.escape(name)}$", re.I)})
            if tag and tag.get("content"):
                return clean_text(tag.get("content"))
    return ""


def extract_homepage_lab_name(soup: BeautifulSoup) -> str:
    candidates: list[str] = []
    for selector in ("h1", "header h2", ".site-title", ".site_name", ".logo", "title"):
        try:
            nodes = soup.select(selector)
        except Exception:
            continue
        for node in nodes:
            text = strip_site_suffix(node.get_text(" ", strip=True))
            if is_probable_lab_name(text):
                candidates.append(text)
    candidates = unique_preserve_order(candidates)
    candidates.sort(key=len)
    return candidates[0] if candidates else ""


def extract_homepage_summary(soup: BeautifulSoup) -> str:
    description = clean_summary_value(meta_content(soup, ("description", "og:description", "twitter:description")))
    if description and any(token in description.casefold() for token in ("research", "연구", "laboratory", "lab", "science", "engineering")):
        return description

    candidates: list[str] = []
    for selector in ("main p", "article p", ".about p", ".research p", "#about p", "#research p"):
        try:
            paragraphs = soup.select(selector)
        except Exception:
            continue
        for paragraph in paragraphs:
            text = clean_summary_value(paragraph.get_text(" ", strip=True))
            if text and any(token in text.casefold() for token in ("research", "연구", "develop", "focus", "investigate", "study")):
                candidates.append(text)
    candidates = unique_preserve_order(candidates)
    candidates.sort(key=lambda x: (len(x) < 80, -len(x)))
    return candidates[0] if candidates else ""


def detect_recruiting_status(text: str) -> str:
    low = clean_text(text).casefold()
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
        "상시 모집",
    )
    if any(pattern in low for pattern in negative_patterns):
        return "closed"
    if any(pattern in low for pattern in positive_patterns):
        return "open"
    return "unknown"


def homepage_identity_score(
    soup: BeautifulSoup,
    lab: dict[str, str],
) -> tuple[int, bool, bool]:
    text = clean_text(soup.get_text(" ", strip=True))
    low = text.casefold()
    score = 0
    professor_name = normalize_name(lab.get("professor_name", ""))
    email = normalize_email(lab.get("email", ""))
    page_emails = {normalize_email(x) for x in EMAIL_RE.findall(text) if normalize_email(x)}
    email_exact = bool(email and email in page_emails)
    name_exact = bool(professor_name and professor_name in normalize_name(text))

    unrelated_postech_emails = {
        page_email for page_email in page_emails
        if page_email.endswith("@postech.ac.kr") and page_email != email
    }
    identity_conflict = bool(unrelated_postech_emails and not email_exact and not name_exact)

    if name_exact:
        score += 5
    if email_exact:
        score += 10

    homepage_name = extract_homepage_lab_name(soup)
    if homepage_name:
        score += 3
        current_lab_name = clean_lab_name(lab.get("lab_name_kor", ""), lab.get("professor_name", ""))
        if current_lab_name and normalize_name(current_lab_name) in normalize_name(homepage_name):
            score += 4

    if any(token in low for token in ("laboratory", " lab ", "research group", "연구실")):
        score += 2
    if any(token in low for token in ("research", "연구")):
        score += 2
    if unrelated_postech_emails and not email_exact:
        score -= min(4, len(unrelated_postech_emails))
    return max(score, 0), email_exact, identity_conflict


def extract_homepage_professor_name(
    soup: BeautifulSoup,
    lab: dict[str, str],
) -> str:
    """Recover a missing professor name from a personal/lab homepage.

    The candidate must agree with the email local-part or appear on a page
    containing the exact professor email. This is deliberately conservative.
    """
    current = clean_professor_name(
        lab.get("professor_name", ""),
        lab.get("department_name", ""),
    )
    if current:
        return ""

    email = normalize_email(lab.get("email", ""))
    email_local = re.sub(r"[^a-z0-9가-힣]", "", email.split("@", 1)[0].casefold()) if email else ""
    page_text = clean_text(soup.get_text(" ", strip=True))
    email_exact = bool(email and email in {normalize_email(x) for x in EMAIL_RE.findall(page_text)})

    candidates: list[str] = []
    candidates.extend(
        [
            meta_content(soup, ("author", "og:title", "twitter:title")),
        ]
    )
    for selector in (
        "title",
        "h1",
        "header h2",
        ".professor-name",
        ".faculty-name",
        ".member-name",
        ".pi-name",
        ".name",
    ):
        try:
            candidates.extend(node.get_text(" ", strip=True) for node in soup.select(selector))
        except Exception:
            continue

    for raw in unique_preserve_order(candidates):
        candidate = strip_site_suffix(raw)
        candidate = re.sub(
            r"(?i)\b(?:homepage|home page|website|laboratory|research group|lab)\b",
            " ",
            candidate,
        )
        candidate = clean_text(candidate).strip("-|·–—")
        if re.search(r"(?i)(?:department|postech|연구실|연구그룹|연구센터)", candidate):
            continue
        cleaned = clean_professor_name(candidate, lab.get("department_name", ""))
        if not cleaned:
            continue
        normalized = normalize_name(cleaned)
        local_match = bool(
            email_local
            and len(email_local) >= 5
            and (email_local in normalized or normalized.endswith(email_local))
        )
        if local_match or email_exact:
            return cleaned
    return ""


def split_homepage_lab_name(name: str) -> tuple[str, str]:
    cleaned = clean_text(name)
    if not cleaned:
        return "", ""
    has_korean = bool(re.search(r"[가-힣]", cleaned))
    has_english = bool(re.search(r"[A-Za-z]", cleaned))
    english_name = cleaned if has_english and not has_korean else ""
    return cleaned, english_name


def enrich_from_lab_homepage(client: RespectfulClient, lab: dict[str, str]) -> dict[str, str]:
    lab_url = normalize_url(lab.get("lab_url", ""))
    if not lab_url or is_forbidden_lab_url(lab_url, lab.get("professor_profile_url", "")):
        return {"lab_url_status": "invalid"}

    result = client.fetch(lab_url)
    soup = result.soup
    homepage_professor_name = extract_homepage_professor_name(soup, lab)
    identity_lab = dict(lab)
    if homepage_professor_name and not clean_text(identity_lab.get("professor_name", "")):
        identity_lab["professor_name"] = homepage_professor_name

    identity_score, email_exact, identity_conflict = homepage_identity_score(soup, identity_lab)
    identity_update = {"professor_name": homepage_professor_name} if homepage_professor_name else {}
    if identity_conflict:
        return {
            **identity_update,
            "lab_url": "",
            "lab_url_status": "invalid",
            "enrichment_source_urls": result.url,
        }
    if identity_score < 8 or (not email_exact and identity_score < 10):
        # Insufficient evidence is not the same as a confirmed mismatch. Keep
        # the URL as a reviewable candidate, but do not expose it as verified.
        return {
            **identity_update,
            "lab_url": result.url,
            "lab_url_status": "candidate_card",
            "enrichment_source_urls": result.url,
        }

    page_text = clean_text(soup.get_text(" ", strip=True))
    homepage_name = extract_homepage_lab_name(soup)
    lab_name_kor, lab_name_eng = split_homepage_lab_name(homepage_name)
    summary = extract_homepage_summary(soup)
    meta_keywords = meta_content(soup, ("keywords",))
    lines = [clean_text(x) for x in soup.stripped_strings if clean_text(x)]
    location = extract_location(lines)

    return {
        **identity_update,
        "lab_name_kor": lab_name_kor,
        "lab_name_eng": lab_name_eng,
        "research_summary": summary,
        "keywords": keyword_phrases(lab.get("primary_field", ""), meta_keywords, summary),
        "keyword_source": "lab_homepage" if (meta_keywords or summary) else "",
        "location": location,
        "recruiting_status": detect_recruiting_status(page_text),
        "lab_url": result.url,
        "lab_url_status": "verified_homepage",
        "enrichment_source_urls": result.url,
    }


# ============================================================
# 10. Merge and quality rules
# ============================================================
def text_quality(field_name: str, value: str, row: Optional[dict[str, str]] = None) -> int:
    text = clean_text(value)
    if not text:
        return 0
    if field_name == "professor_name":
        return professor_name_quality(text, (row or {}).get("department_name", ""))
    if field_name == "lab_name_kor":
        if looks_placeholder_lab_name(text):
            return 1
        return 10 if is_probable_lab_name(text) else 0
    if field_name == "lab_url":
        if not normalize_url(text) or is_forbidden_lab_url(text, (row or {}).get("professor_profile_url", "")):
            return 0
        return 5 + lab_url_status_rank((row or {}).get("lab_url_status", ""))
    if field_name == "primary_field":
        return 8 if clean_primary_field_value(text) == text and 3 <= len(text) <= MAX_PRIMARY_FIELD_CHARS else 0
    if field_name == "research_summary":
        cleaned = clean_summary_value(text)
        return min(10, 3 + len(cleaned) // 100) if cleaned else 0
    if field_name == "keywords":
        return min(8, len(split_multi(clean_keywords_value(text))))
    if field_name == "location":
        return 6 if clean_location_value(text) else 0
    if field_name == "profile_image_url":
        return 4 if valid_image_url(text) else 0
    if field_name == "phone":
        return 4 if canonical_phone(text) else 0
    if field_name == "recruiting_status":
        return 3 if text in {"open", "closed", "always_open"} else 1 if text == "unknown" else 0
    if field_name == "department_page_url":
        return 2 if normalize_url(text) else 0
    if field_name == "keyword_source":
        return {"lab_homepage": 3, "department_page": 2, "manual": 4}.get(text, 1)
    return 1


def sanitize_update(update: dict[str, str], current: dict[str, str]) -> dict[str, str]:
    result = dict(update)
    result["professor_name"] = clean_professor_name(
        result.get("professor_name", ""),
        current.get("department_name", "") or current.get("department_name_raw", ""),
    )
    professor_for_name = result.get("professor_name", "") or current.get("professor_name", "")
    result["lab_name_kor"] = clean_lab_name(result.get("lab_name_kor", ""), professor_for_name)
    result["location"] = clean_location_value(result.get("location", ""))
    result["phone"] = canonical_phone(result.get("phone", ""))
    result["primary_field"] = clean_primary_field_value(result.get("primary_field", ""))
    result["research_summary"] = clean_summary_value(result.get("research_summary", ""))
    result["keywords"] = clean_keywords_value(result.get("keywords", ""))
    result["profile_image_url"] = clean_profile_image_url(result.get("profile_image_url", ""))
    result["lab_url"] = normalize_url(result.get("lab_url", ""))
    result["lab_url_status"] = normalize_lab_url_status(result.get("lab_url_status", ""), result.get("lab_url", ""))
    if result.get("lab_url") and is_forbidden_lab_url(result["lab_url"], current.get("professor_profile_url", "")):
        result["lab_url"] = ""
        result["lab_url_status"] = "invalid"
    return result


def merge_lab_update(
    lab: dict[str, str],
    update: dict[str, str],
    affiliation: str,
    manual: bool = False,
) -> tuple[dict[str, str], list[str]]:
    changed: list[str] = []
    merged = dict(lab)
    update = sanitize_update(update, merged)

    if affiliation:
        old = merged.get("affiliated_programs", "") or merged.get("department_name", "")
        new_value = merge_multi(old, affiliation)
        if new_value != clean_text(merged.get("affiliated_programs", "")):
            merged["affiliated_programs"] = new_value
            changed.append("affiliated_programs")

    merge_fields = (
        "professor_name",
        "lab_name_kor",
        "lab_name_eng",
        "location",
        "phone",
        "profile_image_url",
        "primary_field",
        "research_summary",
        "keywords",
        "keyword_source",
        "recruiting_status",
        "department_page_url",
    )

    for field_name in merge_fields:
        incoming = clean_text(update.get(field_name, ""))
        if not incoming:
            continue
        current = clean_text(merged.get(field_name, ""))
        if text_quality(field_name, incoming, {**merged, **update}) > text_quality(field_name, current, merged):
            merged[field_name] = incoming
            changed.append(field_name)
        elif field_name == "keywords":
            combined = merge_multi(current, incoming, limit=MAX_KEYWORDS)
            if combined != current:
                merged[field_name] = combined
                changed.append(field_name)

    incoming_url = clean_text(update.get("lab_url", ""))
    incoming_status = "manual" if manual and incoming_url else clean_text(update.get("lab_url_status", ""))
    current_url = clean_text(merged.get("lab_url", ""))
    current_status = normalize_lab_url_status(merged.get("lab_url_status", ""), current_url)

    should_replace_url = False
    if incoming_url:
        if not current_url:
            should_replace_url = True
        elif incoming_url == current_url and lab_url_status_rank(incoming_status) > lab_url_status_rank(current_status):
            should_replace_url = True
        elif lab_url_status_rank(incoming_status) > lab_url_status_rank(current_status):
            should_replace_url = True
    elif incoming_status == "invalid" and current_url and current_status not in {"manual", "verified_homepage"}:
        should_replace_url = True

    if should_replace_url:
        if incoming_url != current_url:
            merged["lab_url"] = incoming_url
            changed.append("lab_url")
        if incoming_status != current_status:
            merged["lab_url_status"] = incoming_status
            changed.append("lab_url_status")
    elif not merged.get("lab_url_status"):
        merged["lab_url_status"] = current_status

    if clean_text(merged.get("professor_name", "")) and not clean_text(merged.get("lab_name_kor", "")):
        merged["lab_name_kor"] = f"{clean_text(merged['professor_name'])} 교수 연구실"
        changed.append("lab_name_kor")

    source_urls = sanitize_enrichment_source_urls(
        merged,
        (
            update.get("enrichment_source_urls", ""),
            update.get("department_page_url", ""),
        ),
    )
    if source_urls != clean_text(merged.get("enrichment_source_urls", "")):
        merged["enrichment_source_urls"] = source_urls
        changed.append("enrichment_source_urls")

    merged["enricher_version"] = ENRICHER_VERSION
    return merged, list(dict.fromkeys(changed))


def data_quality_status(lab: dict[str, str]) -> str:
    actual_name = not looks_placeholder_lab_name(lab.get("lab_name_kor", "")) and is_probable_lab_name(lab.get("lab_name_kor", ""))
    trusted_url = bool(normalize_url(lab.get("lab_url", ""))) and lab.get("lab_url_status") in TRUSTED_LAB_URL_STATUSES
    has_research = bool(clean_primary_field_value(lab.get("primary_field", "")) or clean_summary_value(lab.get("research_summary", "")))
    has_keywords = len(split_multi(clean_keywords_value(lab.get("keywords", "")))) >= 2
    score = sum((actual_name, trusted_url, has_research, has_keywords))
    if score >= 4:
        return "complete"
    if score >= 2:
        return "partial"
    return "basic_only"


def apply_manual_overrides(labs_by_id: dict[str, dict[str, str]], override_root: dict) -> int:
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
                    if (normalized_key and normalize_email(lab.get("email", "")) == normalized_key)
                    or lab.get("lab_id") == key
                ),
                None,
            )
            if target is None:
                continue
            merged, changed = merge_lab_update(
                target,
                {**values, "enrichment_source_urls": "manual_override", "keyword_source": values.get("keyword_source", "manual")},
                values.get("affiliated_programs", ""),
                manual=True,
            )
            if changed:
                merged["enrichment_status"] = "manual_override"
                merged["enrichment_message"] = "수동 override 적용: " + ", ".join(changed)
                merged["enriched_at"] = now_iso()
                merged["data_quality_status"] = data_quality_status(merged)
                merged["enricher_version"] = ENRICHER_VERSION
                labs_by_id[target["lab_id"]] = merged
                changed_count += 1
    return changed_count


# ============================================================
# 11. Persistence and initialization
# ============================================================
def save_checkpoint(
    paths: RuntimePaths,
    departments: list[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
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
    atomic_write_csv(paths.departments, departments_sorted, department_fields)
    atomic_write_csv(paths.labs, labs_sorted, lab_fields)


def initialize_rows(
    departments: list[dict[str, str]],
    labs: list[dict[str, str]],
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    department_by_id = {
        clean_text(row.get("department_id", "")): row
        for row in departments
        if clean_text(row.get("department_id", ""))
    }
    labs_by_id: dict[str, dict[str, str]] = {}
    for row in labs:
        lab_id = clean_text(row.get("lab_id", ""))
        if not lab_id:
            continue
        primary_department = department_by_id.get(clean_text(row.get("department_id", "")), {})
        row["primary_department_id"] = clean_text(row.get("primary_department_id", "") or row.get("department_id", ""))
        row["department_type"] = clean_text(row.get("department_type", "") or primary_department.get("department_type", ""))
        row["affiliated_programs"] = merge_multi(row.get("affiliated_programs", ""), row.get("department_name", ""))
        row.setdefault("primary_field", "")
        row.setdefault("department_page_url", "")
        row.setdefault("enrichment_source_urls", "")
        row.setdefault("enrichment_status", "pending")
        row.setdefault("enrichment_message", "")
        row.setdefault("enriched_at", "")
        row["lab_url_status"] = normalize_lab_url_status(row.get("lab_url_status", ""), row.get("lab_url", ""))
        row["data_quality_status"] = data_quality_status(row)
        row["enricher_version"] = ENRICHER_VERSION
        labs_by_id[lab_id] = row
    return labs_by_id, department_by_id


def build_department_name_index(
    labs_by_id: dict[str, dict[str, str]],
    department: dict[str, str],
    globally_unique_name_to_lab_id: dict[str, str],
) -> dict[str, str]:
    department_id = clean_text(department.get("department_id", ""))
    department_name = clean_text(department.get("department_name_kor", ""))
    candidates: defaultdict[str, list[str]] = defaultdict(list)
    for lab_id, row in labs_by_id.items():
        primary_match = department_id and department_id in {
            clean_text(row.get("primary_department_id", "")),
            clean_text(row.get("department_id", "")),
        }
        affiliation_match = department_name and department_name in split_multi(row.get("affiliated_programs", ""))
        if not (primary_match or affiliation_match):
            continue
        name = normalize_name(row.get("professor_name", ""))
        # A name-only match is permitted only when it is unique both globally
        # and inside the current department/program.
        if name and globally_unique_name_to_lab_id.get(name) == lab_id:
            candidates[name].append(lab_id)
    return {name: ids[0] for name, ids in candidates.items() if len(ids) == 1}


def build_indexes(
    labs_by_id: dict[str, dict[str, str]],
) -> tuple[dict[str, str], dict[str, str], set[str], set[str]]:
    email_to_ids: defaultdict[str, list[str]] = defaultdict(list)
    name_to_ids: defaultdict[str, list[str]] = defaultdict(list)
    for lab_id, row in labs_by_id.items():
        email = normalize_email(row.get("email", ""))
        if email:
            email_to_ids[email].append(lab_id)
        name = normalize_name(row.get("professor_name", ""))
        if name:
            name_to_ids[name].append(lab_id)

    duplicate_emails = {email for email, ids in email_to_ids.items() if len(ids) > 1}
    labs_by_email = {email: ids[0] for email, ids in email_to_ids.items() if len(ids) == 1}
    unique_name_to_lab_id = {name: ids[0] for name, ids in name_to_ids.items() if len(ids) == 1}
    return labs_by_email, unique_name_to_lab_id, set(name_to_ids), duplicate_emails


def clean_departments(departments: list[dict[str, str]]) -> None:
    for row in departments:
        row["enricher_version"] = ENRICHER_VERSION
        if row.get("faculty_page_urls"):
            valid_urls = [
                url for url in split_multi(row.get("faculty_page_urls", "")) if normalize_url(url)
            ]
            row["faculty_page_urls"] = merge_multi(*valid_urls)


# ============================================================
# 12. Main pipeline
# ============================================================
def run_stage2(args: argparse.Namespace) -> None:
    paths = RuntimePaths.from_args(Path(args.data_dir), Path(args.overrides) if args.overrides else None)
    departments, department_existing_fields = read_csv_rows(paths.departments)
    labs, lab_existing_fields = read_csv_rows(paths.labs)

    department_fields = ensure_fields(
        department_existing_fields,
        BASE_DEPARTMENT_FIELDS + STAGE2_DEPARTMENT_FIELDS,
    )
    lab_fields = ensure_fields(
        lab_existing_fields,
        BASE_LAB_FIELDS + STAGE2_LAB_FIELDS,
    )

    run_slug = timestamp_slug()
    if not args.dry_run:
        backup_labs = backup_file(paths.labs, paths.backups, run_slug)
        backup_departments = backup_file(paths.departments, paths.backups, run_slug)
        print(f"[BACKUP] labs.csv        → {backup_labs}")
        print(f"[BACKUP] departments.csv → {backup_departments}")

    overrides = load_overrides(paths.overrides)
    cleaned_labs, clean_report = clean_all_labs(labs)
    clean_departments(departments)
    labs_by_id, department_by_id = initialize_rows(departments, cleaned_labs)

    print("=" * 100)
    print(f"POSTECH LAB DATABASE — STAGE 2 ENRICHER {ENRICHER_VERSION}")
    print("=" * 100)
    print(f"데이터 폴더          : {paths.data_dir}")
    print(f"대학원/학과/학부/전공: {len(departments)}개")
    print(f"기존 연구실 레코드    : {len(labs_by_id)}개")
    print(
        "정제 결과            : "
        f"행 {clean_report.changed_rows}개, "
        f"필드 {sum(clean_report.changed_fields.values())}개, "
        f"반복 오염 {sum(clean_report.duplicate_noise.values())}개"
    )
    print()

    if args.clean_only:
        # Manual overrides are deterministic local corrections and therefore
        # also apply in clean-only mode. This lets known names/URLs be repaired
        # without requiring a network crawl.
        manual_count = apply_manual_overrides(labs_by_id, overrides)
        for lab in labs_by_id.values():
            lab["data_quality_status"] = data_quality_status(lab)
            lab["enricher_version"] = ENRICHER_VERSION
        for row in departments:
            row["enricher_version"] = ENRICHER_VERSION
        save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, args.dry_run)
        append_jsonl(
            paths.log,
            {
                "timestamp": now_iso(),
                "level": "clean_summary",
                "enricher_version": ENRICHER_VERSION,
                "labs_total": len(labs_by_id),
                "changed_rows": clean_report.changed_rows,
                "changed_fields": dict(clean_report.changed_fields),
                "blanked_noise": dict(clean_report.blanked_noise),
                "duplicate_noise": dict(clean_report.duplicate_noise),
                "invalid_urls": clean_report.invalid_urls,
                "manual_overrides": manual_count,
                "dry_run": args.dry_run,
            },
        )
        print("[CLEAN-ONLY] 네트워크 수집 없이 기존 CSV 정제만 수행했습니다.")
        print(f"[OVERRIDE] 수동 보정 적용: {manual_count}개 연구실")
        if args.dry_run:
            print("[DRY-RUN] CSV에는 기록하지 않았습니다.")
        else:
            print(f"저장: {paths.labs}")
            print(f"저장: {paths.departments}")
        return

    labs_by_email, unique_name_to_lab_id, normalized_known_names, duplicate_emails = build_indexes(labs_by_id)

    client = RespectfulClient(
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        browser_fallback=args.browser_fallback,
        allow_insecure=args.allow_insecure,
        respect_robots=not args.ignore_robots,
    )

    selected_departments = departments
    if args.department:
        needle = args.department.casefold()
        selected_departments = [
            row
            for row in selected_departments
            if needle in clean_text(row.get("department_name_kor", "")).casefold()
            or needle in clean_text(row.get("department_name_eng", "")).casefold()
            or needle == clean_text(row.get("department_id", "")).casefold()
        ]
    if args.test_limit is not None:
        selected_departments = selected_departments[: args.test_limit]

    print(f"실행 대상            : {len(selected_departments)}개")
    print(f"페이지 상한           : 학과당 {args.max_pages}개, 깊이 {args.max_depth}")
    print(f"브라우저 fallback     : {args.browser_fallback}")
    print(f"robots.txt 준수       : {not args.ignore_robots}")
    print(f"랩 홈페이지 보완      : {not args.skip_lab_homepages}")
    if duplicate_emails:
        print(f"중복 이메일 자동매칭 제외: {len(duplicate_emails)}개")

    run_started_at = now_iso()
    touched_lab_ids: set[str] = set()
    skipped_success_departments = 0
    attempted_departments = 0

    for department_index, department in enumerate(selected_departments, start=1):
        department_id = clean_text(department.get("department_id", ""))
        department_name = clean_text(department.get("department_name_kor", ""))
        department_type = clean_text(department.get("department_type", ""))
        type_label = classify_department_label(department_type)
        homepage = clean_text(department.get("homepage_url", ""))

        if not args.force and clean_text(department.get("enrichment_status", "")) == "success":
            skipped_success_departments += 1
            print(
                f"[SKIP-DEPT] {department_index:02d}/{len(selected_departments):02d} | "
                f"구분={type_label} | 학과={department_name} | 이전 성공"
            )
            continue

        attempted_departments += 1
        print("\n" + "-" * 100)
        print(
            f"[DEPT] {department_index:02d}/{len(selected_departments):02d} | "
            f"구분={type_label} | 학과={department_name} | {homepage or 'URL 없음'}"
        )

        override = resolve_department_override(overrides, department)
        eligible_name_to_lab_id = build_department_name_index(labs_by_id, department, unique_name_to_lab_id)
        try:
            pages = discover_department_pages(
                client,
                department,
                override,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                known_names=normalized_known_names,
                paths=paths,
                save_raw=args.save_raw_html,
            )
        except Exception as exc:
            department["enrichment_status"] = "failed"
            department["enrichment_message"] = str(exc)
            department["enriched_at"] = now_iso()
            department["enricher_version"] = ENRICHER_VERSION
            print(f"[FAIL-DEPT] {department_name} | {exc}")
            save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, args.dry_run)
            continue

        department_match_ids: set[str] = set()
        faculty_pages: set[str] = set()
        field_update_counts: Counter[str] = Counter()

        for result in pages:
            matches = build_page_matches(
                result,
                override,
                labs_by_id,
                labs_by_email,
                eligible_name_to_lab_id,
                normalized_known_names,
            )
            if not matches:
                continue
            faculty_pages.add(result.url)

            for match in matches:
                current = labs_by_id[match.lab_id]
                update = extract_card_data(match.block, result.url, current, override)
                merged, changed_fields = merge_lab_update(current, update, department_name)
                merged["enriched_at"] = now_iso()
                merged["enricher_version"] = ENRICHER_VERSION

                if changed_fields:
                    merged["enrichment_status"] = "success"
                    merged["enrichment_message"] = (
                        f"{department_name} 페이지에서 {match.method} 매칭; "
                        f"갱신: {', '.join(changed_fields)}"
                    )
                    touched_lab_ids.add(merged["lab_id"])
                    field_update_counts.update(changed_fields)
                elif merged.get("enrichment_status") in {"", "pending", "no_match"}:
                    merged["enrichment_status"] = "matched_no_change"
                    merged["enrichment_message"] = (
                        f"{department_name}에서 {match.method} 매칭되었으나 신뢰도 높은 새 필드 없음"
                    )

                merged["data_quality_status"] = data_quality_status(merged)
                labs_by_id[merged["lab_id"]] = merged
                department_match_ids.add(merged["lab_id"])

                print(
                    f"    [MATCH] 구분={type_label} | 학과={department_name} | "
                    f"랩={merged.get('lab_name_kor', '-') or '-'} | "
                    f"교수={merged.get('professor_name', '-') or '-'} | "
                    f"방식={match.method} | 갱신={','.join(changed_fields) or '-'}"
                )
                append_jsonl(
                    paths.log,
                    {
                        "timestamp": now_iso(),
                        "level": "match",
                        "department_type": department_type,
                        "department": department_name,
                        "department_id": department_id,
                        "lab_id": merged.get("lab_id", ""),
                        "lab_name": merged.get("lab_name_kor", ""),
                        "professor": merged.get("professor_name", ""),
                        "match_method": match.method,
                        "updated_fields": changed_fields,
                        "page_url": result.url,
                        "enricher_version": ENRICHER_VERSION,
                    },
                )

        if not args.skip_lab_homepages:
            for lab_id in sorted(department_match_ids):
                lab = labs_by_id[lab_id]
                lab_url = normalize_url(lab.get("lab_url", ""))
                if not lab_url or lab.get("lab_url_status") in {"manual", "invalid"}:
                    continue
                if (
                    not args.force
                    and lab.get("lab_url_status") == "verified_homepage"
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
                    merged["enricher_version"] = ENRICHER_VERSION
                    merged["data_quality_status"] = data_quality_status(merged)
                    labs_by_id[lab_id] = merged
                    touched_lab_ids.add(lab_id)
                    field_update_counts.update(changed)
                    print(
                        f"    [LAB] 학과={department_name} | "
                        f"랩={merged.get('lab_name_kor', '-') or '-'} | "
                        f"교수={merged.get('professor_name', '-') or '-'} | "
                        f"홈페이지 보완={', '.join(changed)}"
                    )

        department["faculty_page_urls"] = merge_multi(department.get("faculty_page_urls", ""), sorted(faculty_pages))
        department["faculty_match_count"] = str(len(department_match_ids))
        department["enriched_at"] = now_iso()
        department["enricher_version"] = ENRICHER_VERSION
        if department_match_ids:
            department["enrichment_status"] = "success"
            summary = ", ".join(f"{key}={value}" for key, value in sorted(field_update_counts.items()))
            department["enrichment_message"] = (
                f"교수/랩 {len(department_match_ids)}명 매칭" + (f"; {summary}" if summary else "")
            )
        else:
            department["enrichment_status"] = "no_match"
            department["enrichment_message"] = "교수 카드 또는 기존 교수와의 안전한 매칭을 찾지 못함"

        print(
            f"[DONE-DEPT] 구분={type_label} | 학과={department_name} | "
            f"매칭={len(department_match_ids)} | 교수페이지={len(faculty_pages)}"
        )

        if department_index % DEFAULT_CHECKPOINT_EVERY == 0:
            save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, args.dry_run)

    # Re-clean after crawling. This makes clean-only and full runs idempotent and
    # catches cross-department page-wide contamination introduced by a bad site.
    final_rows, final_clean_report = clean_all_labs(list(labs_by_id.values()))
    labs_by_id = {row["lab_id"]: row for row in final_rows if clean_text(row.get("lab_id", ""))}

    # Apply explicit manual corrections after automatic cross-record cleaning so
    # trusted overrides are not removed as repeated values. Individual values are
    # still sanitized by merge_lab_update().
    manual_count = apply_manual_overrides(labs_by_id, overrides)
    if manual_count:
        print(f"[OVERRIDE] 수동 보정 적용: {manual_count}개 연구실")

    for lab in labs_by_id.values():
        if lab.get("enrichment_status") in {"", "pending"}:
            lab["enrichment_status"] = "no_match"
            lab["enrichment_message"] = "2차 크롤러에서 안전한 매칭을 찾지 못함"
        if not lab.get("affiliated_programs"):
            lab["affiliated_programs"] = lab.get("department_name", "")
        lab["data_quality_status"] = data_quality_status(lab)
        lab["enricher_version"] = ENRICHER_VERSION

    save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, args.dry_run)

    quality_counts = Counter(clean_text(lab.get("data_quality_status", "")) or "unknown" for lab in labs_by_id.values())
    status_counts = Counter(clean_text(lab.get("enrichment_status", "")) or "unknown" for lab in labs_by_id.values())
    url_status_counts = Counter(clean_text(lab.get("lab_url_status", "")) or "unknown" for lab in labs_by_id.values())

    append_jsonl(
        paths.log,
        {
            "timestamp": now_iso(),
            "level": "summary",
            "run_started_at": run_started_at,
            "enricher_version": ENRICHER_VERSION,
            "departments_selected": len(selected_departments),
            "departments_attempted": attempted_departments,
            "departments_skipped_previous_success": skipped_success_departments,
            "labs_total": len(labs_by_id),
            "duplicate_emails_excluded": sorted(duplicate_emails),
            "labs_touched": len(touched_lab_ids),
            "manual_overrides": manual_count,
            "quality_counts": dict(quality_counts),
            "status_counts": dict(status_counts),
            "lab_url_status_counts": dict(url_status_counts),
            "pre_clean": {
                "changed_rows": clean_report.changed_rows,
                "changed_fields": dict(clean_report.changed_fields),
                "duplicate_noise": dict(clean_report.duplicate_noise),
            },
            "post_clean": {
                "changed_rows": final_clean_report.changed_rows,
                "changed_fields": dict(final_clean_report.changed_fields),
                "duplicate_noise": dict(final_clean_report.duplicate_noise),
            },
            "dry_run": args.dry_run,
        },
    )

    print("\n" + "=" * 100)
    print("STAGE 2 COMPLETE")
    print("=" * 100)
    print(f"버전            : {ENRICHER_VERSION}")
    print(f"실행 대상 학과   : {len(selected_departments)}")
    print(f"실제 재수집 학과 : {attempted_departments}")
    print(f"이전 성공 건너뜀 : {skipped_success_departments}")
    print(f"사전 정제 변경   : 행 {clean_report.changed_rows}, 필드 {sum(clean_report.changed_fields.values())}")
    print(f"사후 정제 변경   : 행 {final_clean_report.changed_rows}, 필드 {sum(final_clean_report.changed_fields.values())}")
    print(f"크롤링 갱신 랩 수: {len(touched_lab_ids)}")
    print(f"수동 보정 수    : {manual_count}")
    print(f"품질 상태       : {dict(quality_counts)}")
    print(f"수집 상태       : {dict(status_counts)}")
    print(f"URL 상태        : {dict(url_status_counts)}")
    if args.dry_run:
        print("DRY RUN이므로 CSV에는 기록하지 않았습니다.")
    else:
        print(f"저장: {paths.labs}")
        print(f"저장: {paths.departments}")
        print(f"로그: {paths.log}")


# ============================================================
# 13. CLI
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "POSTECH 2차 크롤러: 기존 departments.csv/labs.csv를 읽어 학과 교수 페이지와 "
            "연구실 홈페이지에서 실제 연구실명, 연구분야, URL, 위치, 키워드 및 복수 소속을 보완합니다."
        )
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="departments.csv와 labs.csv가 있는 폴더")
    parser.add_argument("--overrides", help="사이트별 보정 JSON 경로. 기본값은 <data-dir>/site_overrides.json")
    parser.add_argument("--department", help="특정 학과명 또는 department_id만 실행")
    parser.add_argument("--test-limit", type=int, help="앞에서 N개 학과만 테스트")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_DEPARTMENT_PAGES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--delay", type=float, default=DEFAULT_REQUEST_DELAY_SECONDS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--force", action="store_true", help="이전 성공 상태도 다시 수집")
    parser.add_argument("--dry-run", action="store_true", help="CSV를 수정하지 않고 정제/수집 결과만 출력")
    parser.add_argument("--clean-only", action="store_true", help="네트워크 요청 없이 기존 CSV 오염값만 정제")
    parser.add_argument("--skip-lab-homepages", action="store_true", help="개별 연구실 홈페이지 검증·보완 생략")
    parser.add_argument("--browser-fallback", action="store_true", help="정적 HTML 부족 시 Playwright 사용")
    parser.add_argument("--allow-insecure", action="store_true", help="SSL 인증서 검증 실패 사이트 허용")
    parser.add_argument("--ignore-robots", action="store_true", help="robots.txt 검사 생략")
    parser.add_argument("--save-raw-html", action="store_true", help="수집 HTML을 <data-dir>/raw_stage2에 저장")
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.max_pages < 1:
        parser.error("--max-pages는 1 이상이어야 합니다.")
    if args.max_depth < 0:
        parser.error("--max-depth는 0 이상이어야 합니다.")
    if args.delay < 0:
        parser.error("--delay는 0 이상이어야 합니다.")
    if args.timeout < 1:
        parser.error("--timeout은 1 이상이어야 합니다.")
    if args.test_limit is not None and args.test_limit < 1:
        parser.error("--test-limit은 1 이상이어야 합니다.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)
    run_stage2(args)


if __name__ == "__main__":
    main()
