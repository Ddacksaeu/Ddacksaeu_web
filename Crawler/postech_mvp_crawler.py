from __future__ import annotations

import argparse
import atexit
import csv
import hashlib
import heapq
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
from copy import deepcopy
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
ENRICHER_VERSION = "0.12.4-preservation-first-repair"

DEFAULT_DATA_DIR = Path("./data")
DEFAULT_REQUEST_DELAY_SECONDS = 0.55
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_DEPARTMENT_PAGES = 12
DEFAULT_MAX_DEPTH = 2
DEFAULT_CHECKPOINT_EVERY = 1
DEFAULT_RESPECT_ROBOTS = True
DEFAULT_CONNECT_TIMEOUT_SECONDS = 4
DEFAULT_HTTP_RETRIES = 1
DEFAULT_MAX_HOST_FAILURES = 3
DEFAULT_LAB_LINK_MAX_PAGES = 120
DEFAULT_LAB_LINK_MAX_DEPTH = 2
DEFAULT_LAB_LINK_CANDIDATES_PER_LAB = 3
DEFAULT_LAB_LINK_IDENTITY_SOURCES_PER_LAB = 2
DEFAULT_LAB_LINK_HOST_PAGE_CAP = 20
DEFAULT_LAB_LINK_PROGRESS_EVERY = 10
DEFAULT_LAB_LINK_TIME_BUDGET_MINUTES = 20
DEFAULT_LAB_LINK_HOMEPAGE_PROBE_PAGES = 2
AIF_RESEARCHER_LIST_URL = "https://aif.postech.ac.kr/kor/research/researcher-search.do"
AIF_RESEARCHER_PAGE_SIZE = 10
AIF_RESEARCHER_MAX_RECORDS = 340
MIN_AUTHORITATIVE_SUCCESS_RATIO = 1.0
DEFAULT_MIN_PRIMARY_ROSTER_COVERAGE = 0.20
CENTRAL_RESEARCHER_HOSTS = {"postech.ac.kr", "www.postech.ac.kr"}
CENTRAL_RESEARCHER_PATH_TOKEN = "/research-industry-academia/researcher-search.do"
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



# Built-in site profiles are always active. An external site_overrides.json may
# extend or override these values, but the shared-portal scope guards never
# depend on a separate file being present.
BUILTIN_SITE_OVERRIDES: dict[str, dict] = {'생명과학과': {'faculty_urls': ['https://life.postech.ac.kr/html/professor/professor01.php', 'https://life.postech.ac.kr/eng/html/professor/professor01.php'], 'allowed_hosts': ['life.postech.ac.kr'], 'render': True, 'max_depth': 3, 'max_card_emails': 2, 'max_card_identities': 2}, '시스템생명공학부': {'faculty_urls': ['https://ibio.postech.ac.kr/web/?depart=1&position=1&sub=professor&top=member', 'https://ibio.postech.ac.kr/web/?depart=1&position=2&sub=professor&top=member', 'https://ibio.postech.ac.kr/web/?depart=1&position=3&sub=professor&top=member'], 'allowed_hosts': ['ibio.postech.ac.kr'], 'scope_query_params': {'depart': ['1']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '첨단재료과학부': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=2&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=2&position=2&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['2']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '의과학전공': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=11&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=11&position=2&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=11&position=3&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['11']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '국방과학기술전공': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=14&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=14&position=2&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=14&position=3&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['14']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '경영과학전공': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=15&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=15&position=2&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['15']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '푸드테크융합전공': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=16&position=2&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['16']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '양자정보과학전공': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=17&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=17&position=2&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=17&position=3&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['17']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '산업데이터사이언스전공': {'faculty_urls': ['https://gscst.postech.ac.kr/web/?depart=18&position=1&sub=professor&top=member', 'https://gscst.postech.ac.kr/web/?depart=18&position=2&sub=professor&top=member'], 'allowed_hosts': ['gscst.postech.ac.kr'], 'scope_query_params': {'depart': ['18']}, 'follow_links': False, 'max_depth': 0, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}, '수학과': {'faculty_urls': ['https://math.postech.ac.kr/bbs/board.php?bo_table=m02_01&sca=%EC%A0%84%EC%9E%84%EA%B5%90%EC%88%98', 'https://math.postech.ac.kr/en/bbs/board.php?bo_table=m02_01', 'https://math.postech.ac.kr/bbs/board.php?bo_table=m02_01&wr_id=16', 'https://math.postech.ac.kr/bbs/board.php?bo_table=m02_01&wr_id=3'], 'allowed_hosts': ['math.postech.ac.kr'], 'scope_query_params': {'bo_table': ['m02_01']}, 'max_depth': 2, 'max_card_emails': 2, 'max_card_identities': 2, 'allow_secondary_field_enrichment': False}}

# Additional program-specific profiles. These departments have no professor
# records whose immutable primary_department_id points to the program itself, so
# their membership must be rebuilt from a tightly scoped official faculty page.
BUILTIN_SITE_OVERRIDES.update({
    "반도체대학원": {
        "faculty_urls": ["https://gradsemi.postech.ac.kr/members/professor/"],
        "allowed_hosts": ["gradsemi.postech.ac.kr"],
        "follow_links": True,
        "max_depth": 1,
        "max_card_emails": 2,
        "max_card_identities": 2,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "정보통신대학원": {
        "faculty_urls": [
            "https://eecs.postech.ac.kr/teaching-and-research/professor/?dept=103"
        ],
        "allowed_hosts": ["eecs.postech.ac.kr"],
        "scope_query_params": {"dept": ["103"]},
        "follow_links": False,
        "max_depth": 0,
        "max_card_emails": 2,
        "max_card_identities": 2,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "소셜데이터사이언스(SDS) 전공": {
        "faculty_urls": ["https://psds.postech.ac.kr/professor"],
        "allowed_hosts": ["psds.postech.ac.kr"],
        "follow_links": True,
        "max_depth": 1,
        "max_card_emails": 2,
        "max_card_identities": 2,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "합성생물학전공": {
        "faculty_urls": ["https://synbio.postech.ac.kr/faculty"],
        "allowed_hosts": ["synbio.postech.ac.kr"],
        "follow_links": True,
        "render": True,
        "max_depth": 2,
        "max_card_emails": 2,
        "max_card_identities": 2,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
})

# These keys are safety invariants rather than optional parser hints. A stale
# external site_overrides.json must not be able to remove a shared-portal query
# lock or replace a program-filtered URL with an unfiltered all-faculty page.
HARD_SCOPE_GUARDS: dict[str, dict] = {
    "시스템생명공학부": {
        "faculty_urls": [
            "https://ibio.postech.ac.kr/web/?depart=1&position=1&sub=professor&top=member",
            "https://ibio.postech.ac.kr/web/?depart=1&position=2&sub=professor&top=member",
            "https://ibio.postech.ac.kr/web/?depart=1&position=3&sub=professor&top=member",
        ],
        "allowed_hosts": ["ibio.postech.ac.kr"],
        "scope_query_params": {"depart": ["1"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "첨단재료과학부": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=2&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=2&position=2&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["2"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "의과학전공": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=11&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=11&position=2&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=11&position=3&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["11"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "국방과학기술전공": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=14&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=14&position=2&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=14&position=3&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["14"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "경영과학전공": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=15&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=15&position=2&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["15"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "푸드테크융합전공": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=16&position=2&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["16"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "양자정보과학전공": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=17&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=17&position=2&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=17&position=3&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["17"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "산업데이터사이언스전공": {
        "faculty_urls": [
            "https://gscst.postech.ac.kr/web/?depart=18&position=1&sub=professor&top=member",
            "https://gscst.postech.ac.kr/web/?depart=18&position=2&sub=professor&top=member",
        ],
        "allowed_hosts": ["gscst.postech.ac.kr"],
        "scope_query_params": {"depart": ["18"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
    "정보통신대학원": {
        "faculty_urls": [
            "https://eecs.postech.ac.kr/teaching-and-research/professor/?dept=103"
        ],
        "allowed_hosts": ["eecs.postech.ac.kr"],
        "scope_query_params": {"dept": ["103"]},
        "follow_links": False,
        "allow_secondary_unique_name_affiliation": True,
        "allow_secondary_field_enrichment": False,
    },
}

# Emergency cardinality guards for shared portals. These values are intentionally
# generous: they do not define the expected faculty count; they only prevent a
# sibling-program navigation leak from attaching most POSTECH professors to one
# program. A department run is rolled back transactionally when the limit is
# exceeded.
SHARED_PORTAL_MAX_MATCHES = {
    "시스템생명공학부": 60,
    "첨단재료과학부": 40,
    "의과학전공": 60,
    "국방과학기술전공": 35,
    "경영과학전공": 35,
    "푸드테크융합전공": 35,
    "양자정보과학전공": 45,
    "산업데이터사이언스전공": 45,
}
# Static faculty-count limits are retained only for legacy audit context.
# They are deliberately not injected into site profiles because legitimate
# adjunct-faculty pages can be large. Runtime safety now depends on URL scope,
# exact-email evidence, and transaction rollback on evidence mismatch.




# High-yield official pages that expose professor e-mail, lab name and/or a
# direct research-group homepage. They are mined by exact professor e-mail;
# their navigation text is never used as professor data.
LAB_LINK_DIRECTORY_URLS = (
    "https://www.postech.ac.kr/kor/research-industry-academia/researcher-search.do",
    "https://postech.ac.kr/eng/research/researcher_search_list.do",
    "https://emed.postech.ac.kr/web/?sub=lab&top=study",
    "https://med.postech.ac.kr/web/?sub=lab&top=study",
    "https://emed.postech.ac.kr/web/?depart=1&position=1&sub=professor&top=member",
    "https://ax.postech.ac.kr/ax/res/research_area.do",
    "https://cite.postech.ac.kr/bbs/board.php?bo_table=sub2_1_a",
    "https://cite.postech.ac.kr/bbs/board.php?bo_table=sub2_1_b",
    "https://me.postech.ac.kr/ko/page/member01",
    "https://ph.postech.ac.kr/physics/member/professor.do?mode=list",
    "https://mse.postech.ac.kr/theme/mse/html/proff.php",
    "https://mse.postech.ac.kr/en/theme/mse_en/html/proff.php",
    "https://chem.postech.ac.kr/bbs/board.php?bo_table=en2_1",
    "https://ce.postech.ac.kr/bbs/board.php?bo_table=eng4_1",
    "https://ime.postech.ac.kr/ime/people/faculty.do",
    "https://cse.postech.ac.kr/csepostech/people/faculty.do",
    "https://dane.postech.ac.kr/member/faculty.php",
    "https://eecs.postech.ac.kr/teaching-and-research/professor/?dept=ALL",
    "https://gift.postech.ac.kr/bbs/board.php?bo_table=sub2_8_N",
)

LAB_LINK_STRONG_LABELS = (
    "연구실 홈페이지", "랩 홈페이지", "공식 홈페이지", "공식 웹사이트",
    "lab homepage", "laboratory homepage", "research group homepage",
    "official website", "official homepage",
)
LAB_LINK_WEAK_LABELS = (
    "homepage", "home page", "website", "web site", "웹사이트", "홈페이지",
    "lab", "laboratory", "research group", "연구실",
)
LAB_NAME_LABELS = (
    "연구실명", "연구실", "랩", "lab name", "laboratory", "lab",
    "research office", "research laboratory", "research group",
)
LAB_LINK_SOURCE_PATH_HINTS = (
    "faculty", "professor", "people", "member", "researcher", "staff",
    "lab", "laboratory", "research_area", "research-area", "연구실",
)
LAB_LINK_RENDER_HOSTS = {
    "life.postech.ac.kr", "synbio.postech.ac.kr", "ax.postech.ac.kr",
    "gradsemi.postech.ac.kr",
}
GENERIC_HOMEPAGE_TITLES = {
    "home", "homepage", "welcome", "website", "postech",
    "pohang university of science and technology", "연구실", "홈",
}

GENERIC_LAB_NAME_EXACT = {
    "lab", "laboratory", "research group", "research center",
    "our lab", "the lab", "this lab", "our laboratory",
    "연구실", "본 연구실", "건강한 연구실",
}
LAB_NAME_NOISE_PATTERNS = (
    re.compile(r"(?i)^(?:head|director|principal investigator|professor|contact|about us)\b"),
    re.compile(r"(?i)\b(?:is funded by|funded by|supported by|welcome to our|click here|homepage|website)\b"),
    re.compile(r"(?i)^(?:www\.|https?://)"),
)
BROAD_PAGE_MAX_KNOWN_EMAILS = 3
BROAD_PAGE_MAX_KNOWN_NAMES = 4
DEAD_HOMEPAGE_PATTERNS = (
    re.compile(r"\b(?:404|403|500)\b.{0,30}(?:not found|error|forbidden)", re.I),
    re.compile(r"(?:domain for sale|buy this domain|parked domain|expired domain)", re.I),
    re.compile(r"(?:페이지를 찾을 수 없|존재하지 않는 페이지|접근이 거부)", re.I),
)

LOCATION_PROSE_NOISE_RE = re.compile(
    r"(?:박사과정\s*시절|연락바랍니다|연락\s*바랍니다|성적증명서|"
    r"학부연구|대학원\s*입학|모집|Track\s*Chair|학회|국회|특별법|"
    r"처분장\s*정책|전망입니다|기사|보도|수상|게재|개최|선정)",
    re.I,
)
POSTECH_POSTAL_ADDRESS_RE = re.compile(
    r"(?:\b37673\b|경상북도\s*포항시|경북\s*포항시|포항시\s*남구|"
    r"청암로\s*77|효자동\s*산?\d+|(?:TEL|전화)\.?\s*0?54[- .]279)",
    re.I,
)


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
    "affiliation_evidence",
    "field_provenance",
    "data_state",
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

# Explicit source precedence for conflicting research-group links.  A current
# departmental professor page is preferred to the central researcher index,
# while an actually verified homepage still outranks an unverified guess.
LAB_LINK_SOURCE_PRIORITY = {
    "department_profile": 700,
    "department_faculty_page": 650,
    "department_source": 600,
    "professor_profile": 500,
    "enrichment_source": 450,
    "official_directory": 400,
    "aif_researcher_detail": 350,
    "aif_researcher_index": 300,
    "existing_trusted_revalidation": 200,
    "existing_candidate": 150,
    "homepage_title_guess": 100,
}

QUARANTINED_DATA_STATES = {
    "clean_only_quarantined",
    "authoritative_rebuild_pending",
}

AUTHORITATIVE_DATA_STATES = {
    "authoritative_rebuilt",
    "authoritative_no_match",
    "authoritative_identity_only",
    "authoritative_central_identity_fallback",
    "manual_verified",
    "incremental_verified",
    "legacy_unverified",
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
    rebuild_report: Path
    lab_link_diagnostics: Path

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
            rebuild_report=data_dir / "authoritative_rebuild_report.json",
            lab_link_diagnostics=data_dir / "lab_link_diagnostics.csv",
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


@dataclass(frozen=True)
class LabLinkCandidate:
    lab_id: str
    url: str
    source_url: str
    source_kind: str
    evidence_method: str
    score: int
    label_text: str = ""
    exact_email: bool = False
    exact_name: bool = False
    lab_name: str = ""


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
    connect_timeout_seconds: int = DEFAULT_CONNECT_TIMEOUT_SECONDS
    browser_fallback: bool = False
    allow_insecure: bool = False
    respect_robots: bool = DEFAULT_RESPECT_ROBOTS
    retry_total: int = DEFAULT_HTTP_RETRIES
    max_host_failures: int = DEFAULT_MAX_HOST_FAILURES
    _robots: dict[str, RobotFileParser] = field(default_factory=dict)
    _cache: dict[str, PageResult] = field(default_factory=dict)
    _host_failures: Counter[str] = field(default_factory=Counter)
    _blocked_hosts: set[str] = field(default_factory=set)
    _playwright: object = field(default=None, init=False, repr=False)
    _browser: object = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        retry_count = max(0, int(self.retry_total))
        retry = Retry(
            total=retry_count,
            connect=retry_count,
            read=retry_count,
            backoff_factor=0.35,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
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
        atexit.register(self.close)

    def _sleep_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

    def _request_timeout(self, read_cap: Optional[int] = None) -> tuple[int, int]:
        connect = max(1, int(self.connect_timeout_seconds))
        read = max(1, int(self.timeout_seconds))
        if read_cap is not None:
            read = min(read, max(1, int(read_cap)))
        return connect, read

    def _ensure_host_available(self, url: str) -> None:
        host = hostname(url)
        if host and host in self._blocked_hosts:
            raise RuntimeError(f"호스트 연속 실패로 이번 실행에서 차단됨: {host}")

    def _mark_success(self, url: str) -> None:
        host = hostname(url)
        if host:
            self._host_failures[host] = 0

    def _mark_failure(self, url: str) -> None:
        host = hostname(url)
        if not host:
            return
        self._host_failures[host] += 1
        if self.max_host_failures > 0 and self._host_failures[host] >= self.max_host_failures:
            self._blocked_hosts.add(host)

    def _robots_allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        self._ensure_host_available(url)
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots:
            parser = RobotFileParser()
            parser.set_url(f"{base}/robots.txt")
            try:
                self._sleep_if_needed()
                response = self.session.get(
                    f"{base}/robots.txt",
                    timeout=self._request_timeout(read_cap=5),
                    verify=not self.allow_insecure,
                )
                self._last_request_at = time.monotonic()
                parser.parse(response.text.splitlines() if response.ok else [])
            except requests.RequestException:
                parser.parse([])
            self._robots[base] = parser
        return self._robots[base].can_fetch(USER_AGENT, url)

    def _static_fetch(self, url: str) -> PageResult:
        self._ensure_host_available(url)
        if not self._robots_allowed(url):
            raise PermissionError(f"robots.txt가 접근을 허용하지 않습니다: {url}")
        self._sleep_if_needed()
        response = self.session.get(
            url,
            timeout=self._request_timeout(),
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

    def _ensure_browser(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright가 설치되지 않았습니다. "
                "pip install playwright 후 playwright install chromium을 실행하세요."
            ) from exc
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)

    def _browser_fetch(self, url: str) -> PageResult:
        self._ensure_host_available(url)
        self._ensure_browser()
        page = self._browser.new_page(user_agent=USER_AGENT, locale="ko-KR")
        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=max(5, int(self.timeout_seconds)) * 1000,
            )
            page.wait_for_timeout(500)
            html = page.content()
            final_url = page.url
        finally:
            page.close()
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
        self._ensure_host_available(url)
        cache_key = f"browser:{url}" if force_browser else f"auto:{url}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        static_result: Optional[PageResult] = None
        try:
            static_result = self._static_fetch(url)
            result = static_result
            should_render = self.browser_fallback and (
                force_browser or self._needs_browser(static_result.html)
            )
            if should_render:
                try:
                    rendered = self._browser_fetch(static_result.url)
                    if not self._needs_browser(rendered.html) or self._needs_browser(static_result.html):
                        result = rendered
                except Exception:
                    if self._needs_browser(static_result.html):
                        raise
                    result = static_result
            self._mark_success(result.url)
        except PermissionError:
            raise
        except Exception:
            # A generic timeout/HTTP error should not launch Chromium. Browser
            # fallback is reserved for hosts explicitly marked as render-only.
            if force_browser and self.browser_fallback:
                try:
                    result = self._browser_fetch(url)
                    self._mark_success(result.url)
                except Exception:
                    self._mark_failure(url)
                    raise
            else:
                self._mark_failure(url)
                raise

        self._cache[cache_key] = result
        return result

    def close(self) -> None:
        browser, playwright = self._browser, self._playwright
        self._browser = None
        self._playwright = None
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                pass
        try:
            self.session.close()
        except Exception:
            pass


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
    if re.fullmatch(
        r"(?i)(?:www\.)?(?:[A-Za-z0-9-]+\.)+(?:ac\.kr|co\.kr|go\.kr|or\.kr|com|org|net|edu|io|ai|kr)(?:/[^\s]*)?",
        href,
    ):
        href = "https://" + href
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


def infer_data_state(row: dict[str, str]) -> str:
    current = clean_text(row.get("data_state", ""))
    if current and current not in QUARANTINED_DATA_STATES:
        return current
    status = clean_text(row.get("enrichment_status", ""))
    link_status = clean_text(row.get("lab_url_status", ""))
    if link_status == "manual":
        return "manual_verified"
    if status == "success_identity_fallback":
        return "authoritative_central_identity_fallback"
    if status == "matched_identity_only":
        return "authoritative_identity_only"
    if status == "no_match":
        return "authoritative_no_match"
    if status == "success":
        return "authoritative_rebuilt"
    if lab_url_provenance_complete(row) or parse_json_dict(row.get("field_provenance", "")):
        return "incremental_verified"
    return "legacy_unverified"


def recover_data_states_from_backups(
    labs_by_id: dict[str, dict[str, str]], backup_dir: Path,
) -> dict[str, int]:
    recovered: dict[str, str] = {}
    if backup_dir.exists():
        backup_files = sorted(
            (path for path in backup_dir.glob("labs_before_stage2_*.csv") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in backup_files:
            try:
                rows, _ = read_csv_rows(path)
            except Exception:
                continue
            for row in rows:
                lab_id = clean_text(row.get("lab_id", ""))
                state = clean_text(row.get("data_state", ""))
                if lab_id and lab_id not in recovered and state and state not in QUARANTINED_DATA_STATES:
                    recovered[lab_id] = state
            if len(recovered) >= len(labs_by_id):
                break

    metrics = {"preserved": 0, "restored_from_backup": 0, "reconstructed": 0}
    for lab_id, row in labs_by_id.items():
        current = clean_text(row.get("data_state", ""))
        if current and current not in QUARANTINED_DATA_STATES:
            metrics["preserved"] += 1
            continue
        backup_state = recovered.get(lab_id, "")
        if backup_state:
            row["data_state"] = backup_state
            metrics["restored_from_backup"] += 1
        else:
            row["data_state"] = infer_data_state(row)
            metrics["reconstructed"] += 1
    return metrics


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def deep_merge_dict(base: dict, override: dict) -> dict:
    result = json.loads(json.dumps(base, ensure_ascii=False))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_overrides(path: Path) -> dict:
    external: dict = {}
    if path.exists():
        with path.open("r", encoding="utf-8-sig") as file:
            external = json.load(file)
        if not isinstance(external, dict):
            raise ValueError("site_overrides.json 최상위 값은 객체여야 합니다.")
    merged = deep_merge_dict(BUILTIN_SITE_OVERRIDES, external)
    # Reapply non-negotiable scope guards after external overrides. Parser
    # selectors remain customizable, but program identity boundaries do not.
    for department_name, guard in HARD_SCOPE_GUARDS.items():
        current = merged.get(department_name, {})
        if not isinstance(current, dict):
            current = {}
        merged[department_name] = deep_merge_dict(current, guard)
    return merged


def effective_builtin_overrides() -> dict:
    """Return built-ins with the same non-negotiable guards as load_overrides()."""
    merged = deep_merge_dict({}, BUILTIN_SITE_OVERRIDES)
    for department_name, guard in HARD_SCOPE_GUARDS.items():
        current = merged.get(department_name, {})
        if not isinstance(current, dict):
            current = {}
        merged[department_name] = deep_merge_dict(current, guard)
    return merged


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
    text = re.sub(r"(?i)^welcome\s+to\s+", "", text).strip(" .,:;-|")
    low = text.casefold()
    if low in GENERIC_LAB_NAME_EXACT or low in GENERIC_LINK_TEXTS:
        return False
    if any(pattern.search(text) for pattern in LAB_NAME_NOISE_PATTERNS):
        return False
    if EMAIL_RE.search(text) or looks_urlish_text(text):
        return False
    if text.count("(") != text.count(")") or text.count("[") != text.count("]"):
        return False
    if re.match(r"^\s*\d+[.)]\s*", text):
        return False
    if re.search(r"(?i)\b(?:funded|supported|located|recruiting|positions?|news|publication)\b", text):
        return False
    if len(text.split()) > 16:
        return False
    explicit = bool(re.search(
        r"(?i)(?:\blab(?:oratory)?\b|research\s+(?:group|center)|\bgroup\b$|연구실$|연구그룹$|연구센터$)",
        text,
    ))
    compact = bool(re.fullmatch(r"(?i)[a-z0-9][a-z0-9._&+\-]{1,30}lab", text.replace(" ", "")))
    if not (explicit or compact):
        return False
    if "department of" in low and not re.search(r"(?i)(?:lab|laboratory|research group)", text):
        return False
    return True

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
    text = re.sub(r"(?i)^welcome\s+to\s+", "", text).strip(" .,:;-|")
    if text.count("(") != text.count(")"):
        inner = clean_text(text.rsplit("(", 1)[-1]).strip(" )")
        if inner and re.search(r"(?:연구실|연구그룹|연구센터)$", inner):
            text = inner
        else:
            return ""
    if re.match(r"(?i)^www\.[a-z0-9._-]+$", text):
        text = text[4:]
    if len(text) > 140:
        text = strip_site_suffix(text)
    matches = [clean_text(match.group(0)).strip(" .,:;-") for match in LAB_NAME_RE.finditer(text)]
    valid_matches = [item for item in matches if item != text and is_probable_lab_name(item)]
    if not is_probable_lab_name(text) and valid_matches:
        valid_matches.sort(key=lambda item: (-len(item.split()), len(item)))
        text = valid_matches[0]
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
    if text.startswith("[") or LOCATION_PROSE_NOISE_RE.search(text) or re.search(
        r"(?:교수\s*(?:연구팀|POSTECH)|연구팀|최종\s*선정|기사\s*중\s*발췌|"
        r"국제공동연구|기술\s*개발|공동\s*연구를\s*통해|수상|게재|보도자료)",
        text,
        re.I,
    ):
        return ""

    # Some official profiles place the room before the building, for example
    # "326, POSTECH Biotech Center (PBC), 55, Jigok-ro ...". Preserve the
    # campus building/room pair and discard the postal-address tail.
    room_first = re.match(
        r"^#?(?P<room>[A-Za-z]?\d{2,4})(?:호)?(?:\s*[,/\-]\s*|\s+)"
        r"(?P<building>[^,;]{2,90}?(?:관|동|센터|연구소|Building|Bldg\.?|Center)(?:\s*\([^)]+\))?)"
        r"(?:\s*[,;]|$)",
        text,
        re.I,
    )
    if room_first:
        return clean_text(f"{room_first.group('building')} {room_first.group('room')}")

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
    # A full postal/contact address is not a lab-room value. It is rejected
    # after attempting to recover an explicit building-room pair above.
    if POSTECH_POSTAL_ADDRESS_RE.search(text) or ADDRESS_NOISE_RE.search(text):
        return ""
    if len(text) > 80:
        return ""
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
    # Strip recruitment wrappers while retaining a substantive research core.
    text = re.sub(
        r"(?is)^(?:무한한\s*기회의\s*장[^.。]{0,220}?(?:모집합니다|모집)|"
        r"대학원생\s*및\s*Post-?Doc\s*모집[^.。]*[.。]?|"
        r"(?:대학원생|학부연구생|박사후\s*연구원|Post-?Doc)[^.。]{0,450}?(?:모집|연락)[^.。]*[.。]?)\s*",
        "", text,
    )
    text = re.sub(
        r"(?is)\s*(?:졸업연구|학기\s*중\s*연구참여|동하계\s*인턴|"
        r"석박사과정|대학원생|Post-?Doc)[^.。]{0,500}(?:모집|지원|연락|참여|연계)?[^.。]*$",
        "", text,
    )
    text = clean_text(text).strip(" .,:;-|")
    if not text:
        return ""
    # A residual contact/hiring sentence is not a research summary.
    if re.search(
        r"(?:we are hiring|graduate students?|postdoctoral|visiting scholars?|"
        r"모집|지원|연락\s*(?:주세요|바랍니다)|관심\s*있는\s*(?:학생|연구원))",
        text, re.I,
    ) and not SUBSTANTIVE_RESEARCH_RE.search(text):
        return ""
    # Bilingual lab-name labels belong in lab_name fields, not summary.
    bilingual_lab_label = re.fullmatch(
        r"[^/]{2,80}(?:연구실|Lab)\s*/\s*[^/]{2,100}(?:Lab|Laboratory)",
        text, re.I,
    )
    if len(text) <= 140 and (
        bilingual_lab_label
        or (is_probable_lab_name(text) and not SUBSTANTIVE_RESEARCH_RE.search(text))
    ):
        return ""
    citation_markers = sum(
        bool(pattern.search(text))
        for pattern in (
            re.compile(r"\bdoi\s*:", re.I),
            re.compile(r"\bvol\.?\s*\d+", re.I),
            re.compile(r"\bp\.?\s*\d+\s*[–-]\s*\d+", re.I),
            re.compile(r"[\"“][^\"”]{15,}[\"”]"),
            re.compile(r"^(?:[A-Z가-힣][^,]{0,35},\s*){2,}"),
            re.compile(r"\b(?:19|20)\d{2}\.?$"),
        )
    )
    if citation_markers >= 2:
        return ""
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
    if re.search(
        r"(?:특별법.{0,120}(?:통과|국회)|처분장\s*정책|법적.?제도적\s*기반|"
        r"학회.{0,80}Track\s*Chair|수상\s*소식|보도자료)",
        text, re.I,
    ):
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
        "연구분야",
        "연구 분야",
        "전문분야",
        "전문 분야",
        "homepage 제작",
        "홈페이지 제작",
        "홈페이지 만들기",
        "무료 홈페이지",
        "포트폴리오 사이트",
        "크리에이터링크",
        "반응형웹",
        "반응형 홈페이지",
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
    r"/(?:news|notice|admission|recruit|award|seminar|event|gallery)(?:/|\.|$)"
    r"|/(?:community|board)/(?:[^?#]*/)?(?:news|notice)(?:/|\.|$)"
    r"|[?&](?:bd_id|bo_table|category|board)=?[^&#]*(?:news|notice|award|recruit)"
    r"|facultyapplication\.postech\.ac\.kr"
    r"|postechian\.org/alumni"
    r"|/invitation/"
    r")"
)


def is_non_identity_source_url(url: str) -> bool:
    normalized = normalize_url(url)
    if not normalized:
        return True
    return bool(PROVENANCE_NOISE_RE.search(normalized))


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
        if is_non_identity_source_url(url):
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


def summary_looks_like_news_article(text: str) -> bool:
    value = clean_text(text)
    if not value:
        return False
    markers = sum(
        bool(pattern.search(value))
        for pattern in (
            re.compile(r"(?:교수\s*연구팀|연구팀은|이번\s*연구|관련\s*링크)"),
            re.compile(r"(?:성공했다|확인했다|입증했다|시사한다|의의를\s*지닌다)"),
            re.compile(r"^[A-Z][^.!?]{20,180}(?:\s+[가-힣])"),
            re.compile(r"[\"“][^\"”]{12,}[\"”]"),
        )
    )
    return markers >= 1


def summary_has_lab_intro_context(text: str) -> bool:
    value = clean_text(text)
    return bool(
        re.search(
            r"(?:본\s*연구실|우리\s*연구실|연구실(?:에서는|은|에서)|"
            r"research\s+laboratory|our\s+lab|the\s+lab\s+(?:focus|stud|develop)|"
            r"laboratory\s+(?:focus|involved|conduct|stud)|"
            r"(?:은|는)\s+[^.]{2,80}\s+분야(?:입니다|이다))",
            value,
            re.I,
        )
    )


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
    if (
        cleaned["research_summary"]
        and summary_looks_like_news_article(cleaned["research_summary"])
        and not summary_has_lab_intro_context(cleaned["research_summary"])
    ):
        cleaned["research_summary"] = ""
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



def remove_repeated_generic_values(rows: list[dict[str, str]], report: CleanReport) -> None:
    """Remove page-wide text accidentally copied into many professor rows."""
    lab_name_groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    summary_groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        lab_name = clean_text(row.get("lab_name_kor", ""))
        if lab_name:
            lab_name_groups[lab_name.casefold()].append(row)
        summary = clean_text(row.get("research_summary", ""))
        if summary:
            summary_groups[summary.casefold()].append(row)

    for group in lab_name_groups.values():
        professor_ids = {normalize_email(row.get("email", "")) or row.get("researcher_id", "") for row in group}
        departments = {normalized_department_name(row.get("department_name", "")) for row in group}
        value = clean_text(group[0].get("lab_name_kor", ""))
        compact_generic = bool(re.fullmatch(r"(?i)[a-z0-9_-]{2,14}\s*lab", value)) or value.casefold() in {
            "rllab", "lab", "research lab", "laboratory"
        }
        english_generic = bool(
            re.fullmatch(r"(?i)[a-z][a-z0-9&+\- ]{1,60}\s+(?:lab|laboratory)", value)
            and len(value.split()) <= 5
        )
        distinct_urls = {
            normalize_url(row.get("lab_url", ""))
            for row in group
            if normalize_url(row.get("lab_url", ""))
        }
        distinct_fields = {
            canonical_output_text(row.get("primary_field", ""))
            for row in group
            if canonical_output_text(row.get("primary_field", ""))
        }
        repeated_wrapper_title = (
            len(professor_ids) >= 3
            and len(distinct_urls) >= 3
            and len(distinct_fields) >= 3
        )
        trusted_group_rows = [
            row for row in group
            if normalize_url(row.get("lab_url", ""))
            and clean_text(row.get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES
        ]
        shared_single_trusted_url = (
            len(distinct_urls) == 1
            and len(trusted_group_rows) == len(group)
            and shared_lab_group_is_verified(trusted_group_rows)
        )
        plausible_shared_url_group = (
            len(distinct_urls) == 1
            and all(normalize_url(row.get("lab_url", "")) for row in group)
        )
        repeated_generic = (
            not shared_single_trusted_url
            and not plausible_shared_url_group
            and (
                (len(professor_ids) >= 4 and len(departments) >= 2 and compact_generic)
                or (len(professor_ids) >= 3 and (compact_generic or english_generic))
                or repeated_wrapper_title
            )
        )
        if repeated_generic:
            for row in group:
                provenance = parse_json_dict(row.get("field_provenance", ""))
                name_evidence = provenance.get("lab_name_kor", {})
                name_evidence = name_evidence if isinstance(name_evidence, dict) else {}
                source_url = normalize_url(name_evidence.get("source_url", ""))
                method = clean_text(name_evidence.get("method", ""))
                strong_distinct_evidence = bool(
                    len(distinct_urls) >= len(group)
                    and source_url
                    and is_official_postech_source(source_url)
                    and "exact_email" in method
                )
                if shared_single_trusted_url or strong_distinct_evidence:
                    continue
                professor = clean_text(row.get("professor_name", ""))
                previous_kor = clean_text(row.get("lab_name_kor", ""))
                previous_eng = clean_text(row.get("lab_name_eng", ""))
                row["lab_name_kor"] = f"{professor} 교수 연구실" if professor else ""
                if previous_eng.casefold() == previous_kor.casefold() or previous_eng.casefold().startswith(previous_kor.casefold() + " @"):
                    row["lab_name_eng"] = ""
                if clean_text(row.get("lab_name_kor", "")) != previous_kor:
                    report.duplicate_noise["generic_lab_name"] += 1
                    report.changed_fields["lab_name_kor"] += 1
                if clean_text(row.get("lab_name_eng", "")) != previous_eng:
                    report.changed_fields["lab_name_eng"] += 1

    for group in summary_groups.values():
        professor_ids = {normalize_email(row.get("email", "")) or row.get("researcher_id", "") for row in group}
        if len(professor_ids) < 3:
            continue
        # An identical prose paragraph assigned to three or more different
        # professors is almost always a department/page introduction.
        for row in group:
            row["research_summary"] = ""
            report.duplicate_noise["generic_research_summary"] += 1
            report.changed_fields["research_summary"] += 1


def remove_other_professor_names_from_fields(rows: list[dict[str, str]], report: CleanReport) -> None:
    known_display_names = {
        clean_professor_name(row.get("professor_name", ""), row.get("department_name", ""))
        for row in rows
    }
    known_display_names.discard("")
    for row in rows:
        own = clean_professor_name(row.get("professor_name", ""), row.get("department_name", ""))
        value = clean_text(row.get("primary_field", ""))
        if not value:
            continue
        parts: list[str] = []
        changed = False
        for part in re.split(r"[;|•·\n]+", value):
            part = clean_text(part).strip(" .,:;|-/")
            if not part:
                continue
            if part in known_display_names and part != own:
                changed = True
                continue
            for name in known_display_names:
                if name == own:
                    continue
                new_part = re.sub(rf"(?:^|[;,\s]){re.escape(name)}(?:$|[;,\s])", " ", part)
                new_part = clean_text(new_part).strip(" .,:;|-/")
                if new_part != part:
                    changed = True
                    part = new_part
            if part:
                parts.append(part)
        new_value = "; ".join(unique_preserve_order(parts))[:MAX_PRIMARY_FIELD_CHARS]
        if changed and new_value != value:
            row["primary_field"] = clean_primary_field_value(new_value)
            report.duplicate_noise["primary_field_professor_name"] += 1
            report.changed_fields["primary_field"] += 1


def authoritative_department_hosts(
    department: dict[str, str],
    override: dict,
) -> set[str]:
    hosts: set[str] = set()
    for url in (
        department.get("homepage_url", ""),
        department.get("detail_url", ""),
        *override.get("faculty_urls", []),
    ):
        host = hostname(normalize_url(clean_text(url)))
        if host:
            hosts.add(host.removeprefix("www."))
    for raw in override.get("allowed_hosts", []):
        host = clean_text(raw).lower().removeprefix("*.").removeprefix("www.")
        if host:
            hosts.add(host)
    return hosts


def reset_stale_cross_identity_contamination(
    departments: list[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
    overrides: dict,
) -> Counter[str]:
    """Remove persisted cross-identity values from homonymous professor rows.

    Old runs could first add a false secondary affiliation, then use that
    affiliation to make a name-only match on a different department page. Once
    a plausible-looking field was stored, quality-based merging preserved it.
    This routine is deliberately conservative: when two different e-mails share
    an identical identity field, the copied value is removed from every affected
    row and must be reacquired from an exact-email primary source.
    """
    department_by_id = {
        clean_text(row.get("department_id", "")): row
        for row in departments
        if clean_text(row.get("department_id", ""))
    }
    hosts_by_department_id: dict[str, set[str]] = {}
    for department_id, department in department_by_id.items():
        hosts_by_department_id[department_id] = authoritative_department_hosts(
            department,
            resolve_department_override(overrides, department),
        )

    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labs_by_id.values():
        name = normalize_name(row.get("professor_name", ""))
        if name:
            groups[name].append(row)

    report: Counter[str] = Counter()
    comparable_fields = (
        "lab_name_kor",
        "lab_name_eng",
        "phone",
        "location",
        "primary_field",
        "research_summary",
    )

    for group in groups.values():
        distinct_emails = {
            normalize_email(row.get("email", ""))
            for row in group
            if normalize_email(row.get("email", ""))
        }
        if len(distinct_emails) < 2:
            continue

        shared_values: dict[str, set[str]] = {}
        shared_phrases: set[str] = set()
        for field_name in comparable_fields:
            value_rows: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
            for row in group:
                value = clean_text(row.get(field_name, ""))
                if not value:
                    continue
                if field_name == "lab_name_kor" and looks_placeholder_lab_name(value):
                    continue
                value_rows[value.casefold()].append(row)
            duplicates = {value for value, owners in value_rows.items() if len(owners) >= 2}
            if duplicates:
                shared_values[field_name] = duplicates
                shared_phrases.update(value for value in duplicates if len(value) >= 8)

        group_has_copy_signal = bool(shared_values)
        for row in group:
            primary_id = clean_text(row.get("primary_department_id", "") or row.get("department_id", ""))
            own_hosts = hosts_by_department_id.get(primary_id, set())
            page_host = hostname(row.get("department_page_url", "")).removeprefix("www.")
            foreign_page = bool(page_host and page_host not in own_hosts)

            for field_name, duplicate_values in shared_values.items():
                value = clean_text(row.get(field_name, ""))
                if value and value.casefold() in duplicate_values:
                    row[field_name] = ""
                    report[field_name] += 1

            # A copied research-field sentence often survives with a prefix such
            # as "주요 연구 분야:". Remove it when it embeds a duplicated value.
            summary = clean_text(row.get("research_summary", ""))
            if summary and any(phrase in summary.casefold() for phrase in shared_phrases):
                row["research_summary"] = ""
                report["research_summary"] += 1

            # In a homonym group, a lab URL acquired from a foreign department
            # page cannot be validated by name alone. Exact-email recrawling must
            # re-establish it. Manual URLs remain untouched.
            if foreign_page and group_has_copy_signal and row.get("lab_url_status") != "manual":
                if clean_text(row.get("lab_url", "")):
                    row["lab_url"] = ""
                    row["lab_url_status"] = "invalid"
                    report["lab_url"] += 1

            # Remove keyword items copied verbatim from another homonymous row.
            other_tokens: set[str] = set()
            for other in group:
                if other is row:
                    continue
                other_tokens.update(item.casefold() for item in split_multi(other.get("keywords", "")))
                other_tokens.update(item.casefold() for item in split_multi(other.get("primary_field", "")))
            current_tokens = split_multi(row.get("keywords", ""))
            kept_tokens = [item for item in current_tokens if item.casefold() not in other_tokens]
            new_keywords = ";".join(unique_preserve_order(kept_tokens)[:MAX_KEYWORDS])
            if new_keywords != clean_text(row.get("keywords", "")):
                row["keywords"] = new_keywords
                report["keywords"] += 1

            if foreign_page:
                row["department_page_url"] = ""
                row["enrichment_source_urls"] = sanitize_enrichment_source_urls(
                    {**row, "department_page_url": "", "enrichment_source_urls": ""}
                )
                report["department_page_url"] += 1
                report["enrichment_source_urls"] += 1

            if not clean_text(row.get("lab_name_kor", "")):
                professor = clean_text(row.get("professor_name", ""))
                row["lab_name_kor"] = f"{professor} 교수 연구실" if professor else ""
            if group_has_copy_signal or foreign_page:
                row["enrichment_status"] = "pending"
                row["enrichment_message"] = "동명이인 교차오염 제거 후 정확 이메일 기반 재수집 대기"

    return report


def clean_all_labs(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], CleanReport]:
    originals = {clean_text(row.get("lab_id", "")): dict(row) for row in rows}
    report = CleanReport()
    cleaned = [clean_existing_lab_row(row, report) for row in rows]
    remove_duplicate_lab_urls(cleaned, report)
    remove_duplicate_profile_images(cleaned, report)
    remove_professor_name_keywords(cleaned, report)
    remove_other_professor_names_from_fields(cleaned, report)
    remove_cross_department_contamination(cleaned, report)
    remove_repeated_generic_values(cleaned, report)
    for row in cleaned:
        row["data_quality_status"] = data_quality_status(row)

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
            # A generic research/news page is not a faculty source. It may add
            # a weak hint, but cannot enter the crawl queue by itself.
            score += 1
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
    if not href or is_non_identity_source_url(href):
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


def department_match_count_within_limit(override: dict, count: int) -> bool:
    """Return False only when an explicit positive safety limit is exceeded."""
    raw_limit = override.get("max_total_matches")
    if raw_limit in (None, ""):
        return True
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return True
    return limit < 1 or count <= limit


def rollback_department_if_scope_overflow(
    override: dict,
    match_count: int,
    department: dict[str, str],
    labs_by_id: dict[str, dict[str, str]],
    labs_snapshot: Optional[dict[str, dict[str, str]]],
    touched_lab_ids: set[str],
    touched_snapshot: Optional[set[str]],
) -> bool:
    """Transactionally undo one department when a scope leak is detected."""
    if department_match_count_within_limit(override, match_count):
        return False
    if labs_snapshot is None or touched_snapshot is None:
        raise RuntimeError("범위 상한이 설정된 학과에 롤백 스냅샷이 없습니다.")
    max_matches = int(override["max_total_matches"])
    labs_by_id.clear()
    labs_by_id.update(deepcopy(labs_snapshot))
    touched_lab_ids.clear()
    touched_lab_ids.update(touched_snapshot)
    department["faculty_page_urls"] = ""
    department["faculty_match_count"] = "0"
    department["enrichment_status"] = "scope_overflow"
    department["enrichment_message"] = (
        f"안전 상한 초과로 학과 단위 변경 전체 롤백: "
        f"매칭 {match_count}명 > 상한 {max_matches}명"
    )
    department["enriched_at"] = now_iso()
    department["enricher_version"] = ENRICHER_VERSION
    return True


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


def override_scope_query_params(override: dict) -> dict[str, set[str]]:
    """Return strict query-parameter constraints declared by site_overrides.json.

    Shared POSTECH portals use the same host and path for multiple programs.
    Without a query scope guard, the crawler can follow sibling-program tabs
    and incorrectly add every professor to every affiliated_programs value.
    """
    raw = override.get("scope_query_params", {})
    if not isinstance(raw, dict):
        return {}
    result: dict[str, set[str]] = {}
    for key, values in raw.items():
        key = clean_text(key)
        if not key:
            continue
        if isinstance(values, (str, int, float)):
            values = [values]
        if not isinstance(values, (list, tuple, set)):
            continue
        normalized = {clean_text(value) for value in values if clean_text(value)}
        if normalized:
            result[key] = normalized
    return result


def url_matches_override_scope(url: str, override: dict) -> bool:
    constraints = override_scope_query_params(override)
    if not constraints:
        return True
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    for key, allowed_values in constraints.items():
        actual_values = {clean_text(value) for value in query.get(key, []) if clean_text(value)}
        if not actual_values or actual_values.isdisjoint(allowed_values):
            return False
    return True


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
    follow_links = bool(override.get("follow_links", True))

    def host_allowed(url: str) -> bool:
        host = hostname(url)
        if not host or not url_matches_override_scope(url, override):
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

        # Redirects on shared portals can silently drop or change the department
        # query parameter. Reject the final URL before parsing or affiliation merge.
        if not host_allowed(result.url):
            append_jsonl(
                paths.log,
                {
                    "timestamp": now_iso(),
                    "level": "scope_rejected",
                    "department_id": department.get("department_id", ""),
                    "department_type": department.get("department_type", ""),
                    "department": department.get("department_name_kor", ""),
                    "requested_url": url,
                    "final_url": result.url,
                    "message": "최종 URL이 site_overrides scope_query_params 범위를 벗어남",
                    "enricher_version": ENRICHER_VERSION,
                },
            )
            print(f"    [SCOPE-REJECT] {result.url}")
            continue

        results.append(result)
        save_raw_html(paths, department.get("department_id", "UNKNOWN"), len(results), result, save_raw)
        soup = result.soup
        content_score = page_content_score(soup, known_names)
        print(
            f"    [PAGE] {len(results):02d}/{max_pages:02d} | "
            f"내용점수={content_score:02d} | {result.method} | {result.url}"
        )

        if depth < max(local_max_depth, 1) and override_scope_query_params(override):
            # Shared portals often separate 전임/겸임/연구/대우교수 by a
            # numeric ``position`` query while displaying all category links in
            # the same navigation. Follow only professor-category URLs that keep
            # the exact department scope; sibling departments remain rejected.
            for anchor in soup.find_all("a"):
                href = anchor_target_url(result.url, anchor)
                if not href or not host_allowed(href) or is_non_identity_source_url(href):
                    continue
                query = parse_qs(urlparse(href).query, keep_blank_values=True)
                if clean_text((query.get("sub") or [""])[0]) != "professor":
                    continue
                position = clean_text((query.get("position") or [""])[0])
                if position and re.fullmatch(r"\d{1,2}", position):
                    push(href, 1800, depth + 1)

        if depth >= local_max_depth or not follow_links:
            continue

        for iframe_url in iter_iframe_urls(soup, result.url):
            if host_allowed(iframe_url):
                push(iframe_url, 900, depth + 1)

        faculty_hub = is_faculty_hub_page(soup, known_names)
        for anchor in soup.find_all("a"):
            href = anchor_target_url(result.url, anchor)
            if not href or not host_allowed(href) or is_non_identity_source_url(href):
                continue
            score = page_link_score(anchor.get_text(" ", strip=True), href)
            if faculty_hub and is_profile_detail_link(anchor, href, known_names):
                score = max(score, 24)
            elif faculty_hub and is_pagination_link(anchor, result.url, href):
                score = max(score, 18)
            minimum_link_score = max(3, int(override.get("min_link_score", 5)))
            if score >= minimum_link_score:
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
        emails = set(node_emails(current)) | extract_identity_emails(text)
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

    max_card_emails = max(1, int(override.get("max_card_emails", 2)))
    max_card_identities = max(1, int(override.get("max_card_identities", 2)))

    for card in cards:
        card_text = clean_text(card.get_text(" ", strip=True))
        emails = card_candidate_emails(card, email_selectors)
        # A selector accidentally targeting the list wrapper or page body must
        # never be treated as one professor card.
        if len(emails) > max_card_emails:
            continue
        if visible_identity_count(card_text, normalized_known_names) > max_card_identities:
            continue
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

    # Name-only matching is allowed only on a faculty hub or profile-like URL,
    # and only when the normalized professor name is globally unique. This
    # prevents news/research articles mentioning a professor from becoming a
    # pseudo faculty card.
    page_text = clean_text(soup.get_text(" ", strip=True))
    normalized_page_text = normalize_name(page_text)
    parsed_result_url = urlparse(result.url)
    page_is_identity_source = bool(
        is_faculty_hub_page(soup, normalized_known_names)
        or PROFILE_DETAIL_PATH_RE.search(parsed_result_url.path)
        or any(token in parsed_result_url.path.casefold() for token in PROFILE_PATH_HINTS)
        or any(key in parse_qs(parsed_result_url.query) for key in PROFILE_DETAIL_QUERY_KEYS)
    )
    if not page_is_identity_source:
        return list(matches.values())
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
    scored: list[tuple[int, int, str]] = []
    selectors = (
        ("h1", 40), ("header h2", 34), (".site-title", 32),
        (".site_name", 32), (".logo", 24), ("title", 20),
    )
    for raw in [meta_content(soup, ("og:title", "twitter:title", "application-name"))]:
        cleaned = clean_lab_name(strip_site_suffix(raw), "")
        if cleaned:
            scored.append((24, len(cleaned), cleaned))
    for selector, base_score in selectors:
        try:
            nodes = soup.select(selector)
        except Exception:
            continue
        for node in nodes:
            cleaned = clean_lab_name(strip_site_suffix(node.get_text(" ", strip=True)), "")
            if not cleaned:
                continue
            score = base_score
            if re.search(r"(?i)(?:laboratory|\blab\b|research group|연구실|연구그룹)", cleaned):
                score += 12
            if len(cleaned.split()) >= 2:
                score += 4
            scored.append((score, len(cleaned), cleaned))
    if not scored:
        return ""
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2]

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
    ambiguous_name = bool(lab.get("_name_is_ambiguous", False))
    identity_conflict = bool(
        unrelated_postech_emails
        and not email_exact
        and (ambiguous_name or not name_exact)
    )

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
    if ambiguous_name and not email_exact:
        # A duplicate display name is not identity evidence. Require the exact
        # professor e-mail before exposing a homepage as verified.
        score = min(score, 7)
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
# 9B. Lab-link-first discovery and verification
# ============================================================
def deobfuscate_email_text(value: str) -> str:
    """Normalize conservative e-mail obfuscations used on official pages."""
    text = str(value or "")
    text = re.sub(r"(?i)(?<=\w)\s*(?:_AT_|\[at\]|\(at\)|\s+at\s+)\s*(?=\w)", "@", text)
    text = re.sub(r"(?i)(?<=\w)\s*(?:_DOT_|\[dot\]|\(dot\)|\s+dot\s+)\s*(?=\w)", ".", text)
    return text


def extract_identity_emails(value: str) -> set[str]:
    normalized = deobfuscate_email_text(value)
    return {
        normalize_email(match.group(0))
        for match in EMAIL_RE.finditer(normalized)
        if normalize_email(match.group(0))
    }


def is_official_postech_source(url: str) -> bool:
    host = hostname(url).removeprefix("www.")
    return bool(host == "postech.ac.kr" or host.endswith(".postech.ac.kr"))


def canonical_url_key(url: str) -> str:
    normalized = normalize_url(url)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    host = parsed.hostname.lower().removeprefix("www.") if parsed.hostname else ""
    port = parsed.port
    netloc = host if not port or port in {80, 443} else f"{host}:{port}"
    query = parse_qs(parsed.query, keep_blank_values=True)
    tracking_prefixes = ("utm_", "fbclid", "gclid", "ref", "source")
    kept_pairs: list[tuple[str, str]] = []
    for key in sorted(query):
        if key.casefold().startswith(tracking_prefixes):
            continue
        for item in sorted(query[key]):
            kept_pairs.append((key, item))
    query_text = "&".join(
        f"{requests.utils.quote(key, safe='')}={requests.utils.quote(item, safe='')}"
        for key, item in kept_pairs
    )
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", query_text, ""))


def department_reference_url_keys(departments: Sequence[dict[str, str]]) -> set[str]:
    keys: set[str] = set()
    for department in departments:
        for field_name in ("homepage_url", "detail_url", "source_url", "faculty_page_urls"):
            for raw in split_multi(department.get(field_name, "")):
                key = canonical_url_key(raw)
                if key:
                    keys.add(key)
    return keys


def lab_name_is_actual(row: dict[str, str]) -> bool:
    professor = clean_text(row.get("professor_name", ""))
    kor = clean_lab_name(row.get("lab_name_kor", ""), professor)
    eng = clean_lab_name(row.get("lab_name_eng", ""), professor)
    return bool((kor and not looks_placeholder_lab_name(kor)) or eng)


def lab_url_provenance(row: dict[str, str]) -> dict:
    provenance = parse_json_dict(row.get("field_provenance", ""))
    value = provenance.get("lab_url", {})
    return value if isinstance(value, dict) else {}


def lab_url_provenance_complete(row: dict[str, str]) -> bool:
    """Return True only when a trusted URL has reproducible source evidence."""
    evidence = lab_url_provenance(row)
    return all(clean_text(evidence.get(key, "")) for key in (
        "source_url", "verified_url", "method", "verified_at",
    ))


def migrate_legacy_lab_url_provenance(row: dict[str, str]) -> bool:
    """Complete legacy link evidence without inventing a new verification event.

    Older versions stored source_url/method/verified_at but omitted verified_url.
    The row's already trusted lab_url is the verified object referenced by that
    evidence, so copying it into verified_url is a schema migration, not a new
    network-verification claim. Evidence-free rows remain untouched and are
    queued for real revalidation.
    """
    url = normalize_url(row.get("lab_url", ""))
    status = clean_text(row.get("lab_url_status", ""))
    if not url or status not in TRUSTED_LAB_URL_STATUSES:
        return False
    provenance = parse_json_dict(row.get("field_provenance", ""))
    evidence = provenance.get("lab_url")
    if not isinstance(evidence, dict) or not evidence:
        return False
    changed = False
    if not normalize_url(evidence.get("verified_url", "")):
        evidence["verified_url"] = url
        changed = True
    if not normalize_url(evidence.get("source_url", "")):
        # Only use the homepage itself when the historic method explicitly says
        # the homepage was checked. Otherwise source provenance is still unknown.
        method = clean_text(evidence.get("method", ""))
        if method.startswith("homepage_") or method == "manual_override":
            evidence["source_url"] = url
            changed = True
    if changed:
        provenance["lab_url"] = evidence
        row["field_provenance"] = compact_json(provenance)
    return changed


def reconstruct_missing_lab_url_provenance(row: dict[str, str]) -> bool:
    """Recover a lost provenance object from surviving same-row evidence.

    This is intentionally strict: the URL must already be trusted, the exact lab
    URL must occur in enrichment_source_urls, and an official professor/profile
    or department page must survive in the same row. The method name explicitly
    records that this is a provenance reconstruction rather than a new fetch.
    """
    url = normalize_url(row.get("lab_url", ""))
    status = clean_text(row.get("lab_url_status", ""))
    if not url or status not in TRUSTED_LAB_URL_STATUSES or lab_url_provenance(row):
        return False
    source_candidates = [
        normalize_url(row.get("department_page_url", "")),
        normalize_url(row.get("professor_profile_url", "")),
        normalize_url(row.get("source_url", "")),
    ]
    source_url = next((item for item in source_candidates if item and is_official_postech_source(item)), "")
    enrichment_urls = {canonical_url_key(item) for item in split_multi(row.get("enrichment_source_urls", "")) if normalize_url(item)}
    if not source_url or canonical_url_key(url) not in enrichment_urls:
        return False
    stamp = clean_text(row.get("enriched_at", "") or row.get("crawled_at", "")) or now_iso()
    provenance = parse_json_dict(row.get("field_provenance", ""))
    provenance["lab_url"] = {
        "scope": "lab_homepage" if status == "verified_homepage" else "department_page",
        "source_url": source_url,
        "verified_url": url,
        "method": "legacy_trusted_link_reconstructed_from_official_identity_and_enrichment_sources",
        "source_kind": "legacy_provenance_reconstruction",
        "verified_at": stamp,
        "reconstructed_at": now_iso(),
    }
    row["field_provenance"] = compact_json(provenance)
    return True


def migrate_all_legacy_lab_url_provenance(
    labs_by_id: dict[str, dict[str, str]],
) -> int:
    changed = 0
    for row in labs_by_id.values():
        changed += int(migrate_legacy_lab_url_provenance(row))
        changed += int(reconstruct_missing_lab_url_provenance(row))
    return changed


PROTECTED_LINK_FIELDS = (
    "lab_url", "lab_url_status", "lab_name_kor", "lab_name_eng",
    "field_provenance", "professor_profile_url", "department_page_url",
    "enrichment_source_urls",
)


def snapshot_protected_link_fields(
    labs_by_id: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    return {
        lab_id: {field: row.get(field, "") for field in PROTECTED_LINK_FIELDS}
        for lab_id, row in labs_by_id.items()
    }


def restore_unexplained_link_regressions(
    labs_by_id: dict[str, dict[str, str]],
    snapshot: dict[str, dict[str, str]],
) -> Counter[str]:
    """Restore link/name evidence lost without an explicit invalidation reason.

    A rebuild may replace a value with stronger evidence, but it may not silently
    erase a usable URL, downgrade a trusted status, remove complete provenance,
    or replace an actual lab name with a placeholder. Known false positives are
    already marked invalid before this guard runs and are therefore not restored.
    """
    report: Counter[str] = Counter()
    for lab_id, before in snapshot.items():
        row = labs_by_id.get(lab_id)
        if not row:
            continue
        before_url = normalize_url(before.get("lab_url", ""))
        after_url = normalize_url(row.get("lab_url", ""))
        before_status = clean_text(before.get("lab_url_status", ""))
        after_status = clean_text(row.get("lab_url_status", ""))
        explicit_invalid = after_status == "invalid"
        if before_url and not after_url and not explicit_invalid:
            for field in ("lab_url", "lab_url_status"):
                row[field] = before.get(field, "")
            report["url_restored"] += 1
        elif before_url and after_url == before_url and lab_url_status_rank(after_status) < lab_url_status_rank(before_status) and not explicit_invalid:
            row["lab_url_status"] = before_status
            report["status_restored"] += 1

        before_prov = before.get("field_provenance", "")
        if before_prov and not row.get("field_provenance", ""):
            row["field_provenance"] = before_prov
            report["provenance_restored"] += 1
        else:
            before_item = parse_json_dict(before_prov).get("lab_url", {})
            after_item = lab_url_provenance(row)
            if isinstance(before_item, dict) and before_item and not after_item:
                provenance = parse_json_dict(row.get("field_provenance", ""))
                provenance["lab_url"] = before_item
                row["field_provenance"] = compact_json(provenance)
                report["link_provenance_restored"] += 1

        before_actual = bool(
            clean_text(before.get("lab_name_kor", ""))
            and not looks_placeholder_lab_name(before.get("lab_name_kor", ""))
        )
        after_actual = bool(
            clean_text(row.get("lab_name_kor", ""))
            and not looks_placeholder_lab_name(row.get("lab_name_kor", ""))
        )
        if before_actual and not after_actual and clean_text(row.get("lab_url_status", "")) != "invalid":
            row["lab_name_kor"] = before.get("lab_name_kor", "")
            row["lab_name_eng"] = before.get("lab_name_eng", "")
            report["lab_name_restored"] += 1
    return report


def lab_link_source_priority(candidate: LabLinkCandidate) -> int:
    kind = clean_text(candidate.source_kind)
    source_url = normalize_url(candidate.source_url)
    if kind == "professor_profile" and is_aif_researcher_listing(source_url):
        kind = "aif_researcher_index"
    elif kind == "professor_profile" and CENTRAL_RESEARCHER_PATH_TOKEN in urlparse(source_url).path:
        kind = "aif_researcher_detail"
    return LAB_LINK_SOURCE_PRIORITY.get(kind, 250)


def candidate_preference_key(candidate: LabLinkCandidate) -> tuple[int, int, int, int, int]:
    return (
        lab_link_source_priority(candidate),
        int(candidate.exact_email),
        int(candidate.exact_name),
        int(candidate.score),
        -len(candidate.url),
    )


def verified_candidate_preference_key(
    update: dict[str, str], candidate: LabLinkCandidate, method: str,
) -> tuple[int, int, int, int, int, int]:
    status = clean_text(update.get("lab_url_status", ""))
    trusted = int(status in TRUSTED_LAB_URL_STATUSES)
    method_strength = 3 if "exact_email" in method else 2 if "email" in method else 1 if "name" in method else 0
    return (
        trusted,
        lab_link_source_priority(candidate),
        lab_url_status_rank(status),
        method_strength,
        int(candidate.exact_email),
        int(candidate.score),
    )


def shared_lab_evidence(row: dict[str, str]) -> dict:
    evidence = lab_url_provenance(row).get("shared_lab_verified", {})
    return evidence if isinstance(evidence, dict) else {}


def shared_lab_group_is_verified(rows: Sequence[dict[str, str]]) -> bool:
    if len(rows) < 2:
        return True
    urls = {canonical_url_key(row.get("lab_url", "")) for row in rows}
    emails = sorted({normalize_email(row.get("email", "")) for row in rows if normalize_email(row.get("email", ""))})
    if len(urls) != 1 or not emails:
        return False
    expected_url = next(iter(urls))
    for row in rows:
        evidence = shared_lab_evidence(row)
        evidence_emails = sorted({normalize_email(item) for item in evidence.get("professor_emails", []) if normalize_email(item)})
        if canonical_url_key(evidence.get("verified_url", "")) != expected_url or evidence_emails != emails:
            return False
        if clean_text(evidence.get("method", "")) not in {
            "shared_homepage_multiple_exact_emails",
            "shared_official_cards_multiple_exact_emails",
        }:
            return False
    return True


def mark_shared_lab_verified(rows: Sequence[dict[str, str]]) -> int:
    """Attach explicit shared-group evidence when every professor has exact-email proof."""
    if len(rows) < 2:
        return 0
    urls = {canonical_url_key(row.get("lab_url", "")) for row in rows}
    departments = {clean_text(row.get("primary_department_id", "") or row.get("department_id", "")) for row in rows}
    if len(urls) != 1 or len(departments) != 1:
        return 0
    verified_url = normalize_url(rows[0].get("lab_url", ""))
    emails = sorted({normalize_email(row.get("email", "")) for row in rows if normalize_email(row.get("email", ""))})
    names = sorted({clean_text(row.get("professor_name", "")) for row in rows if clean_text(row.get("professor_name", ""))})
    if len(emails) != len(rows):
        return 0
    methods = [clean_text(lab_url_provenance(row).get("method", "")) for row in rows]
    exact_homepage = all("homepage_exact_email" in method for method in methods)
    exact_cards = all("exact_email" in method for method in methods)
    if not (exact_homepage or exact_cards):
        return 0
    method = "shared_homepage_multiple_exact_emails" if exact_homepage else "shared_official_cards_multiple_exact_emails"
    stamp = max((clean_text(lab_url_provenance(row).get("verified_at", "")) for row in rows), default="") or now_iso()
    changed = 0
    for row in rows:
        provenance = parse_json_dict(row.get("field_provenance", ""))
        link = provenance.get("lab_url", {}) if isinstance(provenance.get("lab_url", {}), dict) else {}
        shared = {
            "verified_url": verified_url,
            "professor_emails": emails,
            "professor_names": names,
            "method": method,
            "verified_at": stamp,
        }
        if link.get("shared_lab_verified") != shared:
            link["shared_lab_verified"] = shared
            provenance["lab_url"] = link
            row["field_provenance"] = compact_json(provenance)
            changed += 1
    return changed


def mark_all_verified_shared_lab_groups(labs_by_id: dict[str, dict[str, str]]) -> int:
    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labs_by_id.values():
        if normalize_url(row.get("lab_url", "")) and clean_text(row.get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES:
            groups[canonical_url_key(row.get("lab_url", ""))].append(row)
    return sum(mark_shared_lab_verified(group) for group in groups.values() if len(group) >= 2)


def lab_link_revalidation_required(row: dict[str, str], refresh_all: bool = False) -> bool:
    url = normalize_url(row.get("lab_url", ""))
    status = clean_text(row.get("lab_url_status", ""))
    return bool(
        url
        and status != "invalid"
        and (
            refresh_all
            or status not in TRUSTED_LAB_URL_STATUSES
            or not lab_url_provenance_complete(row)
        )
    )


def lab_link_target_required(row: dict[str, str], refresh_all: bool = False) -> bool:
    url = normalize_url(row.get("lab_url", ""))
    status = clean_text(row.get("lab_url_status", ""))
    return bool(
        refresh_all
        or not url
        or status not in TRUSTED_LAB_URL_STATUSES
        or not lab_name_is_actual(row)
        or (url and not lab_url_provenance_complete(row))
    )


def known_professor_identity_counts(text: str, known_emails: set[str], known_names: set[str]) -> tuple[int, int]:
    emails = extract_identity_emails(text) & known_emails
    normalized_text = normalize_name(text)
    names = {name for name in known_names if len(name) >= 2 and name in normalized_text}
    return len(emails), len(names)


def sanitize_existing_lab_link_records(
    departments: Sequence[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
) -> dict[str, object]:
    department_keys = department_reference_url_keys(departments)
    invalidated: list[dict[str, str]] = []
    names_cleaned = 0
    names_promoted = 0
    provenance_missing = 0
    provenance_incomplete = 0
    manual_provenance_backfilled = 0
    for lab in labs_by_id.values():
        professor = clean_text(lab.get("professor_name", ""))
        url = normalize_url(lab.get("lab_url", ""))
        status = clean_text(lab.get("lab_url_status", ""))
        if url and canonical_url_key(url) in department_keys and status != "manual":
            invalidated.append({
                "lab_id": clean_text(lab.get("lab_id", "")),
                "professor_name": professor,
                "url": url,
                "reason": "known_department_page",
            })
            lab["lab_url"] = ""
            lab["lab_url_status"] = "unverified"
            # Keep the URL as discovery provenance only when it is also this
            # professor's department_page_url. Otherwise remove the false lab
            # homepage candidate immediately so a second clean pass is stable.
            invalid_key = canonical_url_key(url)
            department_page_key = canonical_url_key(lab.get("department_page_url", ""))
            if invalid_key != department_page_key:
                retained_sources = [
                    source for source in split_multi(lab.get("enrichment_source_urls", ""))
                    if canonical_url_key(source) != invalid_key
                ]
                lab["enrichment_source_urls"] = merge_multi(*retained_sources)
            provenance = parse_json_dict(lab.get("field_provenance", ""))
            provenance.pop("lab_url", None)
            provenance.pop("lab_url_status", None)
            lab["field_provenance"] = compact_json(provenance)
        elif url and status == "manual" and not lab_url_provenance(lab):
            provenance = parse_json_dict(lab.get("field_provenance", ""))
            stamp = clean_text(lab.get("enriched_at", "")) or now_iso()
            evidence = {
                "scope": "manual", "source_url": url, "verified_url": url,
                "method": "manual_existing", "verified_at": stamp,
            }
            provenance["lab_url"] = dict(evidence)
            provenance["lab_url_status"] = dict(evidence)
            lab["field_provenance"] = compact_json(provenance)
            manual_provenance_backfilled += 1
        elif url and status in TRUSTED_LAB_URL_STATUSES:
            if not lab_url_provenance(lab):
                provenance_missing += 1
            if not lab_url_provenance_complete(lab):
                provenance_incomplete += 1

        original_kor = clean_text(lab.get("lab_name_kor", ""))
        original_eng = clean_text(lab.get("lab_name_eng", ""))
        kor = clean_lab_name(original_kor, professor)
        eng = clean_lab_name(original_eng, professor)
        if (not kor or looks_placeholder_lab_name(kor)) and eng:
            kor = eng
            names_promoted += int(kor != original_kor)
        if not kor and professor:
            kor = f"{professor} 교수 연구실"
        if kor != original_kor or eng != original_eng:
            lab["lab_name_kor"] = kor
            lab["lab_name_eng"] = eng
            names_cleaned += 1
        lab["data_quality_status"] = data_quality_status(lab)
    shared_rows_marked = mark_all_verified_shared_lab_groups(labs_by_id)
    return {
        "department_url_keys": department_keys,
        "invalidated_rows": invalidated,
        "invalidated_count": len(invalidated),
        "names_cleaned": names_cleaned,
        "names_promoted": names_promoted,
        "trusted_without_provenance": provenance_missing,
        "trusted_incomplete_provenance": provenance_incomplete,
        "manual_provenance_backfilled": manual_provenance_backfilled,
        "shared_lab_rows_marked": shared_rows_marked,
    }


def record_lab_link_provenance(
    row: dict[str, str], fields: Iterable[str], candidate: LabLinkCandidate,
    update: dict[str, str], method: str,
) -> None:
    provenance = parse_json_dict(row.get("field_provenance", ""))
    verified_url = normalize_url(update.get("lab_url", candidate.url))
    source_url = normalize_url(candidate.source_url) or verified_url
    stamp = now_iso()
    for field_name in fields:
        if field_name in {
            "enrichment_source_urls", "enrichment_status", "enrichment_message",
            "enriched_at", "enricher_version", "data_quality_status", "field_provenance",
        }:
            continue
        previous = provenance.get(field_name, {})
        previous = dict(previous) if isinstance(previous, dict) else {}
        history = previous.get("history", [])
        history = list(history) if isinstance(history, list) else []
        previous_core = {
            key: previous.get(key, "")
            for key in ("source_url", "verified_url", "method", "verified_at", "source_kind")
            if previous.get(key)
        }
        next_core = {
            "scope": "lab_homepage" if update.get("lab_url_status") == "verified_homepage" else "department_page",
            "source_url": source_url,
            "verified_url": verified_url,
            "method": clean_text(method),
            "source_kind": clean_text(candidate.source_kind),
            "verified_at": stamp,
        }
        if previous_core and any(clean_text(previous_core.get(key, "")) != clean_text(next_core.get(key, "")) for key in ("source_url", "verified_url", "method", "source_kind")):
            history.append(previous_core)
            history = history[-5:]
        shared = previous.get("shared_lab_verified")
        if history:
            next_core["history"] = history
        if isinstance(shared, dict) and shared:
            next_core["shared_lab_verified"] = shared
        provenance[field_name] = next_core
    row["field_provenance"] = compact_json(provenance)


def candidate_url_variants(url: str) -> list[str]:
    normalized = normalize_url(url)
    if not normalized:
        return []
    parsed = urlparse(normalized)
    variants: list[str] = [normalized]
    if parsed.scheme == "http":
        variants.insert(0, urlunparse(parsed._replace(scheme="https")))
    elif parsed.scheme == "https":
        variants.append(urlunparse(parsed._replace(scheme="http")))
    return unique_preserve_order(variants)


def lab_link_context_text(anchor: Tag) -> str:
    parts = [
        clean_text(anchor.get_text(" ", strip=True)),
        clean_text(anchor.get("title", "")),
        clean_text(anchor.get("aria-label", "")),
        clean_text(anchor.get("data-label", "")),
    ]
    parent = anchor.parent if isinstance(anchor.parent, Tag) else None
    if parent is not None:
        parent_text = clean_text(parent.get_text(" ", strip=True))
        if len(parent_text) <= 240:
            parts.append(parent_text)
    previous = anchor.find_previous_sibling()
    if isinstance(previous, Tag):
        parts.append(clean_text(previous.get_text(" ", strip=True)))
    elif isinstance(previous, NavigableString):
        parts.append(clean_text(previous))
    return clean_text(" ".join(parts))[:500]


def lab_link_label_strength(text: str) -> int:
    low = clean_text(text).casefold()
    if any(label.casefold() in low for label in LAB_LINK_STRONG_LABELS):
        return 2
    if any(label.casefold() in low for label in LAB_LINK_WEAK_LABELS):
        return 1
    return 0


def clean_discovered_lab_name(value: str, professor_name: str = "") -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = re.sub(
        r"(?i)^(?:lab(?:oratory)?\s*(?:name)?|research\s+(?:office|laboratory|group)|"
        r"연구실(?:명)?|랩)\s*[:：.\-]?\s*",
        "", text,
    )
    text = re.sub(
        r"\s*[\[(](?:[^\])]{0,50}(?:호|room|rm\.?|office|building|bldg\.?|[A-Z]\d{1,2}[ -]\d{2,4})[^\])]{0,30})[\])]\s*$",
        "", text, flags=re.I,
    )
    return clean_lab_name(text.strip(" .,:;|-/"), professor_name)

def extract_labeled_lab_name_from_block(block: Tag, professor_name: str) -> str:
    lines = [clean_text(item) for item in block.stripped_strings if clean_text(item)]
    for index, line in enumerate(lines):
        for label in sorted(LAB_NAME_LABELS, key=len, reverse=True):
            if line.casefold() == label.casefold() and index + 1 < len(lines):
                candidate = clean_discovered_lab_name(lines[index + 1], professor_name)
                if candidate:
                    return candidate
            match = re.match(
                rf"^\s*{re.escape(label)}\s*[:：.\-]?\s*(?P<value>.+?)\s*$",
                line,
                re.I,
            )
            if match:
                candidate = clean_discovered_lab_name(match.group("value"), professor_name)
                if candidate:
                    return candidate
    return clean_discovered_lab_name(candidate_lab_name_from_lines(lines, professor_name), professor_name)


def split_discovered_lab_name(name: str) -> tuple[str, str]:
    text = clean_text(name)
    if not text:
        return "", ""
    korean = bool(re.search(r"[가-힣]", text))
    english = bool(re.search(r"[A-Za-z]", text))
    if korean and english:
        chunks = [clean_text(x) for x in re.split(r"\s*[|/·]\s*|\s*[()]\s*", text) if clean_text(x)]
        kor_chunks = [x for x in chunks if re.search(r"[가-힣]", x)]
        eng_chunks = [x for x in chunks if re.search(r"[A-Za-z]", x) and not re.search(r"[가-힣]", x)]
        return text, eng_chunks[0] if eng_chunks else ""
    if english:
        return text, text
    return text, ""


def score_lab_link_candidate(
    href: str,
    source_url: str,
    context: str,
    exact_email: bool,
    exact_name: bool,
    source_kind: str,
    professor_profile_url: str,
) -> int:
    href = normalize_url(href)
    if not href or href == normalize_url(source_url):
        return -999
    if is_forbidden_lab_url(href, professor_profile_url):
        return -999
    parsed_href = urlparse(href)
    href_host = hostname(href).removeprefix("www.")
    source_host = hostname(source_url).removeprefix("www.")
    href_path = parsed_href.path.rstrip("/") or "/"
    if href_host in {"postech.ac.kr", "aif.postech.ac.kr", "home.postech.ac.kr"} and href_path == "/":
        return -999
    if href_host == source_host and href_path in {"/", "/ko", "/en", "/kor", "/eng"}:
        return -999
    low = f"{context} {href}".casefold()
    score = 0
    strength = lab_link_label_strength(context)
    score += 55 if strength == 2 else 25 if strength == 1 else 0
    if exact_email:
        score += 35
    if exact_name:
        score += 8
    if is_official_postech_source(source_url):
        score += 12
    if source_kind == "professor_profile":
        score += 8
    if href_host != source_host:
        score += 12
    if any(token in low for token in LAB_PATH_HINTS):
        score += 14
    if hostname(href).endswith("postech.ac.kr"):
        score += 5
    if not strength and exact_email and not same_site(href, source_url):
        score += 12
    if any(token in low for token in ("curriculum vitae", " cv ", "google scholar", "orcid", "linkedin")):
        score -= 50
    path_low = urlparse(href).path.casefold()
    if any(token in path_low for token in ("/news", "/notice", "/seminar", "/publication", "/paper")):
        score -= 60
    return score


def extract_lab_link_candidates_from_block(
    lab: dict[str, str],
    block: Tag,
    source_url: str,
    source_kind: str,
    exact_email: bool,
    exact_name: bool,
) -> list[LabLinkCandidate]:
    professor_name = clean_text(lab.get("professor_name", ""))
    professor_profile_url = clean_text(lab.get("professor_profile_url", ""))
    lab_name = extract_labeled_lab_name_from_block(block, professor_name)
    candidates: list[LabLinkCandidate] = []
    seen: set[str] = set()

    for anchor in block.find_all("a"):
        href = anchor_target_url(source_url, anchor)
        context = lab_link_context_text(anchor)
        score = score_lab_link_candidate(
            href,
            source_url,
            context,
            exact_email,
            exact_name,
            source_kind,
            professor_profile_url,
        )
        key = canonical_url_key(href)
        if score <= 0 or not key or key in seen:
            continue
        seen.add(key)
        candidates.append(
            LabLinkCandidate(
                lab_id=clean_text(lab.get("lab_id", "")),
                url=normalize_url(href),
                source_url=normalize_url(source_url),
                source_kind=source_kind,
                evidence_method="official_exact_email_card" if exact_email else "official_unique_name_card",
                score=score,
                label_text=context,
                exact_email=exact_email,
                exact_name=exact_name,
                lab_name=lab_name,
            )
        )

    block_text = deobfuscate_email_text(block.get_text(" ", strip=True))
    url_text = EMAIL_RE.sub(" ", block_text)
    raw_urls: list[str] = []
    raw_urls.extend(match.group(0) for match in URL_RE.finditer(url_text))
    raw_urls.extend(match.group(0) for match in BARE_DOMAIN_RE.finditer(url_text))
    for raw in raw_urls:
        raw = raw.rstrip(".,);]}")
        href = raw if re.match(r"(?i)^https?://", raw) else "https://" + raw.lstrip("/")
        href = normalize_url(href)
        key = canonical_url_key(href)
        if not key or key in seen:
            continue
        context = block_text[max(0, block_text.find(raw) - 80) : block_text.find(raw) + len(raw) + 80]
        score = score_lab_link_candidate(
            href,
            source_url,
            context,
            exact_email,
            exact_name,
            source_kind,
            professor_profile_url,
        )
        if score <= 0:
            continue
        seen.add(key)
        candidates.append(
            LabLinkCandidate(
                lab_id=clean_text(lab.get("lab_id", "")),
                url=href,
                source_url=normalize_url(source_url),
                source_kind=source_kind,
                evidence_method="official_exact_email_text_url" if exact_email else "official_unique_name_text_url",
                score=score,
                label_text=clean_text(context),
                exact_email=exact_email,
                exact_name=exact_name,
                lab_name=lab_name,
            )
        )

    candidates.sort(key=lambda item: (item.score, bool(item.lab_name), -len(item.url)), reverse=True)
    return candidates


def find_text_node_for_email(soup: BeautifulSoup, email: str) -> Optional[NavigableString]:
    local = re.escape(email.split("@", 1)[0])
    pattern = re.compile(local, re.I)
    for node in soup.find_all(string=pattern):
        if email in extract_identity_emails(str(node)):
            return node
        parent_text = clean_text(node.parent.get_text(" ", strip=True)) if isinstance(node.parent, Tag) else str(node)
        if email in extract_identity_emails(parent_text):
            return node
    return None


def collect_lab_link_seed_urls(
    departments: Sequence[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
    target_lab_ids: Optional[set[str]] = None,
) -> list[tuple[int, str, str]]:
    target_lab_ids = set(labs_by_id.keys()) if target_lab_ids is None else set(target_lab_ids)
    target_labs = [labs_by_id[lab_id] for lab_id in target_lab_ids if lab_id in labs_by_id]
    target_department_ids = {
        clean_text(lab.get("primary_department_id", "") or lab.get("department_id", ""))
        for lab in target_labs
        if clean_text(lab.get("primary_department_id", "") or lab.get("department_id", ""))
    }
    target_department_names: set[str] = set()
    for lab in target_labs:
        target_department_names.add(clean_text(lab.get("department_name", "")))
        target_department_names.update(split_multi(lab.get("affiliated_programs", "")))
    target_department_names.discard("")

    seeds: list[tuple[int, str, str]] = []
    for url in LAB_LINK_DIRECTORY_URLS:
        seeds.append((3200, normalize_url(url), "official_directory"))
    for department in departments:
        department_id = clean_text(department.get("department_id", ""))
        department_name = clean_text(department.get("department_name_kor", ""))
        if department_id not in target_department_ids and department_name not in target_department_names:
            continue
        for url in split_multi(department.get("faculty_page_urls", "")):
            seeds.append((4200, normalize_url(url), "department_faculty_page"))
        for field_name, priority in (("homepage_url", 1000), ("detail_url", 900), ("source_url", 800)):
            url = normalize_url(department.get(field_name, ""))
            if url:
                seeds.append((priority, url, "department_source"))
    for lab in target_labs:
        for field_name, priority, kind in (
            ("department_page_url", 5000, "department_profile"),
            ("professor_profile_url", 4800, "professor_profile"),
            ("source_url", 4600, "professor_profile"),
        ):
            url = normalize_url(lab.get(field_name, ""))
            if url:
                seeds.append((priority, url, kind))
        for url in split_multi(lab.get("enrichment_source_urls", "")):
            url = normalize_url(url)
            if url and is_official_postech_source(url) and not is_non_identity_source_url(url):
                seeds.append((4400, url, "enrichment_source"))
    dedup: dict[str, tuple[int, str, str]] = {}
    for priority, url, kind in seeds:
        key = canonical_url_key(url)
        if not key or not is_official_postech_source(url) or is_non_identity_source_url(url):
            continue
        current = dedup.get(key)
        if current is None or priority > current[0]:
            dedup[key] = (priority, url, kind)
    return sorted(dedup.values(), key=lambda item: (-item[0], item[1]))


def individual_lab_identity_sources(lab: dict[str, str], limit: int = 4) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for field_name, kind in (
        ("professor_profile_url", "professor_profile"),
        ("source_url", "professor_profile"),
        ("department_page_url", "department_profile"),
    ):
        url = normalize_url(lab.get(field_name, ""))
        if url:
            candidates.append((url, kind))
    for url in split_multi(lab.get("enrichment_source_urls", "")):
        url = normalize_url(url)
        if url:
            candidates.append((url, "enrichment_source"))
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for url, kind in candidates:
        key = canonical_url_key(url)
        if (
            not key
            or key in seen
            or not is_official_postech_source(url)
            or is_non_identity_source_url(url)
        ):
            continue
        seen.add(key)
        result.append((url, kind))
        if len(result) >= max(1, limit):
            break
    return result



def is_aif_researcher_listing(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    return hostname(url) == "aif.postech.ac.kr" and parsed.path.endswith("/researcher-search.do") and parse_qs(parsed.query).get("mode", ["list"])[0] != "view"


def aif_researcher_list_url(offset: int) -> str:
    return (
        f"{AIF_RESEARCHER_LIST_URL}?article.offset={max(0, int(offset))}"
        f"&articleLimit={AIF_RESEARCHER_PAGE_SIZE}&mode=list"
    )


def build_unique_name_index(labs_by_id: dict[str, dict[str, str]]) -> dict[str, str]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for lab_id, lab in labs_by_id.items():
        key = normalize_name(lab.get("professor_name", ""))
        if key:
            grouped[key].append(lab_id)
    return {key: ids[0] for key, ids in grouped.items() if len(ids) == 1}


def mine_aif_unique_name_cards(
    result: PageResult,
    labs_by_id: dict[str, dict[str, str]],
    unique_name_index: dict[str, str],
    normalized_known_names: set[str],
    candidate_map: defaultdict[str, list[LabLinkCandidate]],
    name_evidence: dict[str, tuple[int, str, str, str]],
) -> int:
    """Recover official AIF cards that omit a visible e-mail but have a unique professor name."""
    if not is_aif_researcher_listing(result.url):
        return 0
    matched = 0
    soup = result.soup
    for anchor in soup.find_all("a"):
        href = anchor_target_url(result.url, anchor)
        query = parse_qs(urlparse(href).query)
        if query.get("mode", [""])[0] != "view" or not query.get("articleNo"):
            continue
        display_name = clean_professor_name(anchor.get_text(" ", strip=True))
        name_key = normalize_name(display_name)
        lab_id = unique_name_index.get(name_key)
        if not lab_id or lab_id not in labs_by_id:
            continue
        lab = labs_by_id[lab_id]
        block = find_person_container(anchor, lab.get("professor_name", ""), "", normalized_known_names)
        # Short list cards can be smaller than the generic container threshold.
        # Climb to the nearest compact ancestor that contains both the detail and Website links.
        if len(block.find_all("a")) < 2:
            current = anchor.parent
            for _ in range(5):
                if not isinstance(current, Tag):
                    break
                current_text = clean_text(current.get_text(" ", strip=True))
                if len(current.find_all("a")) >= 2 and len(current_text) <= 1800 and visible_identity_count(current_text, normalized_known_names) <= 2:
                    block = current
                    break
                current = current.parent
        block_text = deobfuscate_email_text(block.get_text(" ", strip=True))
        # A unique name is accepted only inside one compact official researcher card.
        if len(block_text) > 1800 or visible_identity_count(block_text, normalized_known_names) > 2:
            continue
        lab_name = extract_labeled_lab_name_from_block(block, lab.get("professor_name", ""))
        if lab_name:
            current = name_evidence.get(lab_id)
            if current is None or 80 > current[0]:
                name_evidence[lab_id] = (80, lab_name, result.url, "aif_unique_name_card")
        before = len(candidate_map.get(lab_id, []))
        candidate_map[lab_id].extend(
            extract_lab_link_candidates_from_block(
                lab,
                block,
                result.url,
                "aif_researcher_index",
                exact_email=False,
                exact_name=True,
            )
        )
        if len(candidate_map.get(lab_id, [])) > before:
            matched += 1
    return matched


def mine_aif_researcher_index(
    client: RespectfulClient,
    labs_by_id: dict[str, dict[str, str]],
    labs_by_email: dict[str, str],
    normalized_known_names: set[str],
    candidate_map: defaultdict[str, list[LabLinkCandidate]],
    name_evidence: dict[str, tuple[int, str, str, str]],
    paths: RuntimePaths,
    progress_every: int,
    deadline: Optional[float],
) -> dict[str, int | bool]:
    """Scan the authoritative AIF index deterministically: ~30 list pages cover all researchers."""
    unique_name_index = build_unique_name_index(labs_by_id)
    pages = attempts = failures = matches = 0
    consecutive_empty = 0
    deadline_hit = False
    max_offsets = range(0, AIF_RESEARCHER_MAX_RECORDS, AIF_RESEARCHER_PAGE_SIZE)
    print("[LAB-CENTRAL] POSTECH 산학협력단 연구자 인덱스를 우선 확인합니다.", flush=True)
    for page_no, offset in enumerate(max_offsets, start=1):
        if deadline is not None and time.monotonic() >= deadline:
            deadline_hit = True
            break
        attempts += 1
        url = aif_researcher_list_url(offset)
        if page_no == 1 or page_no % max(1, progress_every) == 0:
            print(f"[LAB-CENTRAL] 페이지={page_no} | offset={offset} | 후보교수={len(candidate_map)}", flush=True)
        try:
            result = client.fetch(url)
        except Exception as exc:
            failures += 1
            append_jsonl(paths.log, {
                "timestamp": now_iso(), "level": "aif_researcher_index_failed",
                "url": url, "error": str(exc), "enricher_version": ENRICHER_VERSION,
            })
            if failures >= 3 and pages == 0:
                break
            continue
        pages += 1
        exact_matches = mine_lab_link_page(
            result, "aif_researcher_index", labs_by_id, labs_by_email,
            normalized_known_names, candidate_map, name_evidence,
        )
        name_matches = mine_aif_unique_name_cards(
            result, labs_by_id, unique_name_index, normalized_known_names,
            candidate_map, name_evidence,
        )
        page_matches = exact_matches + name_matches
        matches += page_matches
        # List pages contain 10 researcher detail links until the final page.
        detail_links = 0
        for anchor in result.soup.find_all("a"):
            href = anchor_target_url(result.url, anchor)
            q = parse_qs(urlparse(href).query)
            if q.get("mode", [""])[0] == "view" and q.get("articleNo"):
                detail_links += 1
        consecutive_empty = consecutive_empty + 1 if detail_links == 0 else 0
        if consecutive_empty >= 2 or (0 < detail_links < AIF_RESEARCHER_PAGE_SIZE):
            break
    print(
        f"[LAB-CENTRAL-DONE] 페이지={pages} | 실패={failures} | 매칭={matches} | 후보교수={len(candidate_map)}",
        flush=True,
    )
    return {
        "pages": pages, "attempts": attempts, "failures": failures,
        "matches": matches, "deadline_hit": deadline_hit,
    }


HOMEPAGE_PROBE_TERMS = (
    "about", "people", "member", "members", "team", "contact", "pi", "principal-investigator",
    "professor", "research", "laboratory", "lab", "소개", "구성원", "연구", "연락처",
)


def homepage_identity_probe_urls(soup: BeautifulSoup, base_url: str, limit: int = 2) -> list[str]:
    scored: list[tuple[int, str]] = []
    base_key = canonical_url_key(base_url)
    for anchor in soup.find_all("a"):
        href = anchor_target_url(base_url, anchor)
        key = canonical_url_key(href)
        if not key or key == base_key or not same_site(base_url, href):
            continue
        path = urlparse(href).path.casefold()
        if any(path.endswith(ext) for ext in (".pdf", ".zip", ".jpg", ".png", ".doc", ".docx")):
            continue
        text = clean_text(" ".join([
            anchor.get_text(" ", strip=True), anchor.get("title", ""), anchor.get("aria-label", ""), path
        ])).casefold()
        score = sum(10 for term in HOMEPAGE_PROBE_TERMS if term in text)
        if any(token in text for token in ("publication", "paper", "news", "notice", "seminar", "gallery", "login")):
            score -= 30
        if score > 0:
            scored.append((score, href))
    result: list[str] = []
    seen: set[str] = set()
    for _, href in sorted(scored, key=lambda item: (-item[0], len(item[1]))):
        key = canonical_url_key(href)
        if key in seen:
            continue
        seen.add(key)
        result.append(href)
        if len(result) >= max(0, limit):
            break
    return result


def lab_link_diagnostic_recommendation(reason_counts: Counter[str], candidate_count: int) -> str:
    if candidate_count == 0:
        return "official_directory_has_no_website"
    keys = " ".join(reason_counts.keys())
    if "fetch_failed" in keys:
        return "retry_network_or_browser"
    if "ambiguous_name_without_email" in keys or "identity_conflict" in keys:
        return "manual_identity_review"
    if "dead_or_generic_page" in keys:
        return "homepage_dead_or_redirected"
    if "forbidden_final_url" in keys:
        return "candidate_is_profile_news_or_publication"
    return "candidate_identity_not_confirmed"

def classify_lab_link_verification_failure(method: str) -> str:
    method = clean_text(method)
    if method.startswith("fetch_failed"):
        return "transient_network_failure"
    if method in {"dead_or_generic_page"}:
        return "dead_homepage"
    if method in {"known_department_page", "forbidden_final_url", "broad_multi_professor_page"} or method.startswith("broad_multi_professor_page"):
        return "false_positive_page"
    if method in {"identity_conflict", "ambiguous_name_without_email"}:
        return "identity_insufficient"
    return "identity_insufficient"


def lab_link_source_follow_score(anchor: Tag, current_url: str, href: str, known_names: set[str]) -> int:
    if not href or not is_official_postech_source(href) or is_non_identity_source_url(href):
        return -999
    if is_pagination_link(anchor, current_url, href):
        return 800
    if is_profile_detail_link(anchor, href, known_names):
        return 1000
    text = clean_text(anchor.get_text(" ", strip=True)).casefold()
    haystack = f"{text} {urlparse(href).path} {urlparse(href).query}".casefold()
    if any(token in haystack for token in LAB_LINK_SOURCE_PATH_HINTS):
        return 300
    return -999


def discover_lab_link_source_pages(
    client: RespectfulClient,
    departments: Sequence[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
    max_pages: int,
    max_depth: int,
    paths: RuntimePaths,
    save_raw: bool,
    target_lab_ids: Optional[set[str]] = None,
    host_page_cap: int = DEFAULT_LAB_LINK_HOST_PAGE_CAP,
    progress_every: int = DEFAULT_LAB_LINK_PROGRESS_EVERY,
    deadline: Optional[float] = None,
) -> tuple[list[tuple[PageResult, str]], dict[str, object]]:
    target_lab_ids = set(labs_by_id.keys()) if target_lab_ids is None else set(target_lab_ids)
    known_names = {
        normalize_name(labs_by_id[lab_id].get("professor_name", ""))
        for lab_id in target_lab_ids
        if lab_id in labs_by_id and normalize_name(labs_by_id[lab_id].get("professor_name", ""))
    }
    queue: list[tuple[int, int, str, str]] = []
    queued: set[str] = set()
    visited: set[str] = set()
    for priority, url, kind in collect_lab_link_seed_urls(departments, labs_by_id, target_lab_ids):
        key = canonical_url_key(url)
        if key and key not in queued:
            queued.add(key)
            heapq.heappush(queue, (-priority, 0, url, kind))

    results: list[tuple[PageResult, str]] = []
    attempts = 0
    failed = 0
    skipped_host_cap = 0
    deadline_hit = False
    host_pages: Counter[str] = Counter()
    max_attempts = max(max_pages * 2, max_pages + 30)
    progress_every = max(1, int(progress_every))
    while queue and len(results) < max_pages and attempts < max_attempts:
        if deadline is not None and time.monotonic() >= deadline:
            deadline_hit = True
            print("[LAB-SOURCE] 시간 예산 도달 — 현재까지 찾은 후보로 검증을 계속합니다.", flush=True)
            break
        neg_priority, depth, url, kind = heapq.heappop(queue)
        attempts += 1
        key = canonical_url_key(url)
        queued.discard(key)
        if not key or key in visited:
            continue
        visited.add(key)
        host = hostname(url)
        if host_page_cap > 0 and host_pages[host] >= host_page_cap:
            skipped_host_cap += 1
            continue
        if attempts == 1 or attempts % progress_every == 0:
            print(
                f"[LAB-SOURCE] 시도={attempts}/{max_attempts} | 성공={len(results)}/{max_pages} | "
                f"큐={len(queue)} | depth={depth} | host={host}",
                flush=True,
            )
        try:
            result = client.fetch(url)
        except Exception as exc:
            failed += 1
            append_jsonl(
                paths.log,
                {
                    "timestamp": now_iso(),
                    "level": "lab_link_source_fetch_failed",
                    "url": url,
                    "error": str(exc),
                    "enricher_version": ENRICHER_VERSION,
                },
            )
            continue
        if not is_official_postech_source(result.url):
            continue
        results.append((result, kind))
        host_pages[hostname(result.url)] += 1
        save_raw_html(paths, "LAB_LINKS", len(results), result, save_raw)
        if depth >= max_depth:
            continue
        soup = result.soup
        for anchor in soup.find_all("a"):
            href = anchor_target_url(result.url, anchor)
            score = lab_link_source_follow_score(anchor, result.url, href, known_names)
            next_key = canonical_url_key(href)
            if score <= 0 or not next_key or next_key in visited or next_key in queued:
                continue
            next_host = hostname(href)
            if host_page_cap > 0 and host_pages[next_host] >= host_page_cap:
                continue
            queued.add(next_key)
            next_kind = "professor_profile" if is_profile_detail_link(anchor, href, known_names) else kind
            heapq.heappush(queue, (-(max(1, -neg_priority) + score), depth + 1, href, next_kind))
    print(
        f"[LAB-SOURCE-DONE] 성공={len(results)} | 실패={failed} | 시도={attempts} | "
        f"호스트상한건너뜀={skipped_host_cap}",
        flush=True,
    )
    return results, {
        "attempts": attempts,
        "failed": failed,
        "skipped_host_cap": skipped_host_cap,
        "deadline_hit": deadline_hit,
        "host_pages": dict(host_pages),
    }


def mine_lab_link_page(
    result: PageResult,
    source_kind: str,
    labs_by_id: dict[str, dict[str, str]],
    labs_by_email: dict[str, str],
    normalized_known_names: set[str],
    candidate_map: defaultdict[str, list[LabLinkCandidate]],
    name_evidence: dict[str, tuple[int, str, str, str]],
) -> int:
    soup = result.soup
    page_text = deobfuscate_email_text(soup.get_text(" ", strip=True))
    page_emails = extract_identity_emails(page_text)
    direct_nodes = find_email_nodes(soup)
    matched = 0
    for email in sorted(page_emails):
        lab_id = labs_by_email.get(email)
        if not lab_id or lab_id not in labs_by_id:
            continue
        lab = labs_by_id[lab_id]
        node = direct_nodes.get(email) or find_text_node_for_email(soup, email)
        if node is None:
            continue
        block = find_person_container(
            node,
            lab.get("professor_name", ""),
            email,
            normalized_known_names,
        )
        block_text = deobfuscate_email_text(block.get_text(" ", strip=True))
        professor_emails = {
            item for item in extract_identity_emails(block_text)
            if item in labs_by_email
        }
        if len(professor_emails) > 4:
            continue
        exact_name = bool(
            normalize_name(lab.get("professor_name", ""))
            and normalize_name(lab.get("professor_name", "")) in normalize_name(block_text)
        )
        lab_name = extract_labeled_lab_name_from_block(block, lab.get("professor_name", ""))
        if lab_name:
            current = name_evidence.get(lab_id)
            evidence_score = 100 if exact_name else 90
            if current is None or evidence_score > current[0]:
                name_evidence[lab_id] = (evidence_score, lab_name, result.url, "official_exact_email_card")
        candidate_map[lab_id].extend(
            extract_lab_link_candidates_from_block(
                lab,
                block,
                result.url,
                source_kind,
                exact_email=True,
                exact_name=exact_name,
            )
        )
        matched += 1
    return matched


def page_looks_dead_or_generic(soup: BeautifulSoup) -> bool:
    text = clean_text(soup.get_text(" ", strip=True))
    title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    if any(pattern.search(f"{title} {text[:1000]}") for pattern in DEAD_HOMEPAGE_PATTERNS):
        return True
    if len(text) < 60 and len(soup.find_all("script")) < 3:
        return True
    if title.casefold().strip(" -|·") in GENERIC_HOMEPAGE_TITLES and not re.search(
        r"(?i)(?:laboratory|\blab\b|research group|연구실|연구그룹)", text[:3000]
    ):
        return True
    return False


def homepage_research_context(soup: BeautifulSoup) -> bool:
    text = clean_text(soup.get_text(" ", strip=True)).casefold()
    title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "").casefold()
    return any(
        token in f" {title} {text[:5000]} "
        for token in (
            " laboratory", " lab ", "research group", "research center", "research", "연구실", "연구그룹", "연구센터",
        )
    )


def verify_lab_link_candidate(
    client: RespectfulClient,
    lab: dict[str, str],
    candidate: LabLinkCandidate,
    ambiguous_name: bool,
    max_probe_pages: int = DEFAULT_LAB_LINK_HOMEPAGE_PROBE_PAGES,
    department_url_keys: Optional[set[str]] = None,
    known_professor_emails: Optional[set[str]] = None,
    known_professor_names: Optional[set[str]] = None,
) -> tuple[dict[str, str], str]:
    department_url_keys = department_url_keys or set()
    known_professor_emails = known_professor_emails or set()
    known_professor_names = known_professor_names or set()
    if canonical_url_key(candidate.url) in department_url_keys:
        return {}, "known_department_page"
    result: Optional[PageResult] = None
    fetch_errors: list[str] = []
    for variant in candidate_url_variants(candidate.url):
        try:
            result = client.fetch(variant)
            break
        except Exception as exc:
            fetch_errors.append(str(exc))
    if result is None:
        strength = lab_link_label_strength(candidate.label_text)
        source_authoritative = candidate.exact_email and is_official_postech_source(candidate.source_url)
        card_verified = bool(
            source_authoritative
            and canonical_url_key(candidate.url) not in department_url_keys
            and (strength >= 2 or (strength >= 1 and candidate.lab_name and candidate.score >= 85))
        )
        if card_verified:
            lab_name_kor, lab_name_eng = split_discovered_lab_name(candidate.lab_name)
            return {
                "lab_url": normalize_url(candidate.url), "lab_url_status": "verified_card",
                "lab_name_kor": lab_name_kor, "lab_name_eng": lab_name_eng,
                "enrichment_source_urls": candidate.source_url,
                "_lab_link_evidence_method": "official_exact_email_card_unreachable",
                "_source_scope": "department_page",
            }, "official_exact_email_card_unreachable"
        return {}, "fetch_failed: " + " | ".join(fetch_errors[:2])
    final_url = normalize_url(result.url)
    if (not final_url or is_forbidden_lab_url(final_url, lab.get("professor_profile_url", ""))
            or canonical_url_key(final_url) in department_url_keys):
        return {}, "known_department_page" if canonical_url_key(final_url) in department_url_keys else "forbidden_final_url"
    soup = result.soup
    probe_urls = homepage_identity_probe_urls(soup, final_url, max_probe_pages)
    main_page_usable = not page_looks_dead_or_generic(soup)
    if not main_page_usable and not probe_urls:
        return {}, "dead_or_generic_page"
    identity_pages: list[tuple[BeautifulSoup, str]] = [(soup, final_url)] if main_page_usable else []
    for probe_url in probe_urls:
        try:
            probe = client.fetch(probe_url)
        except Exception:
            continue
        if same_site(final_url, probe.url) and not page_looks_dead_or_generic(probe.soup):
            identity_pages.append((probe.soup, normalize_url(probe.url)))
    if not identity_pages:
        return {}, "dead_or_generic_page"
    target_email = normalize_email(lab.get("email", ""))
    target_name = normalize_name(lab.get("professor_name", ""))
    aggregate_text = " ".join(deobfuscate_email_text(x.get_text(" ", strip=True)) for x, _ in identity_pages)
    page_emails = extract_identity_emails(aggregate_text)
    exact_email = bool(target_email and target_email in page_emails)
    exact_name = bool(target_name and target_name in normalize_name(aggregate_text))
    research_context = any(homepage_research_context(x) for x, _ in identity_pages)
    homepage_name = ""
    for item_soup, _ in identity_pages:
        homepage_name = extract_homepage_lab_name(item_soup)
        if homepage_name:
            break
    label_strength = lab_link_label_strength(candidate.label_text)
    url_lab_signal = any(token in f"{hostname(final_url)} {urlparse(final_url).path}".casefold() for token in LAB_PATH_HINTS)
    lab_specific = bool(homepage_name or candidate.lab_name or label_strength >= 2 or url_lab_signal)
    known_email_count, known_name_count = known_professor_identity_counts(
        aggregate_text, known_professor_emails, known_professor_names
    )
    if (known_email_count >= BROAD_PAGE_MAX_KNOWN_EMAILS or known_name_count >= BROAD_PAGE_MAX_KNOWN_NAMES) and not (homepage_name and known_email_count <= 3):
        return {}, f"broad_multi_professor_page:{known_email_count}:{known_name_count}"
    unrelated_postech = {x for x in page_emails if x.endswith("@postech.ac.kr") and x != target_email}
    if unrelated_postech and not exact_email and not exact_name:
        return {}, "identity_conflict"
    if ambiguous_name and not exact_email and not candidate.exact_email:
        return {}, "ambiguous_name_without_email"
    official_name_card = bool(
        candidate.exact_name and is_official_postech_source(candidate.source_url)
        and candidate.source_kind in {"aif_researcher_index", "official_directory", "professor_profile"}
    )
    status = "candidate_card"
    evidence_method = candidate.evidence_method
    if exact_email and research_context and lab_specific:
        status = "verified_homepage"
        evidence_method = "homepage_exact_email"
    elif exact_name and research_context and lab_specific and (candidate.exact_email or official_name_card):
        status = "verified_homepage"
        evidence_method = "official_card_email_plus_homepage_name" if candidate.exact_email else "official_unique_name_card_plus_homepage_name"
    elif candidate.exact_email and (label_strength >= 1 or candidate.lab_name) and research_context:
        status = "verified_card"
        evidence_method = "official_exact_email_card_reachable"
    elif candidate.exact_email and label_strength >= 2:
        status = "verified_card"
        evidence_method = "official_exact_email_strong_label"
    chosen_name = clean_discovered_lab_name(candidate.lab_name, lab.get("professor_name", "")) or clean_discovered_lab_name(homepage_name, lab.get("professor_name", ""))
    lab_name_kor, lab_name_eng = split_discovered_lab_name(chosen_name)
    return {
        "lab_url": final_url, "lab_url_status": status,
        "lab_name_kor": lab_name_kor, "lab_name_eng": lab_name_eng,
        "enrichment_source_urls": merge_multi(candidate.source_url, *(url for _, url in identity_pages)),
        "_lab_link_evidence_method": evidence_method,
        "_source_scope": "lab_homepage" if status == "verified_homepage" else "department_page",
    }, evidence_method

def lab_link_safety_issues(
    before: Sequence[dict[str, str]], after: Sequence[dict[str, str]],
    department_url_keys: Optional[set[str]] = None, allowed_trusted_decrease: int = 0,
) -> list[str]:
    department_url_keys = department_url_keys or set()
    issues: list[str] = []
    before_trusted = sum(bool(normalize_url(r.get("lab_url", ""))) and r.get("lab_url_status") in TRUSTED_LAB_URL_STATUSES for r in before)
    after_trusted = sum(bool(normalize_url(r.get("lab_url", ""))) and r.get("lab_url_status") in TRUSTED_LAB_URL_STATUSES for r in after)
    if after_trusted + max(0, allowed_trusted_decrease) < before_trusted:
        issues.append(f"신뢰 URL 수 비정상 감소 {before_trusted}→{after_trusted}")
    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in after:
        url = normalize_url(row.get("lab_url", ""))
        status = clean_text(row.get("lab_url_status", ""))
        if not url or status not in TRUSTED_LAB_URL_STATUSES:
            continue
        key = canonical_url_key(url)
        if is_forbidden_lab_url(url, row.get("professor_profile_url", "")):
            issues.append(f"금지 URL이 신뢰 상태: {row.get('lab_id')} {url}")
        if key in department_url_keys and status != "manual":
            issues.append(f"학과/교수목록 URL이 신뢰 상태: {row.get('lab_id')} {url}")
        groups[key].append(row)
    for key, rows in groups.items():
        emails = {normalize_email(r.get("email", "")) for r in rows if normalize_email(r.get("email", ""))}
        departments = {clean_text(r.get("primary_department_id", "") or r.get("department_id", "")) for r in rows}
        if len(rows) < 2:
            continue
        if len(emails) >= 4 or len(departments) >= 2:
            issues.append(f"신뢰 URL 다중 교수 충돌 {len(emails)}명: {key}")
        elif not shared_lab_group_is_verified(rows):
            issues.append(f"신뢰 URL 공유 연구실 근거 부족 {len(emails)}명: {key}")
    return unique_preserve_order(issues)

def discover_lab_links_in_memory(
    client: RespectfulClient,
    departments: Sequence[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
    paths: RuntimePaths,
    args: argparse.Namespace,
) -> dict:
    snapshot = deepcopy(labs_by_id)
    sanitation = sanitize_existing_lab_link_records(departments, labs_by_id)
    department_url_keys = sanitation["department_url_keys"]
    trusted_before_raw = sum(
        bool(normalize_url(row.get("lab_url", "")))
        and row.get("lab_url_status") in TRUSTED_LAB_URL_STATUSES
        for row in snapshot.values()
    )
    trusted_before = sum(
        bool(normalize_url(row.get("lab_url", "")))
        and row.get("lab_url_status") in TRUSTED_LAB_URL_STATUSES
        for row in labs_by_id.values()
    )
    any_url_before = sum(bool(normalize_url(row.get("lab_url", ""))) for row in labs_by_id.values())
    actual_name_before = sum(lab_name_is_actual(row) for row in labs_by_id.values())
    labs_by_email, _, normalized_known_names, _ = build_indexes(labs_by_id)
    name_counts = Counter(
        normalize_name(row.get("professor_name", ""))
        for row in labs_by_id.values()
        if normalize_name(row.get("professor_name", ""))
    )
    known_professor_emails = {normalize_email(row.get("email", "")) for row in labs_by_id.values() if normalize_email(row.get("email", ""))}
    known_professor_names = {normalize_name(row.get("professor_name", "")) for row in labs_by_id.values() if normalize_name(row.get("professor_name", ""))}
    candidate_map: defaultdict[str, list[LabLinkCandidate]] = defaultdict(list)
    name_evidence: dict[str, tuple[int, str, str, str]] = {}
    refresh_all = bool(getattr(args, "refresh_lab_links", False))
    target_lab_ids = {
        lab_id
        for lab_id, lab in labs_by_id.items()
        if lab_link_target_required(lab, refresh_all)
    }
    time_budget_minutes = max(0.0, float(getattr(args, "lab_link_time_budget_minutes", DEFAULT_LAB_LINK_TIME_BUDGET_MINUTES)))
    started_at = time.monotonic()
    deadline = (started_at + time_budget_minutes * 60.0) if time_budget_minutes > 0 else None
    source_deadline = (started_at + time_budget_minutes * 60.0 * 0.45) if deadline is not None else None
    identity_deadline = (started_at + time_budget_minutes * 60.0 * 0.70) if deadline is not None else None
    progress_every = max(1, int(getattr(args, "lab_link_progress_every", DEFAULT_LAB_LINK_PROGRESS_EVERY)))
    print(f"[LAB-TARGET] 링크 또는 이름 보완 대상={len(target_lab_ids)}/{len(labs_by_id)}", flush=True)
    if not target_lab_ids:
        return {
            "committed_in_memory": True,
            "issues": [],
            "source_pages": 0,
            "individual_source_pages": 0,
            "source_attempts": 0,
            "source_failures": 0,
            "source_host_cap_skips": 0,
            "time_budget_exhausted": False,
            "page_matches": 0,
            "candidate_labs": 0,
            "updated_labs": 0,
            "updated_lab_ids": [],
            "verified_homepage": 0,
            "verified_card": 0,
            "candidate_only": 0,
            "lab_names_added": 0,
            "fetch_failures": 0,
            "trusted_before": trusted_before,
            "trusted_after": trusted_before,
            "any_url_before": any_url_before,
            "any_url_after": any_url_before,
            "actual_name_before": actual_name_before,
            "actual_name_after": actual_name_before,
            "post_clean_changed_fields": {},
        }

    central_deadline = (started_at + time_budget_minutes * 60.0 * 0.22) if deadline is not None else None
    central_stats = mine_aif_researcher_index(
        client, labs_by_id, labs_by_email, normalized_known_names,
        candidate_map, name_evidence, paths, progress_every, central_deadline,
    )

    source_pages, source_stats = discover_lab_link_source_pages(
        client,
        departments,
        labs_by_id,
        max_pages=int(getattr(args, "lab_link_max_pages", DEFAULT_LAB_LINK_MAX_PAGES)),
        max_depth=int(getattr(args, "lab_link_max_depth", DEFAULT_LAB_LINK_MAX_DEPTH)),
        paths=paths,
        save_raw=bool(getattr(args, "save_raw_html", False)),
        target_lab_ids=target_lab_ids,
        host_page_cap=int(getattr(args, "lab_link_host_page_cap", DEFAULT_LAB_LINK_HOST_PAGE_CAP)),
        progress_every=progress_every,
        deadline=source_deadline,
    )
    page_match_count = 0
    for page_index, (result, source_kind) in enumerate(source_pages, start=1):
        page_match_count += mine_lab_link_page(
            result,
            source_kind,
            labs_by_id,
            labs_by_email,
            normalized_known_names,
            candidate_map,
            name_evidence,
        )
        if page_index == 1 or page_index % progress_every == 0:
            print(
                f"[LAB-MINE] {page_index}/{len(source_pages)} | 후보교수={len(candidate_map)} | "
                f"연구실명근거={len(name_evidence)}",
                flush=True,
            )

    # Guarantee a professor-level fallback even when the global directory crawl
    # reaches its page cap. Each unresolved professor's official POSTECH profile
    # and matched department page are fetched directly; RespectfulClient caching
    # prevents duplicate network requests for pages already visited above.
    individual_source_pages = 0
    identity_source_limit = max(1, int(getattr(args, "lab_link_identity_sources_per_lab", DEFAULT_LAB_LINK_IDENTITY_SOURCES_PER_LAB)))
    target_items = [(lab_id, labs_by_id[lab_id]) for lab_id in sorted(target_lab_ids) if lab_id in labs_by_id]
    for target_index, (lab_id, lab) in enumerate(target_items, start=1):
        if identity_deadline is not None and time.monotonic() >= identity_deadline:
            print("[LAB-IDENTITY] 단계 시간 예산 도달 — URL 후보 검증 단계로 이동합니다.", flush=True)
            break
        if target_index == 1 or target_index % progress_every == 0:
            print(
                f"[LAB-IDENTITY] {target_index}/{len(target_items)} | 교수={lab.get('professor_name', '-')} | "
                f"후보={len(candidate_map.get(lab_id, []))}",
                flush=True,
            )
        current_trusted = bool(normalize_url(lab.get("lab_url", ""))) and clean_text(
            lab.get("lab_url_status", "")
        ) in TRUSTED_LAB_URL_STATUSES
        needs_name = looks_placeholder_lab_name(lab.get("lab_name_kor", ""))
        needs_provenance = current_trusted and not lab_url_provenance_complete(lab)
        if not refresh_all and current_trusted and not needs_name and not needs_provenance:
            continue
        strong_existing_candidate = any(
            candidate.exact_email and candidate.score >= 105
            for candidate in candidate_map.get(lab_id, [])
        )
        if strong_existing_candidate:
            continue
        for source_url, source_kind in individual_lab_identity_sources(lab, identity_source_limit):
            try:
                result = client.fetch(source_url)
            except Exception as exc:
                append_jsonl(
                    paths.log,
                    {
                        "timestamp": now_iso(),
                        "level": "lab_link_identity_source_failed",
                        "lab_id": lab_id,
                        "email": normalize_email(lab.get("email", "")),
                        "url": source_url,
                        "error": str(exc),
                        "enricher_version": ENRICHER_VERSION,
                    },
                )
                continue
            if not is_official_postech_source(result.url):
                continue
            individual_source_pages += 1
            page_match_count += mine_lab_link_page(
                result,
                source_kind,
                {lab_id: lab},
                {normalize_email(lab.get("email", "")): lab_id},
                normalized_known_names,
                candidate_map,
                name_evidence,
            )
            if (
                any(candidate.exact_email and candidate.score >= 105 for candidate in candidate_map.get(lab_id, []))
                and lab_id in name_evidence
            ):
                break

    # Existing non-trusted URLs and trusted legacy URLs without field-level
    # provenance deserve one verification pass.
    for lab_id, lab in labs_by_id.items():
        existing_url = normalize_url(lab.get("lab_url", ""))
        current_status = clean_text(lab.get("lab_url_status", ""))
        needs_revalidation = lab_link_revalidation_required(lab, refresh_all)
        if needs_revalidation:
            candidate_map[lab_id].append(
                LabLinkCandidate(
                    lab_id=lab_id, url=existing_url,
                    source_url=normalize_url(
                        lab_url_provenance(lab).get("source_url", "")
                        or lab.get("department_page_url", "")
                        or lab.get("source_url", "")
                        or lab.get("professor_profile_url", "")
                        or existing_url
                    ),
                    source_kind="existing_candidate" if current_status not in TRUSTED_LAB_URL_STATUSES else "existing_trusted_revalidation",
                    evidence_method="existing_candidate_revalidation" if current_status not in TRUSTED_LAB_URL_STATUSES else "legacy_trusted_revalidation",
                    score=82 if current_status in TRUSTED_LAB_URL_STATUSES else 75,
                    exact_email=False, exact_name=False,
                    lab_name=clean_lab_name(lab.get("lab_name_kor", ""), lab.get("professor_name", "")) or clean_lab_name(lab.get("lab_name_eng", ""), lab.get("professor_name", "")),
                )
            )

    updated_lab_ids: set[str] = set()
    verified_homepage = 0
    verified_card = 0
    candidate_only = 0
    names_added = 0
    fetch_failures = 0
    provenance_only_updates = 0
    revalidation_targets = sum(
        bool(normalize_url(labs_by_id[lab_id].get("lab_url", "")))
        and clean_text(labs_by_id[lab_id].get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES
        and (refresh_all or not lab_url_provenance_complete(labs_by_id[lab_id]))
        for lab_id in target_lab_ids if lab_id in labs_by_id
    )
    revalidation_attempts = 0
    revalidation_success = 0
    revalidation_failures: Counter[str] = Counter()
    verification_reasons: defaultdict[str, Counter[str]] = defaultdict(Counter)
    max_candidates = max(1, int(getattr(args, "lab_link_candidates_per_lab", DEFAULT_LAB_LINK_CANDIDATES_PER_LAB)))

    verify_items = [(lab_id, labs_by_id[lab_id]) for lab_id in sorted(target_lab_ids) if lab_id in labs_by_id]
    for verify_index, (lab_id, lab) in enumerate(verify_items, start=1):
        if deadline is not None and time.monotonic() >= deadline:
            print("[LAB-VERIFY] 시간 예산 도달 — 확보된 결과만 안전성 검사합니다.", flush=True)
            break
        if verify_index == 1 or verify_index % progress_every == 0:
            print(
                f"[LAB-VERIFY] {verify_index}/{len(verify_items)} | 교수={lab.get('professor_name', '-')} | "
                f"URL후보={len(candidate_map.get(lab_id, []))}",
                flush=True,
            )
        current_status = clean_text(lab.get("lab_url_status", ""))
        current_url = normalize_url(lab.get("lab_url", ""))
        current_trusted = bool(current_url) and current_status in TRUSTED_LAB_URL_STATUSES
        needs_url = not current_url or current_status not in TRUSTED_LAB_URL_STATUSES
        needs_name = looks_placeholder_lab_name(lab.get("lab_name_kor", ""))
        needs_provenance = current_trusted and not lab_url_provenance_complete(lab)
        revalidating_trusted = current_trusted and (refresh_all or needs_provenance)
        if not refresh_all and not needs_url and not needs_name and not needs_provenance:
            continue

        before_name = clean_text(lab.get("lab_name_kor", ""))
        if lab_id in name_evidence and needs_name:
            _, lab_name, source_url, method = name_evidence[lab_id]
            kor_name, eng_name = split_discovered_lab_name(lab_name)
            name_update = {
                "lab_name_kor": kor_name,
                "lab_name_eng": eng_name,
                "enrichment_source_urls": source_url,
                "_source_scope": "department_page",
            }
            merged, changed = merge_lab_update(lab, name_update, "")
            if changed:
                record_field_provenance(merged, changed, "department_page", source_url, method)
                labs_by_id[lab_id] = merged
                lab = merged
                updated_lab_ids.add(lab_id)
                if before_name != clean_text(merged.get("lab_name_kor", "")):
                    names_added += 1

        candidates = candidate_map.get(lab_id, [])
        dedup: dict[str, LabLinkCandidate] = {}
        for candidate in candidates:
            key = canonical_url_key(candidate.url)
            current = dedup.get(key)
            if key and (current is None or candidate_preference_key(candidate) > candidate_preference_key(current)):
                dedup[key] = candidate
        ordered = sorted(
            dedup.values(),
            key=candidate_preference_key,
            reverse=True,
        )[:max_candidates]

        best_candidate_update: Optional[tuple[dict[str, str], LabLinkCandidate, str]] = None
        trusted_failure_methods: list[str] = []
        for candidate in ordered:
            candidate_is_current = revalidating_trusted and canonical_url_key(candidate.url) == canonical_url_key(current_url)
            if candidate_is_current:
                revalidation_attempts += 1
            update, method = verify_lab_link_candidate(
                client,
                lab,
                candidate,
                ambiguous_name=name_counts.get(normalize_name(lab.get("professor_name", "")), 0) >= 2,
                max_probe_pages=int(getattr(args, "lab_link_homepage_probe_pages", DEFAULT_LAB_LINK_HOMEPAGE_PROBE_PAGES)),
                department_url_keys=department_url_keys,
                known_professor_emails=known_professor_emails,
                known_professor_names=known_professor_names,
            )
            verification_reasons[lab_id][method] += 1
            if not update:
                if method.startswith("fetch_failed"):
                    fetch_failures += 1
                if candidate_is_current:
                    trusted_failure_methods.append(method)
                continue
            status = update.get("lab_url_status", "candidate_card")
            if candidate_is_current and status not in TRUSTED_LAB_URL_STATUSES:
                # Insufficient current evidence is not destructive. Preserve the
                # previously trusted value and report the reason separately.
                trusted_failure_methods.append(method)
                continue
            if best_candidate_update is None or verified_candidate_preference_key(update, candidate, method) > verified_candidate_preference_key(
                best_candidate_update[0], best_candidate_update[1], best_candidate_update[2]
            ):
                best_candidate_update = (update, candidate, method)

        if best_candidate_update is None:
            if revalidating_trusted:
                reason = trusted_failure_methods[0] if trusted_failure_methods else "identity_not_confirmed"
                revalidation_failures[classify_lab_link_verification_failure(reason)] += 1
            continue
        update, candidate, method = best_candidate_update
        merged, changed = merge_lab_update(lab, update, "")
        trusted_update = clean_text(update.get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES
        missing_link_provenance = trusted_update and not lab_url_provenance_complete(lab)
        refresh_provenance = bool(refresh_all and revalidating_trusted and trusted_update)
        if not changed and not missing_link_provenance and not refresh_provenance:
            continue
        if not changed:
            merged = dict(lab)
        provenance_fields = unique_preserve_order(
            [*changed, *(["lab_url", "lab_url_status"] if trusted_update else [])]
        )
        source_scope = "lab_homepage" if update.get("lab_url_status") == "verified_homepage" else "department_page"
        record_lab_link_provenance(merged, provenance_fields, candidate, update, method)
        if (missing_link_provenance or refresh_provenance) and "field_provenance" not in changed:
            changed = [*changed, "field_provenance"]
            provenance_only_updates += 1
        merged["enrichment_status"] = "success"
        merged["enrichment_message"] = merge_multi(
            merged.get("enrichment_message", ""),
            "랩 링크 우선 보완: " + ", ".join(changed),
        )
        merged["enriched_at"] = now_iso()
        merged["enricher_version"] = ENRICHER_VERSION
        merged["data_quality_status"] = data_quality_status(merged)
        labs_by_id[lab_id] = merged
        updated_lab_ids.add(lab_id)
        if revalidating_trusted and trusted_update:
            revalidation_success += 1
        status = clean_text(merged.get("lab_url_status", ""))
        if status == "verified_homepage":
            verified_homepage += 1
        elif status == "verified_card":
            verified_card += 1
        elif status == "candidate_card":
            candidate_only += 1

    # Do not run the general cross-record cleaner in link-only work. It may alter
    # affiliations or unrelated fields. merge_lab_update already sanitizes every
    # changed link/name field.
    candidate_rows = {lab_id: dict(row) for lab_id, row in labs_by_id.items()}
    shared_lab_rows_marked = mark_all_verified_shared_lab_groups(candidate_rows)
    immutable_fields = (
        "professor_name", "email", "department_id", "primary_department_id",
        "department_name", "affiliated_programs", "affiliation_evidence",
        "department_page_url", "phone", "location", "primary_field",
        "research_summary", "keywords", "profile_image_url",
    )
    issues = lab_link_safety_issues(
        list(snapshot.values()), list(candidate_rows.values()),
        department_url_keys=department_url_keys,
        allowed_trusted_decrease=int(sanitation.get("invalidated_count", 0)),
    )
    for lab_id, before_row in snapshot.items():
        after_row = candidate_rows.get(lab_id, {})
        for field_name in immutable_fields:
            if clean_text(before_row.get(field_name, "")) != clean_text(after_row.get(field_name, "")):
                issues.append(f"랩링크 모드 비대상 필드 변경: {lab_id} {field_name}")
    if issues:
        labs_by_id.clear()
        labs_by_id.update(snapshot)
        return {
            "committed_in_memory": False,
            "issues": issues,
            "source_pages": len(source_pages),
            "individual_source_pages": individual_source_pages,
            "page_matches": page_match_count,
            "updated_labs": 0,
            "trusted_before": trusted_before,
            "trusted_after": trusted_before,
            "any_url_before": any_url_before,
            "any_url_after": any_url_before,
            "actual_name_before": actual_name_before,
            "actual_name_after": actual_name_before,
        }
    labs_by_id.clear()
    labs_by_id.update(candidate_rows)
    trusted_after = sum(
        bool(normalize_url(row.get("lab_url", "")))
        and row.get("lab_url_status") in TRUSTED_LAB_URL_STATUSES
        for row in labs_by_id.values()
    )
    any_url_after = sum(bool(normalize_url(row.get("lab_url", ""))) for row in labs_by_id.values())
    actual_name_after = sum(lab_name_is_actual(row) for row in labs_by_id.values())
    diagnostic_rows: list[dict[str, str]] = []
    for lab_id in sorted(target_lab_ids):
        lab = labs_by_id.get(lab_id, {})
        status = clean_text(lab.get("lab_url_status", ""))
        trusted = bool(normalize_url(lab.get("lab_url", ""))) and status in TRUSTED_LAB_URL_STATUSES
        review = status == "candidate_card"
        if trusted and not review:
            continue
        candidates = sorted(
            {canonical_url_key(c.url): c for c in candidate_map.get(lab_id, []) if canonical_url_key(c.url)}.values(),
            key=lambda c: c.score, reverse=True,
        )
        reasons = verification_reasons.get(lab_id, Counter())
        diagnostic_rows.append({
            "lab_id": lab_id,
            "professor_name": clean_text(lab.get("professor_name", "")),
            "email": normalize_email(lab.get("email", "")),
            "department_name": clean_text(lab.get("department_name", "")),
            "result_class": "review_candidate" if review else "unresolved",
            "current_lab_url": normalize_url(lab.get("lab_url", "")),
            "lab_url_status": status,
            "candidate_count": str(len(candidates)),
            "candidate_urls": ";".join(c.url for c in candidates[:5]),
            "verification_reasons": ";".join(f"{key}:{value}" for key, value in reasons.most_common()),
            "recommendation": lab_link_diagnostic_recommendation(reasons, len(candidates)),
        })

    return {
        "committed_in_memory": True,
        "issues": [],
        "source_pages": len(source_pages),
        "central_directory_pages": int(central_stats.get("pages", 0)),
        "central_directory_matches": int(central_stats.get("matches", 0)),
        "diagnostic_rows": diagnostic_rows,
        "individual_source_pages": individual_source_pages,
        "source_attempts": source_stats.get("attempts", 0),
        "source_failures": source_stats.get("failed", 0),
        "source_host_cap_skips": source_stats.get("skipped_host_cap", 0),
        "time_budget_exhausted": bool(deadline is not None and time.monotonic() >= deadline),
        "page_matches": page_match_count,
        "candidate_labs": len(candidate_map),
        "updated_labs": len(updated_lab_ids),
        "updated_lab_ids": sorted(updated_lab_ids),
        "verified_homepage": verified_homepage,
        "verified_card": verified_card,
        "candidate_only": candidate_only,
        "lab_names_added": actual_name_after - actual_name_before,
        "lab_name_stage_updates": names_added,
        "fetch_failures": fetch_failures,
        "provenance_only_updates": provenance_only_updates,
        "revalidation_targets": revalidation_targets,
        "revalidation_attempts": revalidation_attempts,
        "revalidation_success": revalidation_success,
        "revalidation_failures": dict(revalidation_failures),
        "shared_lab_rows_marked": shared_lab_rows_marked,
        "trusted_before": trusted_before_raw,
        "trusted_after": trusted_after,
        "invalid_department_urls_removed": int(sanitation.get("invalidated_count", 0)),
        "lab_names_sanitized": int(sanitation.get("names_cleaned", 0)),
        "lab_names_promoted_from_eng": int(sanitation.get("names_promoted", 0)),
        "legacy_trusted_without_provenance": int(sanitation.get("trusted_without_provenance", 0)),
        "legacy_trusted_incomplete_provenance": int(sanitation.get("trusted_incomplete_provenance", 0)),
        "manual_provenance_backfilled": int(sanitation.get("manual_provenance_backfilled", 0)),
        "shared_lab_rows_marked_during_sanitation": int(sanitation.get("shared_lab_rows_marked", 0)),
        "any_url_before": any_url_before,
        "any_url_after": any_url_after,
        "actual_name_before": actual_name_before,
        "actual_name_after": actual_name_after,
        "post_clean_changed_fields": {},
    }


def prune_old_backups(backup_dir: Path, keep: int) -> None:
    if keep < 1 or not backup_dir.exists():
        return
    for prefix in ("labs_before_stage2_", "departments_before_stage2_", "research_outputs_clean_before_"):
        files = sorted(
            (path for path in backup_dir.glob(prefix + "*") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale in files[keep:]:
            stale.unlink(missing_ok=True)


def run_lab_links_only(args: argparse.Namespace) -> None:
    paths = RuntimePaths.from_args(Path(args.data_dir), Path(args.overrides) if args.overrides else None)
    departments, _ = read_csv_rows(paths.departments)
    labs, lab_existing_fields = read_csv_rows(paths.labs)
    lab_fields = ensure_fields(lab_existing_fields, BASE_LAB_FIELDS + STAGE2_LAB_FIELDS)
    labs_by_id = {clean_text(row.get("lab_id", "")): dict(row) for row in labs if clean_text(row.get("lab_id", ""))}
    before_rows = deepcopy(list(labs_by_id.values()))
    lab_order = [clean_text(row.get("lab_id", "")) for row in labs if clean_text(row.get("lab_id", ""))]

    client = RespectfulClient(
        delay_seconds=args.delay,
        timeout_seconds=min(args.timeout, 12),
        connect_timeout_seconds=args.connect_timeout,
        browser_fallback=args.browser_fallback,
        allow_insecure=args.allow_insecure,
        respect_robots=not args.ignore_robots,
        retry_total=args.http_retries,
        max_host_failures=args.lab_link_max_host_failures,
    )
    print("=" * 100)
    print(f"POSTECH LAB LINK FIRST — {ENRICHER_VERSION}")
    print("=" * 100)
    print(f"연구실 레코드       : {len(labs_by_id)}")
    print(f"소스 페이지 상한    : {args.lab_link_max_pages}")
    print(f"후속 탐색 깊이      : {args.lab_link_max_depth}")
    print(f"랩당 후보 검증 상한 : {args.lab_link_candidates_per_lab}")
    print(f"교수별 신원소스 상한: {args.lab_link_identity_sources_per_lab}")
    print(f"호스트별 페이지 상한: {args.lab_link_host_page_cap}")
    print(f"호스트 연속실패 상한: {args.lab_link_max_host_failures}")
    print(f"홈페이지 내부 확인  : {args.lab_link_homepage_probe_pages}")
    print(f"전체 시간 예산(분)  : {args.lab_link_time_budget_minutes}")

    try:
        metrics = discover_lab_links_in_memory(client, departments, labs_by_id, paths, args)
    finally:
        client.close()
    if not metrics.get("committed_in_memory"):
        print("[ABORT-LAB-LINKS] 링크 안전성 검증 실패")
        for issue in metrics.get("issues", []):
            print(f"  - {issue}")
        print("원본 labs.csv는 변경하지 않았습니다.")
        return

    for lab_id in metrics.get("updated_lab_ids", []):
        row = labs_by_id.get(lab_id)
        if row is None:
            continue
        row["data_quality_status"] = data_quality_status(row)
        row["enricher_version"] = ENRICHER_VERSION
    final_rows = [labs_by_id[lab_id] for lab_id in lab_order if lab_id in labs_by_id]
    safety_issues = lab_link_safety_issues(before_rows, final_rows)
    if safety_issues:
        print("[ABORT-LAB-LINKS] 최종 검증 실패")
        for issue in safety_issues:
            print(f"  - {issue}")
        print("원본 labs.csv는 변경하지 않았습니다.")
        return

    if args.dry_run:
        print("[DRY-RUN] CSV에는 기록하지 않았습니다.")
    else:
        run_slug = timestamp_slug()
        backup_path = backup_file(paths.labs, paths.backups, run_slug)
        print(f"[BACKUP] labs.csv → {backup_path}")
        atomic_write_csv(paths.labs, final_rows, lab_fields)
        diagnostic_fields = [
            "lab_id", "professor_name", "email", "department_name", "result_class",
            "current_lab_url", "lab_url_status", "candidate_count", "candidate_urls",
            "verification_reasons", "recommendation",
        ]
        atomic_write_csv(paths.lab_link_diagnostics, metrics.get("diagnostic_rows", []), diagnostic_fields)
        prune_old_backups(paths.backups, args.backup_keep)
        print(f"저장: {paths.labs}")
        print(f"진단: {paths.lab_link_diagnostics}")
    print(f"중앙 인덱스 페이지 : {metrics.get('central_directory_pages', 0)}")
    print(f"중앙 인덱스 매칭   : {metrics.get('central_directory_matches', 0)}")
    print(f"소스 페이지        : {metrics.get('source_pages', 0)}")
    print(f"소스 요청 시도     : {metrics.get('source_attempts', 0)}")
    print(f"소스 요청 실패     : {metrics.get('source_failures', 0)}")
    print(f"호스트 상한 건너뜀 : {metrics.get('source_host_cap_skips', 0)}")
    print(f"시간 예산 도달     : {metrics.get('time_budget_exhausted', False)}")
    print(f"교수별 직접 페이지 : {metrics.get('individual_source_pages', 0)}")
    print(f"교수 카드 매칭     : {metrics.get('page_matches', 0)}")
    print(f"갱신 연구실        : {metrics.get('updated_labs', 0)}")
    print(f"홈페이지 직접 검증 : {metrics.get('verified_homepage', 0)}")
    print(f"공식 카드 검증     : {metrics.get('verified_card', 0)}")
    print(f"검토 후보          : {metrics.get('candidate_only', 0)}")
    print(f"연구실명 순증      : {metrics.get('lab_names_added', 0)}")
    print(f"연구실명 단계 갱신 : {metrics.get('lab_name_stage_updates', 0)}")
    print(f"학과페이지 오탐 제거: {metrics.get('invalid_department_urls_removed', 0)}")
    print(f"연구실명 정제      : {metrics.get('lab_names_sanitized', 0)}")
    print(f"영문명 승격        : {metrics.get('lab_names_promoted_from_eng', 0)}")
    print(f"출처 항목 누락 대상: {metrics.get('legacy_trusted_without_provenance', 0)}")
    print(f"출처 구조 불완전   : {metrics.get('legacy_trusted_incomplete_provenance', 0)}")
    print(f"신뢰 URL 재검증 대상: {metrics.get('revalidation_targets', 0)}")
    print(f"신뢰 URL 재검증 시도: {metrics.get('revalidation_attempts', 0)}")
    print(f"신뢰 URL 재검증 성공: {metrics.get('revalidation_success', 0)}")
    print(f"재검증 실패 분류   : {metrics.get('revalidation_failures', {})}")
    print(f"provenance-only 갱신: {metrics.get('provenance_only_updates', 0)}")
    print(f"공유 연구실 근거표시: {metrics.get('shared_lab_rows_marked', 0) + metrics.get('shared_lab_rows_marked_during_sanitation', 0)}")
    print(f"수동 출처 보완     : {metrics.get('manual_provenance_backfilled', 0)}")
    print(
        f"신뢰 URL 총계      : {metrics.get('trusted_before', 0)} → "
        f"{metrics.get('trusted_after', 0)}"
    )
    print(
        f"전체 URL 총계      : {metrics.get('any_url_before', 0)} → "
        f"{metrics.get('any_url_after', 0)}"
    )
    print(
        f"실제 연구실명 총계 : {metrics.get('actual_name_before', 0)} → "
        f"{metrics.get('actual_name_after', 0)}"
    )


# ============================================================
# 10. Merge and quality rules
# ============================================================
def text_quality(field_name: str, value: str, row: Optional[dict[str, str]] = None) -> int:
    text = clean_text(value)
    if not text:
        return 0
    if field_name == "professor_name":
        return professor_name_quality(text, (row or {}).get("department_name", ""))
    if field_name in {"lab_name_kor", "lab_name_eng"}:
        if field_name == "lab_name_kor" and looks_placeholder_lab_name(text):
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
    result["lab_name_eng"] = clean_lab_name(result.get("lab_name_eng", ""), professor_for_name)
    if (not result["lab_name_kor"] or looks_placeholder_lab_name(result["lab_name_kor"])) and result["lab_name_eng"]:
        result["lab_name_kor"] = result["lab_name_eng"]
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
    source_scope = clean_text(update.get("_source_scope", "primary")) or "primary"
    allow_secondary_fields = bool(update.get("_allow_secondary_field_enrichment", False))
    secondary_affiliation_only = source_scope == "secondary" and not allow_secondary_fields

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

    for field_name in (() if secondary_affiliation_only else merge_fields):
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

    incoming_url = "" if secondary_affiliation_only else clean_text(update.get("lab_url", ""))
    incoming_status = (
        "unverified"
        if secondary_affiliation_only
        else ("manual" if manual and incoming_url else clean_text(update.get("lab_url_status", "")))
    )
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
                for affiliation in split_multi(values.get("affiliated_programs", "")):
                    record_affiliation_evidence(merged, affiliation, "", "manual", False)
                record_field_provenance(merged, changed, "manual", "", "manual")
                merged["data_state"] = "manual_verified"
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


def reset_affiliations_for_full_rebuild(
    departments: list[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
) -> int:
    """Reset derived affiliations before a full authoritative recrawl.

    This is intentionally opt-in because older CSVs do not retain per-program
    provenance for each affiliation. Resetting to the primary department is the
    only safe way to remove previously accumulated cross-program contamination.
    """
    changed = 0
    for lab in labs_by_id.values():
        primary_name = clean_text(lab.get("department_name", ""))
        if clean_text(lab.get("affiliated_programs", "")) != primary_name:
            lab["affiliated_programs"] = primary_name
            changed += 1
    for department in departments:
        department["faculty_page_urls"] = ""
        department["faculty_match_count"] = "0"
        department["enrichment_status"] = "pending"
        department["enrichment_message"] = "소속 전체 재구축 대기"
        department["enriched_at"] = ""
        department["enricher_version"] = ENRICHER_VERSION
    return changed


def clear_non_authoritative_enrichment_for_full_rebuild(
    labs_by_id: dict[str, dict[str, str]],
) -> Counter[str]:
    """Discard stale Stage-2 fields before an authoritative full recrawl.

    A syntactically valid but wrong value can have the same quality score as a
    correct incoming value and therefore survive forever. Full ``--force`` runs
    now retain only manual values and fields independently verified from the
    exact professor's lab homepage. Department-card-derived values are rebuilt.
    """
    report: Counter[str] = Counter()
    for lab in labs_by_id.values():
        status = clean_text(lab.get("lab_url_status", ""))
        homepage_trusted = status in {"verified_homepage", "manual"}
        homepage_fields_trusted = homepage_trusted and clean_text(lab.get("keyword_source", "")) in {
            "lab_homepage",
            "manual",
        }

        # Preservation-first rebuild: verified-card and candidate-card links are
        # evidence-bearing observations, not disposable cache. Known department
        # pages and forbidden URLs are invalidated by the dedicated sanitation
        # pass; every other existing URL/name survives until stronger evidence
        # replaces it. This prevents a bounded recrawl from deleting data it did
        # not have enough time to rediscover.
        preserve_existing_link = bool(
            normalize_url(lab.get("lab_url", ""))
            and clean_text(lab.get("lab_url_status", "")) != "invalid"
        )
        if not preserve_existing_link and not homepage_trusted:
            for field_name in ("lab_name_eng", "location"):
                if clean_text(lab.get(field_name, "")):
                    lab[field_name] = ""
                    report[field_name] += 1
            lab_name = clean_text(lab.get("lab_name_kor", ""))
            if lab_name and not looks_placeholder_lab_name(lab_name):
                professor = clean_text(lab.get("professor_name", ""))
                lab["lab_name_kor"] = f"{professor} 교수 연구실" if professor else ""
                report["lab_name_kor"] += 1

        if clean_text(lab.get("keyword_source", "")) != "manual" and clean_text(lab.get("primary_field", "")):
            # primary_field is extracted from an official professor card; a lab
            # homepage verification does not prove this separate field.
            lab["primary_field"] = ""
            report["primary_field"] += 1

        if not homepage_fields_trusted:
            for field_name in (
                "research_summary",
                "keywords",
                "keyword_source",
            ):
                if clean_text(lab.get(field_name, "")):
                    lab[field_name] = ""
                    report[field_name] += 1

        if clean_text(lab.get("department_page_url", "")):
            lab["department_page_url"] = ""
            report["department_page_url"] += 1
        lab["enrichment_source_urls"] = sanitize_enrichment_source_urls(
            {**lab, "department_page_url": "", "enrichment_source_urls": ""}
        )
        lab["enrichment_status"] = "pending"
        lab["enrichment_message"] = "권위 소스 기반 전체 재수집 대기"
        lab["enriched_at"] = ""
        lab["enricher_version"] = ENRICHER_VERSION
    return report


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
        row.setdefault("affiliation_evidence", "")
        row.setdefault("field_provenance", "")
        row.setdefault("data_state", "legacy_unverified")
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
        # Name-only matching is restricted to the immutable primary department.
        # Secondary/program affiliations must be established by exact e-mail;
        # otherwise one stale affiliation can recursively create many more.
        if not primary_match:
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
        if row.get("faculty_page_urls"):
            valid_urls = [
                url for url in split_multi(row.get("faculty_page_urls", "")) if normalize_url(url)
            ]
            row["faculty_page_urls"] = merge_multi(*valid_urls)





def authoritative_rebuild_requested(args: argparse.Namespace) -> bool:
    return bool(
        not getattr(args, "clean_only", False)
        and not getattr(args, "department", None)
        and getattr(args, "test_limit", None) is None
        and not getattr(args, "incremental", False)
    )

def parse_json_dict(value: object) -> dict:
    text = clean_text(value)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_affiliation_evidence(
    row: dict[str, str],
    affiliation: str,
    source_url: str,
    method: str,
    primary: bool,
) -> None:
    affiliation = clean_text(affiliation)
    if not affiliation:
        return
    evidence = parse_json_dict(row.get("affiliation_evidence", ""))
    evidence[affiliation] = {
        "source_url": normalize_url(source_url),
        "method": clean_text(method),
        "primary": bool(primary),
        "verified_at": now_iso(),
    }
    row["affiliation_evidence"] = compact_json(evidence)


def record_field_provenance(
    row: dict[str, str],
    fields: Iterable[str],
    source_scope: str,
    source_url: str,
    method: str,
) -> None:
    provenance = parse_json_dict(row.get("field_provenance", ""))
    for field_name in fields:
        if field_name in {
            "enrichment_source_urls", "enrichment_status", "enrichment_message",
            "enriched_at", "enricher_version", "data_quality_status",
            "affiliated_programs", "affiliation_evidence", "field_provenance",
            "data_state",
        }:
            continue
        provenance[field_name] = {
            "scope": clean_text(source_scope),
            "source_url": normalize_url(source_url),
            "method": clean_text(method),
            "verified_at": now_iso(),
        }
    row["field_provenance"] = compact_json(provenance)


def primary_affiliation_evidence(row: dict[str, str]) -> str:
    primary_name = clean_text(row.get("department_name", ""))
    if not primary_name:
        return ""
    source_url = normalize_url(row.get("source_url", ""))
    evidence = {
        primary_name: {
            "source_url": source_url,
            "method": "stage1_primary_department",
            "primary": True,
            "verified_at": clean_text(row.get("crawled_at", "")) or now_iso(),
        }
    }
    return compact_json(evidence)


def remove_self_name_and_labels_from_research_fields(row: dict[str, str]) -> Counter[str]:
    changed: Counter[str] = Counter()
    own_name = normalize_name(row.get("professor_name", ""))
    field_labels = {normalize_name(value) for value in FIELD_LABELS}

    primary_items = []
    for item in split_multi(row.get("primary_field", "")):
        normalized = normalize_name(item)
        if not normalized or normalized == own_name or normalized in field_labels:
            changed["primary_field"] += 1
            continue
        primary_items.append(item)
    new_primary = clean_primary_field_value(";".join(primary_items))
    if new_primary != clean_text(row.get("primary_field", "")):
        row["primary_field"] = new_primary
        changed["primary_field"] += 1

    keyword_items = []
    for item in split_multi(row.get("keywords", "")):
        normalized = normalize_name(item)
        low = item.casefold()
        if normalized == own_name or normalized in field_labels:
            changed["keywords"] += 1
            continue
        if any(token in low for token in (
            "홈페이지 제작", "홈페이지 만들기", "무료 홈페이지", "포트폴리오 사이트",
            "크리에이터링크", "반응형웹", "반응형 홈페이지",
        )):
            changed["keywords"] += 1
            continue
        if re.search(r"(?:교수|연구팀).{0,30}(?:수상|선정|개최|게재)|(?:호텔|행사|개최됐다)", item):
            changed["keywords"] += 1
            continue
        keyword_items.append(item)
    new_keywords = clean_keywords_value(";".join(keyword_items))
    if new_keywords != clean_text(row.get("keywords", "")):
        row["keywords"] = new_keywords
        changed["keywords"] += 1

    summary = clean_text(row.get("research_summary", ""))
    if summary and re.fullmatch(r"[\"“‘][^\"”’]{20,}[\"”’]", summary):
        row["research_summary"] = ""
        changed["research_summary"] += 1
    return changed


def reset_foreign_department_provenance(
    departments: list[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
    overrides: dict,
) -> Counter[str]:
    """Quarantine fields whose last department page is foreign to the primary department.

    Legacy rows have no per-field provenance. A foreign ``department_page_url`` is
    therefore a strong contamination signal: another department/program page
    supplied plausible-looking values that quality scoring could never replace.
    Exact-homepage/manual values remain; card-derived values are blanked and must
    be reacquired from the professor's primary department page.
    """
    departments_by_id = {
        clean_text(row.get("department_id", "")): row
        for row in departments if clean_text(row.get("department_id", ""))
    }
    report: Counter[str] = Counter()
    for row in labs_by_id.values():
        primary_id = clean_text(row.get("primary_department_id", "") or row.get("department_id", ""))
        department = departments_by_id.get(primary_id)
        if not department:
            continue
        own_hosts = authoritative_department_hosts(
            department, resolve_department_override(overrides, department)
        )
        page_url = normalize_url(row.get("department_page_url", ""))
        page_host = hostname(page_url).removeprefix("www.")
        if not page_host or page_host in own_hosts:
            continue

        # Cross-listed faculty commonly appear on another official department's
        # roster. Exact-email per-field evidence is authoritative for that person
        # even when the host differs from the immutable primary department. Host
        # mismatch alone must never erase a directly matched current record.
        provenance = parse_json_dict(row.get("field_provenance", ""))
        exact_official_page_evidence = False
        for field_name, evidence in provenance.items():
            if not isinstance(evidence, dict):
                continue
            evidence_source = normalize_url(evidence.get("source_url", ""))
            method = clean_text(evidence.get("method", ""))
            if (
                canonical_url_key(evidence_source) == canonical_url_key(page_url)
                and is_official_postech_source(evidence_source)
                and "exact_email" in method
            ):
                exact_official_page_evidence = True
                break
        if exact_official_page_evidence:
            continue

        status = clean_text(row.get("lab_url_status", ""))
        keep_homepage = status in {"verified_homepage", "manual"}
        keep_homepage_content = keep_homepage and clean_text(row.get("keyword_source", "")) in {
            "lab_homepage", "manual"
        }

        if not keep_homepage:
            for field_name in (
                "lab_name_eng", "phone", "location", "profile_image_url", "primary_field",
            ):
                if clean_text(row.get(field_name, "")):
                    row[field_name] = ""
                    report[field_name] += 1
            lab_name = clean_text(row.get("lab_name_kor", ""))
            if lab_name and not looks_placeholder_lab_name(lab_name):
                professor = clean_text(row.get("professor_name", ""))
                row["lab_name_kor"] = f"{professor} 교수 연구실" if professor else ""
                report["lab_name_kor"] += 1
            if clean_text(row.get("lab_url", "")):
                row["lab_url"] = ""
                report["lab_url"] += 1
            row["lab_url_status"] = "unverified"

        if not keep_homepage_content:
            for field_name in ("research_summary", "keywords", "keyword_source"):
                if clean_text(row.get(field_name, "")):
                    row[field_name] = ""
                    report[field_name] += 1

        row["department_page_url"] = ""
        row["enrichment_source_urls"] = sanitize_enrichment_source_urls(
            {**row, "department_page_url": "", "enrichment_source_urls": ""}
        )
        row["field_provenance"] = ""
        row["enrichment_status"] = "pending"
        row["enrichment_message"] = "외부 학과 페이지 유래 필드 격리 후 주 소속 권위 페이지 재수집 대기"
        row["data_state"] = "foreign_source_quarantined"
        report["rows"] += 1
    return report


def quarantine_unverified_affiliations(
    departments: list[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
    overrides: dict,
) -> int:
    """Keep only secondary affiliations that satisfy the current evidence contract.

    Existing affiliation order is preserved. Clean-only must also preserve the
    successful faculty-page roster because scoped unique-name evidence depends
    on that immutable crawl record; deleting it makes a second clean pass remove
    affiliations that the first pass accepted.
    """
    changed = 0
    department_by_name = {
        clean_text(row.get("department_name_kor", "")): row
        for row in departments
        if clean_text(row.get("department_name_kor", ""))
    }
    for row in labs_by_id.values():
        primary = clean_text(row.get("department_name", ""))
        evidence = parse_json_dict(row.get("affiliation_evidence", ""))
        valid_secondary: list[str] = []
        # Preserve the user-facing/current authoritative ordering rather than
        # iterating a JSON object serialized with sort_keys=True.
        for name in split_multi(row.get("affiliated_programs", "")):
            if name == primary:
                continue
            item = evidence.get(name)
            if not isinstance(item, dict):
                continue
            method = clean_text(item.get("method", ""))
            source_url = normalize_url(item.get("source_url", ""))
            if method == "manual":
                valid_secondary.append(name)
                continue
            if method.startswith("email") and source_url:
                valid_secondary.append(name)
                continue
            if method == "unique_name_scoped_faculty_page":
                valid, _ = scoped_unique_name_evidence_status(
                    name, item, department_by_name, overrides
                )
                if valid:
                    valid_secondary.append(name)
        new_value = merge_multi(primary, valid_secondary)
        if new_value != clean_text(row.get("affiliated_programs", "")):
            row["affiliated_programs"] = new_value
            changed += 1
        retained_evidence = parse_json_dict(primary_affiliation_evidence(row))
        for affiliation in valid_secondary:
            retained_evidence[affiliation] = evidence[affiliation]
        row["affiliation_evidence"] = compact_json(retained_evidence)
        # Affiliation cleanup is a maintenance action, not source lineage.
        # Preserve data_state exactly; the caller may recover legacy states from
        # backups or reconstruct them from enrichment evidence.
    # Do not clear department faculty_page_urls/status in clean-only mode. They
    # are the source-of-truth evidence used above and are not derived noise.
    return changed


def exact_page_email_lab_ids(result: PageResult, labs_by_email: dict[str, str]) -> set[str]:
    return {
        labs_by_email[email]
        for email in {normalize_email(value) for value in EMAIL_RE.findall(result.html)}
        if email in labs_by_email
    }


def is_central_researcher_profile_url(url: str) -> bool:
    url = normalize_url(url)
    if not url:
        return False
    parsed = urlparse(url)
    return (
        parsed.hostname in CENTRAL_RESEARCHER_HOSTS
        and CENTRAL_RESEARCHER_PATH_TOKEN in parsed.path
        and clean_text((parse_qs(parsed.query).get("mode") or [""])[0]) == "view"
    )


def page_has_faculty_identity_context(result: PageResult, known_names: set[str]) -> bool:
    """Permit page-wide exact-email fallback only on a faculty identity page."""
    if is_non_identity_source_url(result.url):
        return False
    parsed = urlparse(result.url)
    url_text = f"{parsed.path} {parsed.query}".casefold()
    if any(token in url_text for token in ("faculty", "professor", "people", "member", "staff", "교수")):
        return True
    soup = result.soup
    if is_faculty_hub_page(soup, known_names):
        return True
    page_text = clean_text(soup.get_text(" ", strip=True)).casefold()
    faculty_terms = sum(
        term in page_text
        for term in ("교수", "교수진", "전임교수", "겸임교수", "faculty", "professor")
    )
    return faculty_terms >= 2 and bool(EMAIL_RE.search(result.html))


def central_profile_identity_matches(result: PageResult, lab: dict[str, str]) -> bool:
    if not is_central_researcher_profile_url(result.url):
        return False
    expected_email = normalize_email(lab.get("email", ""))
    if not expected_email:
        return False
    page_emails = {normalize_email(value) for value in EMAIL_RE.findall(result.html)}
    if expected_email not in page_emails:
        return False
    expected_name = normalize_name(lab.get("professor_name", ""))
    if not expected_name:
        return True
    page_text = normalize_name(result.soup.get_text(" ", strip=True))
    return expected_name in page_text


def verify_primary_roster_via_central_profiles(
    client: RespectfulClient,
    department: dict[str, str],
    expected_lab_ids: set[str],
    already_verified_ids: set[str],
    required_matches: int,
    labs_by_id: dict[str, dict[str, str]],
    paths: RuntimePaths,
    save_raw: bool,
) -> dict[str, str]:
    """Verify missing primary identities from official POSTECH profile pages.

    This path is identity-only. It never imports lab names, research fields,
    summaries, locations, lab URLs, or secondary affiliations.
    """
    verified: dict[str, str] = {}
    if required_matches <= len(already_verified_ids):
        return verified
    candidates: list[tuple[str, str]] = []
    for lab_id in sorted(expected_lab_ids - already_verified_ids):
        lab = labs_by_id.get(lab_id, {})
        source_url = normalize_url(lab.get("source_url", ""))
        if is_central_researcher_profile_url(source_url):
            candidates.append((lab_id, source_url))
    for index, (lab_id, source_url) in enumerate(candidates, start=1):
        if len(already_verified_ids) + len(verified) >= required_matches:
            break
        try:
            result = client.fetch(source_url)
        except Exception as exc:
            append_jsonl(
                paths.log,
                {
                    "timestamp": now_iso(),
                    "level": "central_identity_fallback_warning",
                    "department": department.get("department_name_kor", ""),
                    "lab_id": lab_id,
                    "source_url": source_url,
                    "message": str(exc),
                    "enricher_version": ENRICHER_VERSION,
                },
            )
            continue
        if not central_profile_identity_matches(result, labs_by_id.get(lab_id, {})):
            continue
        verified[lab_id] = result.url
        save_raw_html(
            paths,
            department.get("department_id", "UNKNOWN"),
            9000 + index,
            result,
            save_raw,
        )
    return verified


def canonical_evidence_url_key(url: str) -> tuple:
    """Canonical URL key used only for evidence-page equality checks.

    Redirected POSTECH pages frequently add an explicit :443 and reorder query
    parameters. Those changes do not alter page identity and must not turn a
    valid affiliation proof into a commit failure.
    """
    normalized = normalize_url(url)
    if not normalized:
        return ()
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    port = parsed.port
    if (parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80):
        port = None
    query = parse_qs(parsed.query, keep_blank_values=True)
    query_key = tuple(
        sorted(
            (clean_text(key), tuple(sorted(clean_text(value) for value in values)))
            for key, values in query.items()
        )
    )
    return (parsed.scheme.lower(), host, port, parsed.path or "/", query_key)


def scoped_unique_name_evidence_status(
    affiliation: str,
    item: dict,
    department_by_name: dict[str, dict[str, str]],
    overrides: dict,
) -> tuple[bool, str]:
    """Validate a name-only secondary affiliation against the exact official scope.

    A globally unique professor name is accepted only when the department has
    explicitly opted into this fallback, the source URL stays inside the
    department's hard host/query scope, and that exact page was visited during
    the successful authoritative rebuild.
    """
    department = department_by_name.get(clean_text(affiliation))
    if not department:
        return False, "unknown_affiliation"
    override = resolve_department_override(overrides, department)
    if not bool(override.get("allow_secondary_unique_name_affiliation", False)):
        return False, "scoped_name_not_allowed"
    source_url = normalize_url(item.get("source_url", ""))
    if not source_url:
        return False, "missing_source_url"
    if not url_matches_override_scope(source_url, override):
        return False, "source_outside_query_scope"
    source_host = hostname(source_url).removeprefix("www.")
    if source_host not in authoritative_department_hosts(department, override):
        return False, "source_outside_authoritative_host"
    visited_pages = {
        canonical_evidence_url_key(url)
        for url in split_multi(department.get("faculty_page_urls", ""))
        if canonical_evidence_url_key(url)
    }
    if canonical_evidence_url_key(source_url) not in visited_pages:
        return False, "source_not_in_successful_faculty_pages"
    return True, "verified_scoped_unique_name"


def affiliation_evidence_violations(
    labs: Iterable[dict[str, str]],
    departments: Optional[Sequence[dict[str, str]]] = None,
    overrides: Optional[dict] = None,
) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    department_by_name = {
        clean_text(row.get("department_name_kor", "")): row
        for row in (departments or [])
        if clean_text(row.get("department_name_kor", ""))
    }
    effective_overrides = overrides or effective_builtin_overrides()
    for row in labs:
        primary = clean_text(row.get("department_name", ""))
        evidence = parse_json_dict(row.get("affiliation_evidence", ""))
        for affiliation in split_multi(row.get("affiliated_programs", "")):
            if affiliation == primary:
                continue
            item = evidence.get(affiliation)
            base = {
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "email": normalize_email(row.get("email", "")),
                "affiliation": affiliation,
            }
            if not isinstance(item, dict):
                violations.append({**base, "reason": "missing_evidence"})
                continue
            method = clean_text(item.get("method", ""))
            source_url = normalize_url(item.get("source_url", ""))
            if method == "manual":
                continue
            if method.startswith("email") and source_url:
                continue
            if method == "unique_name_scoped_faculty_page":
                valid, reason = scoped_unique_name_evidence_status(
                    affiliation, item, department_by_name, effective_overrides
                )
                if valid:
                    continue
                violations.append({
                    **base,
                    "method": method,
                    "source_url": source_url,
                    "reason": reason,
                })
                continue
            violations.append({
                **base,
                "method": method,
                "source_url": source_url,
                "reason": "weak_evidence",
            })
    return violations

def minimum_primary_roster_matches(expected_count: int, override: dict) -> int:
    """Minimum known-primary identities that must be recovered from a department page.

    The baseline is the first-stage roster already keyed by stable e-mail. This is
    not a guessed faculty count: it only prevents a one-card or menu-only parse
    from being accepted as a successful full department rebuild.
    """
    if expected_count <= 0:
        return 0
    try:
        ratio = float(override.get("min_primary_roster_coverage", DEFAULT_MIN_PRIMARY_ROSTER_COVERAGE))
    except (TypeError, ValueError):
        ratio = DEFAULT_MIN_PRIMARY_ROSTER_COVERAGE
    ratio = min(1.0, max(0.0, ratio))
    ratio_required = int(expected_count * ratio + 0.999)
    floor = 1 if expected_count <= 3 else 2
    return min(expected_count, max(floor, ratio_required))


def foreign_department_page_violations(
    departments: Sequence[dict[str, str]],
    labs: Iterable[dict[str, str]],
    overrides: dict,
) -> list[dict[str, str]]:
    department_by_id = {
        clean_text(row.get("department_id", "")): row
        for row in departments
        if clean_text(row.get("department_id", ""))
    }
    violations: list[dict[str, str]] = []
    for row in labs:
        primary_id = clean_text(row.get("primary_department_id", "") or row.get("department_id", ""))
        department = department_by_id.get(primary_id)
        page_url = normalize_url(row.get("department_page_url", ""))
        if not department or not page_url:
            continue
        own_hosts = authoritative_department_hosts(
            department, resolve_department_override(overrides, department)
        )
        page_host = hostname(page_url).removeprefix("www.")
        if page_host and page_host not in own_hosts:
            violations.append(
                {
                    "lab_id": clean_text(row.get("lab_id", "")),
                    "professor_name": clean_text(row.get("professor_name", "")),
                    "department_page_url": page_url,
                }
            )
    return violations


def authoritative_commit_failure_reasons(
    selected_departments: Sequence[dict[str, str]],
    labs: Iterable[dict[str, str]],
    overrides: dict,
) -> tuple[list[str], dict]:
    accepted_statuses = {"success", "success_identity_fallback"}
    failed_departments = [
        {
            "department_id": clean_text(row.get("department_id", "")),
            "department_name": clean_text(row.get("department_name_kor", "")),
            "status": clean_text(row.get("enrichment_status", "")) or "unknown",
            "message": clean_text(row.get("enrichment_message", "")),
            "faculty_match_count": clean_text(row.get("faculty_match_count", "")),
        }
        for row in selected_departments
        if clean_text(row.get("enrichment_status", "")) not in accepted_statuses
    ]
    successful_departments = len(selected_departments) - len(failed_departments)
    minimum_successes = max(
        1, int(len(selected_departments) * MIN_AUTHORITATIVE_SUCCESS_RATIO + 0.999)
    ) if selected_departments else 0
    lab_rows = list(labs)
    evidence_violations = affiliation_evidence_violations(
        lab_rows, selected_departments, overrides
    )
    foreign_violations = foreign_department_page_violations(
        selected_departments, lab_rows, overrides
    )
    reasons: list[str] = []
    if successful_departments < minimum_successes:
        names = ", ".join(item["department_name"] for item in failed_departments) or "알 수 없음"
        reasons.append(
            f"학과 성공 {successful_departments}/{len(selected_departments)} < 최소 {minimum_successes}; "
            f"실패={names}"
        )
    if evidence_violations:
        reasons.append(f"복수소속 증거 위반 {len(evidence_violations)}건")
    if foreign_violations:
        reasons.append(f"주 소속 외부 페이지 출처 {len(foreign_violations)}건")
    return reasons, {
        "successful_departments": successful_departments,
        "minimum_successes": minimum_successes,
        "failed_departments": failed_departments,
        "affiliation_evidence_violations": len(evidence_violations),
        "affiliation_evidence_violation_details": evidence_violations,
        "foreign_department_page_violations": len(foreign_violations),
    }


def write_authoritative_rebuild_report(
    paths: RuntimePaths,
    selected_departments: Sequence[dict[str, str]],
    failure_reasons: Sequence[str],
    commit_metrics: dict,
    committed: bool,
) -> None:
    payload = {
        "generated_at": now_iso(),
        "enricher_version": ENRICHER_VERSION,
        "committed": committed,
        "failure_reasons": list(failure_reasons),
        **commit_metrics,
        "departments": [
            {
                "department_id": clean_text(row.get("department_id", "")),
                "department_name": clean_text(row.get("department_name_kor", "")),
                "department_type": clean_text(row.get("department_type", "")),
                "status": clean_text(row.get("enrichment_status", "")),
                "faculty_match_count": clean_text(row.get("faculty_match_count", "")),
                "message": clean_text(row.get("enrichment_message", "")),
                "faculty_page_urls": split_multi(row.get("faculty_page_urls", "")),
            }
            for row in selected_departments
        ],
    }
    atomic_write_json(paths.rebuild_report, payload)


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
    legacy_provenance_migrated = migrate_all_legacy_lab_url_provenance(labs_by_id)
    protected_link_snapshot = snapshot_protected_link_fields(labs_by_id)
    local_link_sanitation: dict[str, object] = {}
    data_state_repair = {"preserved": 0, "restored_from_backup": 0, "reconstructed": 0}
    if args.clean_only:
        # Local-only integrity repair: remove known department/faculty pages
        # falsely stored as lab homepages and normalize lab-name fields.
        local_link_sanitation = sanitize_existing_lab_link_records(departments, labs_by_id)
        data_state_repair = recover_data_states_from_backups(labs_by_id, paths.backups)
    full_scope = not args.department and args.test_limit is None
    # A normal unscoped run is authoritative by default. Incremental behavior
    # must be explicitly requested; otherwise a stale "success" flag can freeze
    # contaminated values indefinitely.
    authoritative_rebuild = authoritative_rebuild_requested(args)
    effective_force = bool(args.force or authoritative_rebuild)
    # Full source-of-truth rebuilds are globally transactional. Intermediate
    # department checkpoints remain in memory and are committed only after the
    # minimum success ratio and evidence checks pass.
    checkpoint_dry_run = bool(args.dry_run or authoritative_rebuild)
    reset_affiliation_count = 0
    authoritative_field_reset_report: Counter[str] = Counter()
    stale_identity_report: Counter[str] = Counter()
    foreign_source_report = reset_foreign_department_provenance(
        departments, labs_by_id, overrides
    )
    quarantined_affiliation_count = 0
    if args.clean_only:
        quarantined_affiliation_count = quarantine_unverified_affiliations(
            departments, labs_by_id, overrides
        )
    elif args.reset_affiliations or authoritative_rebuild:
        reset_affiliation_count = reset_affiliations_for_full_rebuild(departments, labs_by_id)
        for lab in labs_by_id.values():
            lab["affiliation_evidence"] = primary_affiliation_evidence(lab)
            # Preserve per-field evidence, especially lab_url provenance. New
            # authoritative observations overwrite their own keys and retain
            # history; a full crawl must never erase unrelated verified facts.
            lab["data_state"] = "authoritative_rebuild_pending"
        authoritative_field_reset_report = clear_non_authoritative_enrichment_for_full_rebuild(labs_by_id)
    stale_identity_report = reset_stale_cross_identity_contamination(
        departments,
        labs_by_id,
        overrides,
    )
    extra_clean_report: Counter[str] = Counter()
    for lab in labs_by_id.values():
        extra_clean_report.update(remove_self_name_and_labels_from_research_fields(lab))

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
    if foreign_source_report:
        print(f"외부 학과 출처 격리   : {dict(foreign_source_report)}")
    if args.clean_only:
        print(f"증거 없는 소속 격리   : {quarantined_affiliation_count}개 연구실")
        print(f"학과페이지 링크 제거  : {local_link_sanitation.get('invalidated_count', 0)}개")
        print(f"연구실명 로컬 정제    : {local_link_sanitation.get('names_cleaned', 0)}개")
        print(f"수동 링크 출처 보완   : {local_link_sanitation.get('manual_provenance_backfilled', 0)}개")
        print(
            "data_state 복구      : "
            f"백업 {data_state_repair.get('restored_from_backup', 0)}개, "
            f"재구성 {data_state_repair.get('reconstructed', 0)}개, "
            f"보존 {data_state_repair.get('preserved', 0)}개"
        )
    if args.reset_affiliations or authoritative_rebuild:
        mode_label = "명시적" if args.reset_affiliations else "기본 전체 권위 재구축"
        print(f"소속 전체 초기화      : {reset_affiliation_count}개 연구실 ({mode_label})")
        print(f"비권위 필드 초기화    : {dict(authoritative_field_reset_report)}")
    if stale_identity_report:
        print(f"동명이인 오염 초기화  : {dict(stale_identity_report)}")
    if extra_clean_report:
        print(f"연구필드 추가 정제    : {dict(extra_clean_report)}")
    print()

    if args.clean_only:
        # Manual overrides are deterministic local corrections and therefore
        # also apply in clean-only mode. This lets known names/URLs be repaired
        # without requiring a network crawl.
        manual_count = apply_manual_overrides(labs_by_id, overrides)
        for lab in labs_by_id.values():
            lab["data_quality_status"] = data_quality_status(lab)
            # clean-only describes a maintenance action, not source lineage.
            # Preserve or reconstruct data_state; never overwrite it with a
            # blanket cleaning marker.
            if not clean_text(lab.get("data_state", "")):
                lab["data_state"] = infer_data_state(lab)
            lab["enricher_version"] = ENRICHER_VERSION
        for row in departments:
            row["enricher_version"] = ENRICHER_VERSION
        save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run)
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
                "data_state_repair": data_state_repair,
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
    primary_lab_ids_by_department: defaultdict[str, set[str]] = defaultdict(set)
    for lab_id, lab in labs_by_id.items():
        primary_id = clean_text(lab.get("primary_department_id", "") or lab.get("department_id", ""))
        if primary_id:
            primary_lab_ids_by_department[primary_id].add(lab_id)
    professor_name_counts = Counter(
        normalize_name(lab.get("professor_name", ""))
        for lab in labs_by_id.values()
        if normalize_name(lab.get("professor_name", ""))
    )
    ambiguous_professor_names = {
        name for name, count in professor_name_counts.items() if count >= 2
    }

    client = RespectfulClient(
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        connect_timeout_seconds=args.connect_timeout,
        browser_fallback=args.browser_fallback,
        allow_insecure=args.allow_insecure,
        respect_robots=not args.ignore_robots,
        retry_total=max(3, args.http_retries),
        max_host_failures=0,
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

        if not effective_force and clean_text(department.get("enrichment_status", "")) == "success":
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
        # Shared-portal runs are transactional. If a selector/navigation defect
        # suddenly matches an implausibly large number of professors, every lab
        # mutation made by this department is rolled back before any checkpoint.
        guarded_department = bool(override.get("scope_query_params"))
        # Every department run is transactional in memory. A scope/completeness
        # failure restores the state from immediately before that department.
        department_lab_snapshot = deepcopy(labs_by_id)
        touched_lab_ids_snapshot = set(touched_lab_ids)
        primary_name_to_lab_id = build_department_name_index(
            labs_by_id, department, unique_name_to_lab_id
        )
        allow_secondary_unique_name = bool(
            override.get("allow_secondary_unique_name_affiliation", False)
        )
        # Program/division rosters often contain only professors whose immutable
        # primary department is elsewhere. On explicitly scoped official pages,
        # globally unique names may establish affiliation only; they can never
        # supply lab descriptive fields.
        eligible_name_to_lab_id = (
            dict(unique_name_to_lab_id)
            if allow_secondary_unique_name
            else dict(primary_name_to_lab_id)
        )
        eligible_name_to_lab_id.update(primary_name_to_lab_id)
        discovery_error = ""
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
            # Do not stop here. Primary departments can still be identity-verified
            # through official central POSTECH researcher profiles below.
            discovery_error = str(exc)
            pages = []
            print(f"[WARN-DEPT] {department_name} | 학과 페이지 탐색 실패, 중앙 프로필 fallback 시도 | {exc}")
            append_jsonl(
                paths.log,
                {
                    "timestamp": now_iso(),
                    "level": "department_discovery_failed_fallback_pending",
                    "department": department_name,
                    "department_id": department_id,
                    "message": discovery_error,
                    "enricher_version": ENRICHER_VERSION,
                },
            )

        department_match_ids: set[str] = set()
        faculty_pages: set[str] = set()
        field_update_counts: Counter[str] = Counter()
        page_exact_evidence_ids: set[str] = set()
        exact_evidence_source_by_lab_id: dict[str, str] = {}
        primary_name_evidence_ids: set[str] = set()
        identity_fallback_ids: set[str] = set()
        secondary_name_fallback_ids: set[str] = set()
        central_fallback_ids: set[str] = set()

        for result in pages:
            exact_ids = exact_page_email_lab_ids(result, labs_by_email)
            if page_has_faculty_identity_context(result, normalized_known_names):
                page_exact_evidence_ids.update(exact_ids)
                for exact_lab_id in exact_ids:
                    exact_evidence_source_by_lab_id.setdefault(exact_lab_id, result.url)
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
                current_primary_id = clean_text(
                    current.get("primary_department_id", "") or current.get("department_id", "")
                )
                is_primary_source = bool(department_id and department_id == current_primary_id)
                secondary_name_identity_only = bool(
                    not is_primary_source and match.method.startswith("name")
                )
                if secondary_name_identity_only:
                    safe_secondary_name = bool(
                        allow_secondary_unique_name
                        and page_has_faculty_identity_context(result, normalized_known_names)
                    )
                    if not safe_secondary_name:
                        print(
                            f"    [REJECT] 학과={department_name} | "
                            f"교수={current.get('professor_name', '-') or '-'} | "
                            f"방식={match.method} | 보조소속 이름 증거가 안전 조건을 충족하지 않음"
                        )
                        continue
                    merged = dict(current)
                    merged["affiliated_programs"] = merge_multi(
                        merged.get("affiliated_programs", ""), department_name
                    )
                    record_affiliation_evidence(
                        merged,
                        department_name,
                        result.url,
                        "unique_name_scoped_faculty_page",
                        False,
                    )
                    merged["enrichment_source_urls"] = sanitize_enrichment_source_urls(
                        merged, [result.url]
                    )
                    merged["enrichment_status"] = "matched_identity_only"
                    merged["enrichment_message"] = (
                        f"{department_name} 범위 고정 공식 교수 페이지에서 "
                        "전역 고유 교수명 확인; 연구실 필드는 복사하지 않음"
                    )
                    merged["enriched_at"] = now_iso()
                    merged["enricher_version"] = ENRICHER_VERSION
                    merged["data_state"] = (
                        "authoritative_identity_only"
                        if authoritative_rebuild
                        else "incremental_identity_only"
                    )
                    merged["data_quality_status"] = data_quality_status(merged)
                    labs_by_id[match.lab_id] = merged
                    department_match_ids.add(match.lab_id)
                    touched_lab_ids.add(match.lab_id)
                    secondary_name_fallback_ids.add(match.lab_id)
                    print(
                        f"    [SCOPED-NAME] 학과={department_name} | "
                        f"교수={merged.get('professor_name', '-') or '-'} | 소속만 확인"
                    )
                    append_jsonl(
                        paths.log,
                        {
                            "timestamp": now_iso(),
                            "level": "secondary_unique_name_affiliation",
                            "department_type": department_type,
                            "department": department_name,
                            "department_id": department_id,
                            "lab_id": merged.get("lab_id", ""),
                            "professor": merged.get("professor_name", ""),
                            "match_method": match.method,
                            "page_url": result.url,
                            "enricher_version": ENRICHER_VERSION,
                        },
                    )
                    continue
                if not is_primary_source and not match.method.startswith("email"):
                    print(
                        f"    [REJECT] 학과={department_name} | 교수={current.get('professor_name', '-') or '-'} | "
                        f"방식={match.method} | 보조소속은 정확 이메일 또는 범위 고정 고유이름 증거 필요"
                    )
                    continue
                if is_primary_source and match.method.startswith("name"):
                    primary_name_evidence_ids.add(match.lab_id)
                update["_source_scope"] = "primary" if is_primary_source else "secondary"
                update["_allow_secondary_field_enrichment"] = bool(
                    override.get("allow_secondary_field_enrichment", False)
                )
                if not is_primary_source:
                    # Secondary program pages establish affiliation only unless
                    # explicitly opted in. They must not become the primary
                    # source URL for a professor's research fields.
                    update["department_page_url"] = ""
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

                record_affiliation_evidence(
                    merged,
                    department_name,
                    result.url,
                    match.method,
                    is_primary_source,
                )
                record_field_provenance(
                    merged,
                    changed_fields,
                    "primary" if is_primary_source else "secondary",
                    result.url,
                    match.method,
                )
                merged["data_state"] = (
                    "authoritative_rebuilt" if authoritative_rebuild else "incremental_verified"
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

        # Exact e-mail on an official faculty page is sufficient for identity
        # and affiliation even when the site's DOM does not expose a card.
        # No descriptive fields are copied in this fallback path.
        for exact_lab_id, exact_source_url in sorted(exact_evidence_source_by_lab_id.items()):
            if exact_lab_id in department_match_ids:
                continue
            current = labs_by_id.get(exact_lab_id)
            if not current:
                continue
            current_primary_id = clean_text(
                current.get("primary_department_id", "") or current.get("department_id", "")
            )
            is_primary_source = bool(department_id and department_id == current_primary_id)
            merged = dict(current)
            if is_primary_source:
                merged["department_page_url"] = exact_source_url
                merged["enrichment_source_urls"] = sanitize_enrichment_source_urls(
                    merged, [exact_source_url]
                )
            else:
                merged["affiliated_programs"] = merge_multi(
                    merged.get("affiliated_programs", ""), department_name
                )
            record_affiliation_evidence(
                merged,
                department_name,
                exact_source_url,
                "email_page_identity_only",
                is_primary_source,
            )
            merged["enrichment_status"] = "matched_identity_only"
            merged["enrichment_message"] = (
                f"{department_name} 공식 교수 페이지에서 정확 이메일 신원 확인; "
                "카드 필드는 복사하지 않음"
            )
            merged["enriched_at"] = now_iso()
            merged["enricher_version"] = ENRICHER_VERSION
            merged["data_state"] = (
                "authoritative_identity_only" if authoritative_rebuild else "incremental_identity_only"
            )
            merged["data_quality_status"] = data_quality_status(merged)
            labs_by_id[exact_lab_id] = merged
            department_match_ids.add(exact_lab_id)
            touched_lab_ids.add(exact_lab_id)
            identity_fallback_ids.add(exact_lab_id)
            print(
                f"    [EMAIL-IDENTITY] 학과={department_name} | "
                f"교수={merged.get('professor_name', '-') or '-'} | 카드 없이 정확 이메일 확인"
            )

        supported_ids = page_exact_evidence_ids | primary_name_evidence_ids
        expected_primary_ids = primary_lab_ids_by_department.get(department_id, set())
        recovered_primary_ids = supported_ids & expected_primary_ids
        required_primary_matches = minimum_primary_roster_matches(
            len(expected_primary_ids), override
        )
        if required_primary_matches and len(recovered_primary_ids) < required_primary_matches:
            central_verified = verify_primary_roster_via_central_profiles(
                client,
                department,
                expected_primary_ids,
                recovered_primary_ids,
                required_primary_matches,
                labs_by_id,
                paths,
                args.save_raw_html,
            )
            for fallback_lab_id, fallback_url in central_verified.items():
                fallback_lab = labs_by_id.get(fallback_lab_id)
                if not fallback_lab:
                    continue
                fallback_lab["enrichment_status"] = "matched_identity_only"
                fallback_lab["enrichment_message"] = (
                    f"{department_name} 학과 사이트 직접 확인 부족; "
                    "POSTECH 중앙 연구자 프로필에서 교수명·이메일 재확인"
                )
                fallback_lab["enriched_at"] = now_iso()
                fallback_lab["enricher_version"] = ENRICHER_VERSION
                fallback_lab["data_state"] = "authoritative_central_identity_fallback"
                fallback_lab["data_quality_status"] = data_quality_status(fallback_lab)
                labs_by_id[fallback_lab_id] = fallback_lab
                department_match_ids.add(fallback_lab_id)
                touched_lab_ids.add(fallback_lab_id)
                central_fallback_ids.add(fallback_lab_id)
                recovered_primary_ids.add(fallback_lab_id)
                print(
                    f"    [CENTRAL-FALLBACK] 학과={department_name} | "
                    f"교수={fallback_lab.get('professor_name', '-') or '-'} | {fallback_url}"
                )

        if required_primary_matches and len(recovered_primary_ids) < required_primary_matches:
            labs_by_id.clear()
            labs_by_id.update(deepcopy(department_lab_snapshot))
            touched_lab_ids.clear()
            touched_lab_ids.update(touched_lab_ids_snapshot)
            department["enrichment_status"] = "failed_completeness_guard"
            department["enrichment_message"] = (
                f"기존 주 소속 이메일 로스터 {len(expected_primary_ids)}명 중 "
                f"{len(recovered_primary_ids)}명만 재확인; 최소 {required_primary_matches}명 필요"
            )
            department["faculty_match_count"] = "0"
            department["enriched_at"] = now_iso()
            department["enricher_version"] = ENRICHER_VERSION
            print(
                f"[ROLLBACK-COVERAGE] 학과={department_name} | "
                f"재확인={len(recovered_primary_ids)}/{len(expected_primary_ids)} | "
                f"최소={required_primary_matches}"
            )
            save_checkpoint(
                paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run
            )
            continue

        if guarded_department:
            # Scoped-portal protection must recognize all authoritative identity
            # channels. Central POSTECH profiles explain primary-department
            # matches, while compact globally-unique names explain affiliation
            # matches on the exact scoped program page.
            guard_supported_ids = (
                supported_ids | central_fallback_ids | secondary_name_fallback_ids
            )
            allowed_matches = max(
                len(guard_supported_ids) + 3,
                int(len(guard_supported_ids) * 1.20) + 1,
            )
            unsupported_ids = department_match_ids - guard_supported_ids
            evidence_mismatch = bool(
                department_match_ids
                and (len(department_match_ids) > allowed_matches or len(unsupported_ids) > 3)
            )
            if evidence_mismatch:
                labs_by_id.clear()
                labs_by_id.update(deepcopy(department_lab_snapshot or {}))
                touched_lab_ids.clear()
                touched_lab_ids.update(touched_lab_ids_snapshot or set())
                department["enrichment_status"] = "failed_scope_guard"
                department["enrichment_message"] = (
                    f"권위 신원증거={len(guard_supported_ids)}, 매칭={len(department_match_ids)}, "
                    f"설명불가={len(unsupported_ids)}; 학과 변경 전체 롤백"
                )
                department["faculty_match_count"] = "0"
                department["enriched_at"] = now_iso()
                department["enricher_version"] = ENRICHER_VERSION
                print(
                    f"[ROLLBACK-DEPT] 학과={department_name} | 권위증거={len(guard_supported_ids)} | "
                    f"매칭={len(department_match_ids)} | 설명불가={len(unsupported_ids)}"
                )
                save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run)
                continue

        if rollback_department_if_scope_overflow(
            override,
            len(department_match_ids),
            department,
            labs_by_id,
            department_lab_snapshot,
            touched_lab_ids,
            touched_lab_ids_snapshot,
        ):
            max_matches = int(override.get("max_total_matches"))
            print(
                f"[ROLLBACK-DEPT] 구분={type_label} | 학과={department_name} | "
                f"매칭={len(department_match_ids)} > 상한={max_matches}"
            )
            append_jsonl(
                paths.log,
                {
                    "timestamp": now_iso(),
                    "level": "scope_overflow",
                    "department_type": department_type,
                    "department": department_name,
                    "department_id": department_id,
                    "matched_count": len(department_match_ids),
                    "max_total_matches": max_matches,
                    "rolled_back": True,
                    "enricher_version": ENRICHER_VERSION,
                },
            )
            save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run)
            continue

        if not args.skip_lab_homepages:
            for lab_id in sorted(department_match_ids):
                lab = labs_by_id[lab_id]
                lab_url = normalize_url(lab.get("lab_url", ""))
                if not lab_url or lab.get("lab_url_status") in {"manual", "invalid"}:
                    continue
                if (
                    not effective_force
                    and lab.get("lab_url_status") == "verified_homepage"
                    and not looks_placeholder_lab_name(lab.get("lab_name_kor", ""))
                    and clean_text(lab.get("research_summary", ""))
                    and len(split_multi(lab.get("keywords", ""))) >= 2
                ):
                    continue
                try:
                    homepage_identity = dict(lab)
                    homepage_identity["_name_is_ambiguous"] = (
                        normalize_name(lab.get("professor_name", "")) in ambiguous_professor_names
                    )
                    homepage_update = enrich_from_lab_homepage(client, homepage_identity)
                    homepage_update["_source_scope"] = "lab_homepage"
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
                    record_field_provenance(
                        merged, changed, "lab_homepage", lab_url, "homepage_identity_verified"
                    )
                    merged["data_state"] = (
                        "authoritative_rebuilt" if authoritative_rebuild else "incremental_verified"
                    )
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
            department["enrichment_status"] = (
                "success_identity_fallback"
                if central_fallback_ids and not (department_match_ids - central_fallback_ids)
                else "success"
            )
            summary_parts = [
                f"{key}={value}" for key, value in sorted(field_update_counts.items())
            ]
            if identity_fallback_ids:
                summary_parts.append(f"exact_email_identity_only={len(identity_fallback_ids)}")
            if secondary_name_fallback_ids:
                summary_parts.append(
                    f"scoped_unique_name_affiliation={len(secondary_name_fallback_ids)}"
                )
            if central_fallback_ids:
                summary_parts.append(f"central_profile_identity={len(central_fallback_ids)}")
            summary = ", ".join(summary_parts)
            department["enrichment_message"] = (
                f"교수/랩 {len(department_match_ids)}명 권위 확인" + (f"; {summary}" if summary else "")
            )
        else:
            department["enrichment_status"] = "no_match"
            department["enrichment_message"] = "교수 카드 또는 기존 교수와의 안전한 매칭을 찾지 못함"

        print(
            f"[DONE-DEPT] 구분={type_label} | 학과={department_name} | "
            f"매칭={len(department_match_ids)} | 교수페이지={len(faculty_pages)}"
        )

        if department_index % DEFAULT_CHECKPOINT_EVERY == 0:
            save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run)

    lab_link_metrics: dict = {}
    if not args.skip_lab_homepages:
        print("\n" + "-" * 100)
        print("[LAB-LINK-FIRST] 공식 교수·연구실 디렉터리와 개별 홈페이지를 교차 검증합니다.")
        lab_link_metrics = discover_lab_links_in_memory(
            client, departments, labs_by_id, paths, args
        )
        touched_lab_ids.update(lab_link_metrics.get("updated_lab_ids", []))
        if not lab_link_metrics.get("committed_in_memory", False):
            print("[LAB-LINK-ROLLBACK] 링크 단계만 롤백했습니다.")
            for issue in lab_link_metrics.get("issues", []):
                print(f"  - {issue}")
        else:
            print(
                "[LAB-LINK-DONE] "
                f"소스={lab_link_metrics.get('source_pages', 0)}, "
                f"갱신={lab_link_metrics.get('updated_labs', 0)}, "
                f"verified_homepage={lab_link_metrics.get('verified_homepage', 0)}, "
                f"verified_card={lab_link_metrics.get('verified_card', 0)}, "
                f"연구실명 추가={lab_link_metrics.get('lab_names_added', 0)}"
            )

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
        if lab.get("lab_id") in touched_lab_ids:
            current_state = clean_text(lab.get("data_state", ""))
            identity_states = {
                "authoritative_identity_only",
                "authoritative_central_identity_fallback",
                "incremental_identity_only",
            }
            if current_state not in identity_states:
                lab["data_state"] = "authoritative_rebuilt" if authoritative_rebuild else "incremental_verified"
        elif authoritative_rebuild and clean_text(lab.get("data_state", "")) == "authoritative_rebuild_pending":
            lab["data_state"] = "authoritative_no_match"
        lab["enricher_version"] = ENRICHER_VERSION

    link_regression_repairs = restore_unexplained_link_regressions(
        labs_by_id, protected_link_snapshot
    )
    # Re-run schema migration because a restored legacy record may still lack
    # verified_url. Evidence-free records remain queued for network revalidation.
    legacy_provenance_migrated += migrate_all_legacy_lab_url_provenance(labs_by_id)
    for lab in labs_by_id.values():
        lab["data_quality_status"] = data_quality_status(lab)

    failure_reasons, commit_metrics = authoritative_commit_failure_reasons(
        selected_departments, labs_by_id.values(), overrides
    )
    commit_metrics["legacy_provenance_migrated"] = legacy_provenance_migrated
    commit_metrics["link_regression_repairs"] = dict(link_regression_repairs)
    if authoritative_rebuild and not args.dry_run and failure_reasons:
        append_jsonl(
            paths.log,
            {
                "timestamp": now_iso(),
                "level": "authoritative_commit_aborted",
                "reasons": failure_reasons,
                **commit_metrics,
                "selected_departments": len(selected_departments),
                "enricher_version": ENRICHER_VERSION,
            },
        )
        write_authoritative_rebuild_report(
            paths, selected_departments, failure_reasons, commit_metrics, committed=False
        )
        print("\n[ABORT-COMMIT] 전체 권위 재구축 검증 실패")
        for reason in failure_reasons:
            print(f"  - {reason}")
        for item in commit_metrics.get("failed_departments", []):
            print(
                f"    · {item.get('department_name', '-')}: "
                f"{item.get('status', '-')} | {item.get('message', '-') or '-'}"
            )
        print(f"진단 보고서: {paths.rebuild_report}")
        print("원본 departments.csv/labs.csv는 변경하지 않았습니다. 백업만 생성되었습니다.")
        return

    save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, args.dry_run)

    if authoritative_rebuild and not args.dry_run:
        write_authoritative_rebuild_report(
            paths, selected_departments, [], commit_metrics, committed=True
        )

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
            "legacy_provenance_migrated": legacy_provenance_migrated,
            "link_regression_repairs": dict(link_regression_repairs),
            "quality_counts": dict(quality_counts),
            "status_counts": dict(status_counts),
            "lab_url_status_counts": dict(url_status_counts),
            "lab_link_first": {
                key: value for key, value in lab_link_metrics.items()
                if key != "updated_lab_ids"
            },
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
    print(f"구형 provenance 이관: {legacy_provenance_migrated}")
    print(f"링크 퇴행 자동 복구 : {dict(link_regression_repairs)}")
    print(f"품질 상태       : {dict(quality_counts)}")
    print(f"수집 상태       : {dict(status_counts)}")
    print(f"URL 상태        : {dict(url_status_counts)}")
    if args.dry_run:
        print("DRY RUN이므로 CSV에는 기록하지 않았습니다.")
    else:
        print(f"저장: {paths.labs}")
        print(f"저장: {paths.departments}")
        print(f"로그: {paths.log}")

    if (
        authoritative_rebuild
        and not args.dry_run
        and not args.skip_research_cleaning
        and (paths.data_dir / "research_outputs.csv").exists()
    ):
        run_research_output_cleaner(args)
    if authoritative_rebuild and not args.dry_run and not args.skip_final_audit:
        run_data_audit(args)


# ============================================================
# 13. Research-output integrity pipeline and data audit
# ============================================================
OUTPUT_FIELDS = [
    "output_id",
    "lab_id",
    "researcher_id",
    "output_type",
    "output_subtype",
    "title",
    "year",
    "venue_or_organization",
    "authors_or_recipients",
    "identifier",
    "raw_text",
    "url",
    "source_url",
    "crawled_at",
]

RECENT_OUTPUT_FIELDS = [
    "output_id",
    "lab_id",
    "output_type",
    "title",
    "year",
    "venue",
    "authors",
    "identifier",
    "url",
    "source_url",
    "display_order",
]

OUTPUT_TYPE_PRECEDENCE = {
    "publication": 1,
    "presentation": 2,
    "book": 3,
    "patent": 4,
}

COUNTRY_TITLE_VALUES = {
    "usa",
    "us",
    "u.s.",
    "u.s.a.",
    "korea",
    "south korea",
    "republic of korea",
    "한국",
    "대한민국",
    "japan",
    "일본",
    "china",
    "중국",
    "germany",
    "독일",
    "europe",
    "eu",
    "pct",
    "국제",
    "taiwan",
    "대만",
    "canada",
    "캐나다",
    "france",
    "프랑스",
    "uk",
    "united kingdom",
    "영국",
    "미국",
    "ep",
    "wipo",
    "-",
}

PATENT_COUNTRY_PATTERN = (
    r"USA|U\.?S\.?A\.?|US|Korea|South Korea|Republic of Korea|한국|대한민국|"
    r"Japan|일본|China|중국|Germany|독일|Europe|EU|PCT|국제|Taiwan|대만|"
    r"Canada|캐나다|France|프랑스|UK|United Kingdom|영국|미국|EP|WIPO|-"
)


def canonical_output_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", clean_text(value)).casefold()
    text = re.sub(r"https?://\S+", " ", text)
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)


def normalized_raw_text(value: str) -> str:
    return unicodedata.normalize("NFKC", clean_text(value)).casefold()


def normalize_output_type(value: str) -> str:
    output_type = clean_text(value).casefold()
    return output_type if output_type in OUTPUT_TYPE_PRECEDENCE else "publication"


def normalize_output_year(value: str, raw_text: str = "") -> str:
    current_year = datetime.now().year
    match = re.search(r"\b(19\d{2}|20\d{2})\b", clean_text(value))
    if match and 1900 <= int(match.group(1)) <= current_year:
        return match.group(1)

    raw = clean_text(raw_text)
    trailing = re.findall(r"\((19\d{2}|20\d{2})\)\s*$", raw)
    if trailing and 1900 <= int(trailing[-1]) <= current_year:
        return trailing[-1]
    years = [
        year
        for year in re.findall(r"\b(19\d{2}|20\d{2})\b", raw)
        if 1900 <= int(year) <= current_year
    ]
    return years[-1] if years else ""


def output_title_is_invalid(title: str, professor_name: str = "") -> bool:
    text = clean_text(title).strip(" .,:;|-/")
    if len(text) < 2 or re.fullmatch(r"[\W_]+", text):
        return True
    if text.casefold() in COUNTRY_TITLE_VALUES:
        return True
    if professor_name and canonical_output_text(text) == canonical_output_text(professor_name):
        return True
    parts = [clean_text(part) for part in text.split(",") if clean_text(part)]
    if len(parts) >= 2 and len(parts) <= 8 and all(re.fullmatch(r"[가-힣]{2,4}", part) for part in parts):
        return True
    return False


def looks_like_person_segment(value: str) -> bool:
    text = clean_text(value).strip(" .,-")
    title_terms = (
        "방법", "장치", "시스템", "조성물", "제조", "용도", "센서", "소자",
        "전지", "물질", "재료", "분석", "제어", "영상", "이미지", "데이터",
        "모델", "프로그램", "매체", "공정", "구조", "광흡수제", "전해질",
        "메타렌즈", "보안코드", "피펫", "큐벳", "장갑", "비행복", "방염복",
        "소재", "기판", "탄소", "전극", "조직", "단백질", "화합물", "촉매",
        "필터", "통신", "신호", "회로", "안테나", "디스플레이", "입자",
        "질환", "치료", "진단", "예방", "발광", "전달", "검출", "생성",
        "균주", "다당체", "세포", "바이오센서", "음악", "나노구조체",
    )
    grammatical_title_signal = re.search(
        r"(?:을|를|은|는|의|에|로|으로|와|과)$|(?:하는|되는|가지는|포함하는|이용한|위한)$",
        text,
    )
    # Five- or six-syllable transliterated names such as 트란마이란,
    # 가미마샤마 and 비르마라비 occur in the patent export. Do not confuse
    # them with compact Korean patent titles containing a technical noun.
    if re.fullmatch(r"[가-힣]{2,8}", text):
        return not any(term in text for term in title_terms) and not grammatical_title_signal
    # Legacy researcher exports also contain transliterated foreign inventor
    # names written as multiple Hangul words.
    if re.fullmatch(r"[가-힣]{1,10}(?:\s+[가-힣]{1,10}){1,3}", text):
        if not any(term in text for term in title_terms) and not grammatical_title_signal:
            return True
    if re.fullmatch(r"[A-Za-z0-9_-]{6,14}", text) and any(ch.isdigit() for ch in text):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z.'’\-]*(?:\s+[A-Za-z][A-Za-z.'’\-]*){0,3}", text):
        words = re.findall(r"[A-Za-z][A-Za-z.'’\-]*", text)
        title_terms = {
            "method", "methods", "system", "systems", "device", "devices", "composition",
            "compositions", "apparatus", "protein", "proteins", "molecule", "molecules",
            "therapy", "treatment", "vaccine", "measuring", "fabrication", "bioadhesive",
        }
        if any(word.casefold() in title_terms for word in words):
            return False
        return bool(words) and all(word[0].isupper() or word.isupper() for word in words)
    return False


def parse_patent_raw_text(raw_text: str) -> dict[str, str]:
    """Parse patent rows from the right-hand country/identifier boundary.

    POSTECH patent entries contain comma-separated inventors, a title, country,
    and application number. The first crawler split US application numbers at
    their internal comma, producing titles such as "USA". Parsing from the
    country marker avoids that structural error.
    """
    raw = clean_text(raw_text)
    match = re.match(
        rf"^(?P<head>.*),\s*(?P<country>{PATENT_COUNTRY_PATTERN})\s*,\s*(?P<identifier>.+?)\s*$",
        raw,
        re.I,
    )
    if not match:
        return {}

    head = clean_text(match.group("head")).strip(" ,")
    parts = [clean_text(part) for part in head.split(",")]
    first_title = 0
    while first_title < len(parts) and (
        not parts[first_title]
        or parts[first_title] == "-"
        or looks_like_person_segment(parts[first_title])
    ):
        first_title += 1
    if first_title >= len(parts):
        # Very short Korean patent titles (for example "큐벳") are
        # indistinguishable from a person name in isolation. The final segment
        # before the country marker is nevertheless the title by source schema.
        first_title = max(0, len(parts) - 1)

    authors = ", ".join(part for part in parts[:first_title] if part and part != "-")
    title = ", ".join(part for part in parts[first_title:] if part)
    identifier = clean_text(match.group("identifier"))
    identifier = re.sub(r"\s*\((?:19|20)\d{2}\)\s*$", "", identifier).strip()
    if output_title_is_invalid(title):
        return {}
    return {
        "title": title,
        "authors_or_recipients": authors,
        "venue_or_organization": "" if clean_text(match.group("country")) == "-" else clean_text(match.group("country")),
        "identifier": identifier,
    }



def patent_identifier_year(identifier: str) -> str:
    """Return a filing year only when the identifier format encodes it explicitly."""
    text = clean_text(identifier)
    current_year = datetime.now().year
    patterns = (
        r"^(?:10-)(?P<year>19\d{2}|20\d{2})-",
        r"^PCT/KR(?P<year>19\d{2}|20\d{2})/",
        r"^(?P<year>19\d{2}|20\d{2})-\d{4,}",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match and 1900 <= int(match.group("year")) <= current_year + 1:
            return match.group("year")
    return ""


def comma_prefix_is_people(prefix: str) -> bool:
    parts = [clean_text(part) for part in prefix.split(",") if clean_text(part)]
    return bool(parts) and all(looks_like_person_segment(part) for part in parts)


def parsed_patent_is_better(current_title: str, parsed_title: str) -> bool:
    current = clean_text(current_title)
    parsed = clean_text(parsed_title)
    if not parsed:
        return False
    if output_title_is_invalid(current):
        return True
    current_key = canonical_output_text(current)
    parsed_key = canonical_output_text(parsed)
    if not current_key or current_key == parsed_key:
        return False
    # The old CSV often stored only the final comma-delimited title fragment
    # and moved the preceding fragments into the inventor column.
    if len(parsed) > len(current) and current_key in parsed_key:
        first_segment = clean_text(parsed.split(",", 1)[0])
        return not looks_like_person_segment(first_segment)
    # The inverse error stores one or more inventor names at the beginning of
    # the title. Remove them only when every removed comma segment is person-like.
    if len(current) > len(parsed) and current_key.endswith(parsed_key):
        suffix_index = current.casefold().rfind(parsed.casefold())
        if suffix_index > 0:
            return comma_prefix_is_people(current[:suffix_index].strip(" ,"))
    return False


def output_row_richness(row: dict[str, str]) -> tuple[int, int, int, str]:
    populated = sum(
        bool(clean_text(row.get(field_name, "")))
        for field_name in (
            "title",
            "year",
            "venue_or_organization",
            "authors_or_recipients",
            "identifier",
            "url",
        )
    )
    return (
        populated,
        len(clean_text(row.get("authors_or_recipients", ""))),
        len(clean_text(row.get("title", ""))),
        clean_text(row.get("crawled_at", "")),
    )


def normalize_output_row(
    row: dict[str, str],
    professor_by_lab_id: dict[str, str],
) -> tuple[dict[str, str], bool]:
    normalized = {field_name: clean_text(row.get(field_name, "")) for field_name in OUTPUT_FIELDS}
    normalized["output_type"] = normalize_output_type(normalized.get("output_type", ""))
    normalized["year"] = normalize_output_year(normalized.get("year", ""), normalized.get("raw_text", ""))
    normalized["url"] = normalize_url(normalized.get("url", ""))
    normalized["source_url"] = normalize_url(normalized.get("source_url", ""))
    professor_name = professor_by_lab_id.get(normalized.get("lab_id", ""), "")

    patent_reparsed = False
    if normalized["output_type"] == "patent":
        parsed = parse_patent_raw_text(normalized.get("raw_text", ""))
        if parsed:
            current_title = normalized.get("title", "")
            if parsed_patent_is_better(current_title, parsed.get("title", "")):
                normalized.update(parsed)
                patent_reparsed = True
            else:
                # Country, identifier, and inventor fields are structurally
                # recoverable even when the existing title is already better.
                for field_name in ("venue_or_organization", "identifier"):
                    if clean_text(parsed.get(field_name, "")) and not clean_text(normalized.get(field_name, "")):
                        normalized[field_name] = parsed[field_name]
                if clean_text(parsed.get("authors_or_recipients", "")) and not clean_text(normalized.get("authors_or_recipients", "")):
                    normalized["authors_or_recipients"] = parsed["authors_or_recipients"]
        encoded_year = patent_identifier_year(normalized.get("identifier", ""))
        if encoded_year and encoded_year != clean_text(normalized.get("year", "")):
            normalized["year"] = encoded_year
            patent_reparsed = True

    return normalized, patent_reparsed


def choose_best_output_row(group: list[dict[str, str]]) -> dict[str, str]:
    candidates = group
    if group and group[0].get("output_type") == "patent":
        title_counts = Counter(
            canonical_output_text(row.get("title", ""))
            for row in group
            if canonical_output_text(row.get("title", ""))
        )
        if title_counts:
            highest_frequency = title_counts.most_common(1)[0][1]
            candidates = [
                row
                for row in group
                if title_counts[canonical_output_text(row.get("title", ""))] == highest_frequency
            ]
    return max(candidates, key=output_row_richness)


def output_identity_key(row: dict[str, str]) -> tuple[str, ...]:
    """Canonical identity used by both deduplication and post-run auditing."""
    lab_id = clean_text(row.get("lab_id", ""))
    output_type = normalize_output_type(row.get("output_type", ""))
    title_key = canonical_output_text(row.get("title", ""))
    year = clean_text(row.get("year", ""))
    if output_type == "patent":
        identifier_key = canonical_output_text(row.get("identifier", ""))
        if len(identifier_key) >= 5:
            return (lab_id, output_type, "identifier", identifier_key)
        return (lab_id, output_type, "title", title_key, year)
    if year:
        return (lab_id, output_type, "title_year", title_key, year)
    return (
        lab_id,
        output_type,
        "title_venue",
        title_key,
        canonical_output_text(row.get("venue_or_organization", "")),
    )


def clean_research_outputs_rows(
    rows: list[dict[str, str]],
    labs_by_id: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    professor_by_lab_id = {
        lab_id: clean_text(row.get("professor_name", ""))
        for lab_id, row in labs_by_id.items()
    }
    normalized_rows: list[dict[str, str]] = []
    patent_reparsed = 0
    for row in rows:
        normalized, reparsed = normalize_output_row(row, professor_by_lab_id)
        normalized_rows.append(normalized)
        patent_reparsed += int(reparsed)

    # First remove exact source duplicates. Type precedence is essential because
    # every patent/book row in the current source was also parsed as publication.
    exact_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in normalized_rows:
        raw_key = normalized_raw_text(row.get("raw_text", ""))
        key = (
            clean_text(row.get("lab_id", "")),
            raw_key or f"__OUTPUT_ID__{clean_text(row.get('output_id', ''))}",
        )
        exact_groups[key].append(row)

    exact_deduped: list[dict[str, str]] = []
    for group in exact_groups.values():
        exact_deduped.append(
            max(
                group,
                key=lambda row: (
                    OUTPUT_TYPE_PRECEDENCE.get(row.get("output_type", ""), 0),
                    output_row_richness(row),
                ),
            )
        )
    exact_removed = len(normalized_rows) - len(exact_deduped)

    valid_rows: list[dict[str, str]] = []
    invalid_title_counts: Counter[str] = Counter()
    for row in exact_deduped:
        professor_name = professor_by_lab_id.get(row.get("lab_id", ""), "")
        if output_title_is_invalid(row.get("title", ""), professor_name):
            invalid_title_counts[row.get("output_type", "publication")] += 1
            continue
        valid_rows.append(row)

    # Then collapse semantic duplicates conservatively within the same lab/type.
    identity_groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in valid_rows:
        identity_groups[output_identity_key(row)].append(row)

    cleaned: list[dict[str, str]] = []
    for identity_key, group in identity_groups.items():
        row = dict(choose_best_output_row(group))
        row["output_id"] = stable_id("OUT", *identity_key, length=16)
        cleaned.append(row)

    type_sort_order = {"publication": 0, "patent": 1, "book": 2, "presentation": 3}
    cleaned.sort(
        key=lambda row: (
            clean_text(row.get("lab_id", "")),
            type_sort_order.get(row.get("output_type", ""), 9),
            -(int(row["year"]) if clean_text(row.get("year", "")).isdigit() else -1),
            canonical_output_text(row.get("title", "")),
        )
    )

    report: dict[str, object] = {
        "input_rows": len(rows),
        "patents_reparsed": patent_reparsed,
        "exact_source_duplicates_removed": exact_removed,
        "invalid_titles_dropped": dict(invalid_title_counts),
        "semantic_duplicates_removed": len(valid_rows) - len(cleaned),
        "clean_rows": len(cleaned),
        "type_counts": dict(Counter(row.get("output_type", "") for row in cleaned)),
        "missing_year_rows": sum(not clean_text(row.get("year", "")) for row in cleaned),
    }
    return cleaned, report


def build_recent_outputs(cleaned_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_lab: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in cleaned_rows:
        by_lab[clean_text(row.get("lab_id", ""))].append(row)

    recent_rows: list[dict[str, str]] = []
    for lab_id, rows in by_lab.items():
        ordered = sorted(
            rows,
            key=lambda row: (
                int(row["year"]) if clean_text(row.get("year", "")).isdigit() else -1,
                clean_text(row.get("crawled_at", "")),
                canonical_output_text(row.get("title", "")),
            ),
            reverse=True,
        )
        selected = (
            [row for row in ordered if row.get("output_type") == "publication"][:5]
            + [row for row in ordered if row.get("output_type") == "patent"][:3]
            + [row for row in ordered if row.get("output_type") in {"book", "presentation"}][:3]
        )
        for display_order, row in enumerate(selected, start=1):
            recent_rows.append(
                {
                    "output_id": row.get("output_id", ""),
                    "lab_id": lab_id,
                    "output_type": row.get("output_type", ""),
                    "title": row.get("title", ""),
                    "year": row.get("year", ""),
                    "venue": row.get("venue_or_organization", ""),
                    "authors": row.get("authors_or_recipients", ""),
                    "identifier": row.get("identifier", ""),
                    "url": row.get("url", ""),
                    "source_url": row.get("source_url", ""),
                    "display_order": str(display_order),
                }
            )
    recent_rows.sort(key=lambda row: (row["lab_id"], int(row["display_order"])))
    return recent_rows


def recompute_lab_output_counts(
    labs_by_id: dict[str, dict[str, str]],
    cleaned_rows: list[dict[str, str]],
) -> int:
    counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in cleaned_rows:
        counts[clean_text(row.get("lab_id", ""))][row.get("output_type", "")] += 1
    changed = 0
    for lab_id, lab in labs_by_id.items():
        publication_count = str(counts[lab_id]["publication"])
        patent_count = str(counts[lab_id]["patent"])
        if clean_text(lab.get("publication_count", "")) != publication_count:
            lab["publication_count"] = publication_count
            changed += 1
        if clean_text(lab.get("patent_count", "")) != patent_count:
            lab["patent_count"] = patent_count
            changed += 1
    return changed


def run_research_output_cleaner(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir).expanduser().resolve()
    outputs_path = data_dir / "research_outputs.csv"
    labs_path = data_dir / "labs.csv"
    clean_path = data_dir / "research_outputs_clean.csv"
    recent_path = data_dir / "recent_outputs.csv"

    output_rows, _ = read_csv_rows(outputs_path)
    lab_rows, lab_fields = read_csv_rows(labs_path)
    labs_by_id = {
        clean_text(row.get("lab_id", "")): dict(row)
        for row in lab_rows
        if clean_text(row.get("lab_id", ""))
    }
    cleaned_rows, report = clean_research_outputs_rows(output_rows, labs_by_id)
    recent_rows = build_recent_outputs(cleaned_rows)
    changed_count_fields = recompute_lab_output_counts(labs_by_id, cleaned_rows)

    if args.dry_run:
        print(json.dumps({**report, "recent_rows": len(recent_rows), "lab_count_fields_changed": changed_count_fields}, ensure_ascii=False, indent=2))
        print("DRY RUN이므로 파일을 기록하지 않았습니다.")
        return

    run_slug = timestamp_slug()
    backup_file(labs_path, data_dir / "backups", run_slug)
    atomic_write_csv(clean_path, cleaned_rows, OUTPUT_FIELDS)
    atomic_write_csv(recent_path, recent_rows, RECENT_OUTPUT_FIELDS)
    atomic_write_csv(
        labs_path,
        sorted(labs_by_id.values(), key=lambda row: (row.get("department_name", ""), row.get("professor_name", ""))),
        lab_fields,
    )
    report_path = data_dir / "research_outputs_clean_summary.json"
    report_payload = {
        **report,
        "recent_rows": len(recent_rows),
        "lab_count_fields_changed": changed_count_fields,
        "raw_source_modified": False,
        "enricher_version": ENRICHER_VERSION,
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 100)
    print("RESEARCH OUTPUT CLEANING COMPLETE")
    print("=" * 100)
    print(json.dumps(report_payload, ensure_ascii=False, indent=2))
    print(f"원본 유지 : {outputs_path}")
    print(f"정제 저장 : {clean_path}")
    print(f"최근 저장 : {recent_path}")
    print(f"집계 갱신 : {labs_path}")


def count_affiliations(labs: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in labs:
        for affiliation in split_multi(row.get("affiliated_programs", "")):
            counts[affiliation] += 1
    return counts


def build_data_audit_report(
    departments: list[dict[str, str]],
    labs: list[dict[str, str]],
    outputs: list[dict[str, str]],
    overrides: Optional[dict] = None,
) -> dict[str, object]:
    labs_by_id = {
        clean_text(row.get("lab_id", "")): row
        for row in labs
        if clean_text(row.get("lab_id", ""))
    }
    professor_by_lab = {
        lab_id: clean_text(row.get("professor_name", ""))
        for lab_id, row in labs_by_id.items()
    }

    field_counts = {
        field_name: sum(bool(clean_text(row.get(field_name, ""))) for row in labs)
        for field_name in (
            "professor_name",
            "email",
            "phone",
            "location",
            "lab_url",
            "profile_image_url",
            "primary_field",
            "research_summary",
            "keywords",
        )
    }
    field_counts["actual_lab_name"] = sum(lab_name_is_actual(row) for row in labs)
    field_counts["trusted_lab_url"] = sum(
        bool(clean_text(row.get("lab_url", "")))
        and clean_text(row.get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES
        for row in labs
    )

    duplicate_name_groups: list[dict[str, object]] = []
    names: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labs:
        normalized_name = normalize_name(row.get("professor_name", ""))
        if normalized_name:
            names[normalized_name].append(row)
    for group in names.values():
        emails = {normalize_email(row.get("email", "")) for row in group if normalize_email(row.get("email", ""))}
        if len(emails) < 2:
            continue
        shared_fields: dict[str, list[str]] = {}
        for field_name in (
            "lab_name_kor",
            "phone",
            "location",
            "lab_url",
            "primary_field",
            "research_summary",
        ):
            values = Counter(
                clean_text(row.get(field_name, "")).casefold()
                for row in group
                if clean_text(row.get(field_name, ""))
                and not (field_name == "lab_name_kor" and looks_placeholder_lab_name(row.get(field_name, "")))
            )
            duplicates = [value for value, count in values.items() if count >= 2]
            if duplicates:
                shared_fields[field_name] = duplicates
        duplicate_name_groups.append(
            {
                "professor_name": clean_text(group[0].get("professor_name", "")),
                "emails": sorted(emails),
                "shared_fields": shared_fields,
            }
        )

    repeated_lab_names = []
    invalid_repeated_generic_lab_names = []
    lab_name_rows: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labs:
        name = clean_text(row.get("lab_name_kor", ""))
        if name and not looks_placeholder_lab_name(name):
            lab_name_rows[name.casefold()].append(row)
    for name, group in lab_name_rows.items():
        emails = {normalize_email(row.get("email", "")) for row in group if normalize_email(row.get("email", ""))}
        if len(emails) >= 3:
            item = {
                "lab_name": clean_text(group[0].get("lab_name_kor", "")),
                "professor_count": len(emails),
                "departments": sorted({clean_text(row.get("department_name", "")) for row in group}),
                "urls": sorted({normalize_url(row.get("lab_url", "")) for row in group if normalize_url(row.get("lab_url", ""))}),
            }
            repeated_lab_names.append(item)
            trusted_group = [row for row in group if clean_text(row.get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES]
            all_distinct_official = len(item["urls"]) == len(group) and all(
                is_official_postech_source(lab_url_provenance(row).get("source_url", ""))
                and "exact_email" in clean_text(lab_url_provenance(row).get("method", ""))
                for row in group
            )
            shared_verified = len(trusted_group) == len(group) and shared_lab_group_is_verified(trusted_group)
            if not (all_distinct_official or shared_verified):
                invalid_repeated_generic_lab_names.append(item)

    exact_raw_groups: defaultdict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    invalid_titles: Counter[str] = Counter()
    for row in outputs:
        raw_key = normalized_raw_text(row.get("raw_text", ""))
        if raw_key:
            exact_raw_groups[(clean_text(row.get("lab_id", "")), raw_key)].append(row)
        output_type = normalize_output_type(row.get("output_type", ""))
        if output_title_is_invalid(
            row.get("title", ""), professor_by_lab.get(clean_text(row.get("lab_id", "")), "")
        ):
            invalid_titles[output_type] += 1
    duplicate_raw_groups = [group for group in exact_raw_groups.values() if len(group) >= 2]
    mixed_type_duplicate_groups = sum(
        len({normalize_output_type(row.get("output_type", "")) for row in group}) >= 2
        for group in duplicate_raw_groups
    )

    raw_output_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in outputs:
        raw_output_counts[clean_text(row.get("lab_id", ""))][normalize_output_type(row.get("output_type", ""))] += 1
    count_mismatch_labs = 0
    for lab_id, lab in labs_by_id.items():
        if clean_text(lab.get("publication_count", "")) != str(raw_output_counts[lab_id]["publication"]):
            count_mismatch_labs += 1
            continue
        if clean_text(lab.get("patent_count", "")) != str(raw_output_counts[lab_id]["patent"]):
            count_mismatch_labs += 1

    affiliation_counts = count_affiliations(labs)
    affiliation_guard_violations = affiliation_evidence_violations(
        labs, departments, overrides or effective_builtin_overrides()
    )

    department_by_id = {
        clean_text(row.get("department_id", "")): row
        for row in departments if clean_text(row.get("department_id", ""))
    }
    foreign_department_page_rows = []
    for row in labs:
        primary_id = clean_text(row.get("primary_department_id", "") or row.get("department_id", ""))
        department = department_by_id.get(primary_id)
        page_url = normalize_url(row.get("department_page_url", ""))
        if not department or not page_url:
            continue
        own_hosts = authoritative_department_hosts(
            department, resolve_department_override(BUILTIN_SITE_OVERRIDES, department)
        )
        page_host = hostname(page_url).removeprefix("www.")
        if page_host and page_host not in own_hosts:
            provenance = parse_json_dict(row.get("field_provenance", ""))
            exact_cross_listed = any(
                isinstance(evidence, dict)
                and canonical_url_key(evidence.get("source_url", "")) == canonical_url_key(page_url)
                and is_official_postech_source(evidence.get("source_url", ""))
                and "exact_email" in clean_text(evidence.get("method", ""))
                for evidence in provenance.values()
            )
            if exact_cross_listed:
                continue
            foreign_department_page_rows.append({
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "primary_department": clean_text(row.get("department_name", "")),
                "department_page_url": page_url,
            })

    department_url_keys = department_reference_url_keys(departments)
    known_department_page_rows = []
    trusted_without_provenance = []
    trusted_incomplete_provenance = []
    reconstructed_provenance_rows = []
    suspicious_lab_name_rows = []
    trusted_url_groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labs:
        url = normalize_url(row.get("lab_url", ""))
        status = clean_text(row.get("lab_url_status", ""))
        if url and canonical_url_key(url) in department_url_keys:
            known_department_page_rows.append({
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "lab_url": url, "lab_url_status": status,
            })
        if url and status in TRUSTED_LAB_URL_STATUSES:
            provenance_item = {
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "lab_url": url,
            }
            if not lab_url_provenance(row):
                trusted_without_provenance.append(provenance_item)
            if not lab_url_provenance_complete(row):
                trusted_incomplete_provenance.append(provenance_item)
            elif clean_text(lab_url_provenance(row).get("source_kind", "")) == "legacy_provenance_reconstruction":
                reconstructed_provenance_rows.append(provenance_item)
        if url and status in TRUSTED_LAB_URL_STATUSES:
            trusted_url_groups[canonical_url_key(url)].append(row)
        professor = clean_text(row.get("professor_name", ""))
        raw_kor = clean_text(row.get("lab_name_kor", ""))
        raw_eng = clean_text(row.get("lab_name_eng", ""))
        clean_kor = clean_lab_name(raw_kor, professor)
        clean_eng = clean_lab_name(raw_eng, professor)
        suspicious = (raw_kor and not looks_placeholder_lab_name(raw_kor) and not clean_kor) or (raw_eng and not clean_eng)
        if suspicious:
            suspicious_lab_name_rows.append({
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": professor,
                "lab_name_kor": raw_kor, "lab_name_eng": raw_eng,
            })
    duplicate_trusted_url_groups = []
    for key, group in trusted_url_groups.items():
        if len(group) < 2:
            continue
        duplicate_trusted_url_groups.append({
            "lab_url": normalize_url(group[0].get("lab_url", "")),
            "professor_count": len(group),
            "professors": [clean_text(row.get("professor_name", "")) for row in group],
            "departments": sorted({clean_text(row.get("department_name", "")) for row in group}),
            "methods": [clean_text(lab_url_provenance(row).get("method", "")) for row in group],
            "shared_lab_verified": shared_lab_group_is_verified(group),
        })
    lab_link_audit = {
        "any_url": sum(bool(normalize_url(row.get("lab_url", ""))) for row in labs),
        "trusted_url": sum(bool(normalize_url(row.get("lab_url", ""))) and clean_text(row.get("lab_url_status", "")) in TRUSTED_LAB_URL_STATUSES for row in labs),
        "candidate_url": sum(clean_text(row.get("lab_url_status", "")) == "candidate_card" for row in labs),
        "missing_url": sum(not normalize_url(row.get("lab_url", "")) for row in labs),
        "known_department_page_rows": known_department_page_rows,
        "known_department_page_count": len(known_department_page_rows),
        "trusted_without_field_provenance": trusted_without_provenance,
        "trusted_without_field_provenance_count": len(trusted_without_provenance),
        "trusted_with_incomplete_field_provenance": trusted_incomplete_provenance,
        "trusted_with_incomplete_field_provenance_count": len(trusted_incomplete_provenance),
        "reconstructed_field_provenance_rows": reconstructed_provenance_rows,
        "reconstructed_field_provenance_count": len(reconstructed_provenance_rows),
        "duplicate_trusted_url_groups": duplicate_trusted_url_groups,
        "unverified_shared_url_group_count": sum(not item["shared_lab_verified"] for item in duplicate_trusted_url_groups),
        "suspicious_lab_name_rows": suspicious_lab_name_rows,
        "suspicious_lab_name_count": len(suspicious_lab_name_rows),
    }
    lab_link_audit["valid"] = not any((
        lab_link_audit["known_department_page_count"],
        lab_link_audit["suspicious_lab_name_count"],
        lab_link_audit["trusted_with_incomplete_field_provenance_count"],
        lab_link_audit["unverified_shared_url_group_count"],
    ))

    suspicious_location_rows = []
    suspicious_summary_rows = []
    for row in labs:
        raw_location = clean_text(row.get("location", ""))
        cleaned_location = clean_location_value(raw_location)
        if raw_location and cleaned_location != raw_location:
            suspicious_location_rows.append({
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "location": raw_location,
                "cleaned_value": cleaned_location,
            })
        raw_summary = clean_text(row.get("research_summary", ""))
        cleaned_summary = clean_summary_value(raw_summary)
        if raw_summary and cleaned_summary != raw_summary:
            suspicious_summary_rows.append({
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "research_summary": raw_summary,
                "cleaned_value": cleaned_summary,
            })
    content_quality = {
        "suspicious_location_rows": suspicious_location_rows,
        "suspicious_location_count": len(suspicious_location_rows),
        "suspicious_summary_rows": suspicious_summary_rows,
        "suspicious_summary_count": len(suspicious_summary_rows),
    }
    content_quality["valid"] = not any((
        content_quality["suspicious_location_count"],
        content_quality["suspicious_summary_count"],
    ))

    return {
        "enricher_version": ENRICHER_VERSION,
        "departments_total": len(departments),
        "labs_total": len(labs),
        "outputs_total": len(outputs),
        "unique_lab_ids": len({clean_text(row.get("lab_id", "")) for row in labs if clean_text(row.get("lab_id", ""))}),
        "unique_emails": len({normalize_email(row.get("email", "")) for row in labs if normalize_email(row.get("email", ""))}),
        "field_counts": field_counts,
        "quality_counts": dict(Counter(clean_text(row.get("data_quality_status", "")) or "unknown" for row in labs)),
        "enrichment_status_counts": dict(Counter(clean_text(row.get("enrichment_status", "")) or "unknown" for row in labs)),
        "lab_url_status_counts": dict(Counter(clean_text(row.get("lab_url_status", "")) or "unknown" for row in labs)),
        "lab_links": lab_link_audit,
        "content_quality": content_quality,
        "affiliation_counts": dict(affiliation_counts.most_common()),
        "affiliation_guard_violations": affiliation_guard_violations,
        "affiliation_evidence_violation_count": len(affiliation_guard_violations),
        "foreign_department_page_rows": foreign_department_page_rows,
        "foreign_department_page_count": len(foreign_department_page_rows),
        "data_state_counts": dict(Counter(clean_text(row.get("data_state", "")) or "unknown" for row in labs)),
        "quarantined_data_state_count": sum(clean_text(row.get("data_state", "")) in QUARANTINED_DATA_STATES for row in labs),
        "duplicate_name_groups": duplicate_name_groups,
        "repeated_lab_names": repeated_lab_names,
        "invalid_repeated_generic_lab_names": invalid_repeated_generic_lab_names,
        "invalid_repeated_generic_lab_name_count": len(invalid_repeated_generic_lab_names),
        "research_outputs": {
            "type_counts": dict(Counter(normalize_output_type(row.get("output_type", "")) for row in outputs)),
            "exact_duplicate_groups": len(duplicate_raw_groups),
            "exact_duplicate_rows_excess": sum(len(group) - 1 for group in duplicate_raw_groups),
            "mixed_type_duplicate_groups": mixed_type_duplicate_groups,
            "invalid_title_counts": dict(invalid_titles),
            "labs_with_raw_count_mismatch": count_mismatch_labs,
        },
    }


def validate_clean_output_artifacts(
    labs: list[dict[str, str]],
    outputs: list[dict[str, str]],
    recent: list[dict[str, str]],
) -> dict[str, object]:
    output_ids = [clean_text(row.get("output_id", "")) for row in outputs]
    identity_counts = Counter(output_identity_key(row) for row in outputs)
    current_year = datetime.now().year
    known_lab_ids = {clean_text(row.get("lab_id", "")) for row in labs}
    output_id_set = set(output_ids)

    recent_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    display_orders: defaultdict[str, list[int]] = defaultdict(list)
    recent_unknown_output_ids = 0
    for row in recent:
        lab_id = clean_text(row.get("lab_id", ""))
        output_type = normalize_output_type(row.get("output_type", ""))
        bucket = "other" if output_type in {"book", "presentation"} else output_type
        recent_counts[lab_id][bucket] += 1
        if clean_text(row.get("output_id", "")) not in output_id_set:
            recent_unknown_output_ids += 1
        order = clean_text(row.get("display_order", ""))
        if order.isdigit():
            display_orders[lab_id].append(int(order))

    recent_limit_violations = []
    for lab_id, counts in recent_counts.items():
        if counts["publication"] > 5 or counts["patent"] > 3 or counts["other"] > 3:
            recent_limit_violations.append({"lab_id": lab_id, **dict(counts)})

    non_contiguous_display_orders = sum(
        sorted(values) != list(range(1, len(values) + 1))
        for values in display_orders.values()
    )

    output_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in outputs:
        output_counts[clean_text(row.get("lab_id", ""))][normalize_output_type(row.get("output_type", ""))] += 1
    lab_count_mismatches = 0
    for lab in labs:
        lab_id = clean_text(lab.get("lab_id", ""))
        if clean_text(lab.get("publication_count", "")) != str(output_counts[lab_id]["publication"]):
            lab_count_mismatches += 1
            continue
        if clean_text(lab.get("patent_count", "")) != str(output_counts[lab_id]["patent"]):
            lab_count_mismatches += 1

    report = {
        "rows": len(outputs),
        "type_counts": dict(Counter(normalize_output_type(row.get("output_type", "")) for row in outputs)),
        "duplicate_output_ids": len(output_ids) - len(set(output_ids)),
        "semantic_duplicate_keys": sum(count - 1 for count in identity_counts.values() if count > 1),
        "invalid_titles": sum(output_title_is_invalid(row.get("title", "")) for row in outputs),
        "future_years": sum(
            clean_text(row.get("year", "")).isdigit()
            and int(clean_text(row.get("year", ""))) > current_year
            for row in outputs
        ),
        "unknown_lab_ids": sum(clean_text(row.get("lab_id", "")) not in known_lab_ids for row in outputs),
        "recent_rows": len(recent),
        "recent_limit_violations": recent_limit_violations,
        "recent_unknown_output_ids": recent_unknown_output_ids,
        "non_contiguous_display_order_labs": non_contiguous_display_orders,
        "lab_count_mismatches": lab_count_mismatches,
    }
    report["valid"] = not any(
        (
            report["duplicate_output_ids"],
            report["semantic_duplicate_keys"],
            report["invalid_titles"],
            report["future_years"],
            report["unknown_lab_ids"],
            len(recent_limit_violations),
            report["recent_unknown_output_ids"],
            report["non_contiguous_display_order_labs"],
            report["lab_count_mismatches"],
        )
    )
    return report


def run_data_audit(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir).expanduser().resolve()
    departments, _ = read_csv_rows(data_dir / "departments.csv")
    labs, _ = read_csv_rows(data_dir / "labs.csv")
    outputs, _ = read_csv_rows(data_dir / "research_outputs.csv")
    overrides_path = Path(args.overrides).expanduser().resolve() if args.overrides else data_dir / "site_overrides.json"
    audit_overrides = load_overrides(overrides_path)
    report = build_data_audit_report(departments, labs, outputs, audit_overrides)
    clean_path = data_dir / "research_outputs_clean.csv"
    recent_path = data_dir / "recent_outputs.csv"
    if clean_path.exists() and recent_path.exists():
        clean_outputs, _ = read_csv_rows(clean_path)
        recent_outputs, _ = read_csv_rows(recent_path)
        clean_validation = validate_clean_output_artifacts(
            labs, clean_outputs, recent_outputs
        )
        report["clean_output_artifacts"] = clean_validation
        report["research_outputs"]["lab_count_basis"] = "research_outputs_clean.csv"
        report["research_outputs"]["labs_with_active_count_mismatch"] = clean_validation[
            "lab_count_mismatches"
        ]
    else:
        report["research_outputs"]["lab_count_basis"] = "research_outputs.csv"
        report["research_outputs"]["labs_with_active_count_mismatch"] = report[
            "research_outputs"
        ]["labs_with_raw_count_mismatch"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.dry_run:
        report_path = data_dir / "data_audit_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"감사 보고서: {report_path}")


def run_self_test() -> None:
    tests = 0

    # Shared-portal scope must reject sibling programs.
    override = BUILTIN_SITE_OVERRIDES["푸드테크융합전공"]
    assert url_matches_override_scope(
        "https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member",
        override,
    )
    assert not url_matches_override_scope(
        "https://gscst.postech.ac.kr/web/?depart=14&position=1&sub=professor&top=member",
        override,
    )
    tests += 1

    # Static faculty-count guesses are not used; evidence must be attached to
    # every secondary affiliation instead.
    evidence_row = {
        "lab_id": "L1", "department_name": "컴퓨터공학과",
        "affiliated_programs": "컴퓨터공학과;푸드테크융합전공",
        "affiliation_evidence": "",
    }
    assert len(affiliation_evidence_violations([evidence_row])) == 1
    record_affiliation_evidence(
        evidence_row, "푸드테크융합전공",
        "https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member",
        "email", False,
    )
    assert not affiliation_evidence_violations([evidence_row])
    tests += 1

    # A scoped globally-unique name is valid only when the exact successful
    # official page and the department's hard scope are both available.
    scoped_url = "https://gscst.postech.ac.kr:443/web/?top=member&sub=professor&depart=16&position=2"
    scoped_department = {
        "department_id": "D16",
        "department_name_kor": "푸드테크융합전공",
        "homepage_url": "",
        "faculty_page_urls": scoped_url,
    }
    scoped_row = {
        "lab_id": "L2", "department_name": "컴퓨터공학과",
        "professor_name": "전역고유이름", "email": "unique@postech.ac.kr",
        "affiliated_programs": "컴퓨터공학과;푸드테크융합전공",
        "affiliation_evidence": "",
    }
    record_affiliation_evidence(
        scoped_row, "푸드테크융합전공", scoped_url,
        "unique_name_scoped_faculty_page", False,
    )
    assert not affiliation_evidence_violations(
        [scoped_row], [scoped_department], effective_builtin_overrides()
    )
    bad_scoped_department = dict(scoped_department)
    bad_scoped_department["faculty_page_urls"] = (
        "https://gscst.postech.ac.kr/web/?depart=14&position=2&sub=professor&top=member"
    )
    assert len(affiliation_evidence_violations(
        [scoped_row], [bad_scoped_department], effective_builtin_overrides()
    )) == 1
    tests += 1

    # clean-only must preserve the same scoped-name evidence contract instead
    # of deleting affiliations that the authoritative commit accepted.
    scoped_clean_lab = {"L2": dict(scoped_row)}
    quarantine_unverified_affiliations(
        [dict(scoped_department)], scoped_clean_lab, effective_builtin_overrides()
    )
    assert "푸드테크융합전공" in split_multi(
        scoped_clean_lab["L2"]["affiliated_programs"]
    )
    assert not affiliation_evidence_violations(
        scoped_clean_lab.values(), [scoped_department], effective_builtin_overrides()
    )
    tests += 1

    # Official-list-shaped HTML must produce one exact-email match per card.
    official_like = PageResult(
        "https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member",
        """<html><body><ul>
        <li class='person'><h4>박주홍</h4><p>연구분야 IoT, Healthcare Architecture</p>
        <p>연락처 054-279-8875</p><p>이메일 juhpark@postech.ac.kr</p></li>
        <li class='person'><h4>홍길동</h4><p>연구분야 Other Field</p>
        <p>이메일 other@postech.ac.kr</p></li>
        </ul></body></html>""",
        "requests",
    )
    official_labs = {
        "L1": {"lab_id": "L1", "professor_name": "박주홍", "email": "juhpark@postech.ac.kr", "department_name": "컴퓨터공학과"},
        "L2": {"lab_id": "L2", "professor_name": "홍길동", "email": "other@postech.ac.kr", "department_name": "전자전기공학과"},
    }
    official_matches = build_page_matches(
        official_like,
        {"faculty_card_selectors": ["li.person"], "max_card_emails": 2, "max_card_identities": 2},
        official_labs,
        {"juhpark@postech.ac.kr": "L1", "other@postech.ac.kr": "L2"},
        {},
        {normalize_name("박주홍"), normalize_name("홍길동")},
    )
    assert {match.lab_id for match in official_matches} == {"L1", "L2"}
    first_match = next(match for match in official_matches if match.lab_id == "L1")
    first_update = extract_card_data(first_match.block, official_like.url, official_labs["L1"], {})
    assert "IoT" in first_update["primary_field"]
    assert first_update["phone"] == "054-279-8875"
    assert "other@postech.ac.kr" not in first_match.block.get_text(" ", strip=True)
    tests += 1

    # Name fallback must never use a derived affiliation.
    department = {"department_id": "D2", "department_name_kor": "프로그램B"}
    lab_rows = {
        "L1": {
            "lab_id": "L1",
            "department_id": "D1",
            "primary_department_id": "D1",
            "department_name": "학과A",
            "affiliated_programs": "학과A;프로그램B",
            "professor_name": "홍길동",
        }
    }
    assert not build_department_name_index(lab_rows, department, {normalize_name("홍길동"): "L1"})
    tests += 1

    # Secondary program pages may add affiliation but cannot overwrite fields.
    lab = {
        "lab_id": "L1",
        "professor_name": "홍길동",
        "department_name": "학과A",
        "affiliated_programs": "학과A",
        "lab_name_kor": "정상 연구실",
        "primary_field": "정상 분야",
        "lab_url": "",
        "lab_url_status": "unverified",
    }
    merged, changed = merge_lab_update(
        lab,
        {
            "_source_scope": "secondary",
            "_allow_secondary_field_enrichment": False,
            "lab_name_kor": "오염 연구실",
            "primary_field": "오염 분야",
        },
        "프로그램B",
    )
    assert merged["lab_name_kor"] == "정상 연구실"
    assert merged["primary_field"] == "정상 분야"
    assert "프로그램B" in split_multi(merged["affiliated_programs"])
    assert changed == ["affiliated_programs"]
    tests += 1

    # Homonymous copied values must be blanked before exact-email recrawl.
    departments = [
        {"department_id": "D1", "department_name_kor": "학과A", "homepage_url": "https://a.postech.ac.kr"},
        {"department_id": "D2", "department_name_kor": "학과B", "homepage_url": "https://b.postech.ac.kr"},
    ]
    homonyms = {
        "L1": {
            "lab_id": "L1", "department_id": "D1", "primary_department_id": "D1",
            "department_name": "학과A", "professor_name": "김동명", "email": "one@postech.ac.kr",
            "lab_name_kor": "Copied Lab", "primary_field": "Copied Field",
            "research_summary": "주요 연구 분야: Copied Field",
            "department_page_url": "https://b.postech.ac.kr/faculty", "lab_url": "https://wrong.example.com",
            "lab_url_status": "verified_homepage", "keywords": "Copied Field",
        },
        "L2": {
            "lab_id": "L2", "department_id": "D2", "primary_department_id": "D2",
            "department_name": "학과B", "professor_name": "김동명", "email": "two@postech.ac.kr",
            "lab_name_kor": "Copied Lab", "primary_field": "Copied Field",
            "research_summary": "주요 연구 분야: Copied Field",
            "department_page_url": "https://b.postech.ac.kr/faculty", "lab_url": "",
            "lab_url_status": "unverified", "keywords": "Copied Field",
        },
    }
    contamination = reset_stale_cross_identity_contamination(departments, homonyms, {})
    assert contamination["lab_name_kor"] == 2
    assert all(looks_placeholder_lab_name(row["lab_name_kor"]) for row in homonyms.values())
    assert not homonyms["L1"]["lab_url"]
    tests += 1

    # Exact raw duplicate must keep the patent row and repair a split US patent.
    labs_for_outputs = {"L1": {"lab_id": "L1", "professor_name": "이승용"}}
    raw = "이승용,손형석, 이미지 처리 방법 및 장치, USA, 15/441,145 (2017)"
    output_rows = [
        {
            "output_id": "A", "lab_id": "L1", "researcher_id": "R1", "output_type": "publication",
            "output_subtype": "journal", "title": "이승용", "year": "2017", "venue_or_organization": "손형석",
            "authors_or_recipients": "", "identifier": "", "raw_text": raw, "url": "", "source_url": "", "crawled_at": "",
        },
        {
            "output_id": "B", "lab_id": "L1", "researcher_id": "R1", "output_type": "patent",
            "output_subtype": "patent", "title": "USA", "year": "2017", "venue_or_organization": "15/441",
            "authors_or_recipients": "이승용,손형석, 이미지 처리 방법 및 장치", "identifier": "145",
            "raw_text": raw, "url": "", "source_url": "", "crawled_at": "",
        },
    ]
    cleaned, report = clean_research_outputs_rows(output_rows, labs_for_outputs)
    assert len(cleaned) == 1 and cleaned[0]["output_type"] == "patent"
    assert cleaned[0]["title"] == "이미지 처리 방법 및 장치"
    assert cleaned[0]["identifier"] == "15/441,145"
    assert report["exact_source_duplicates_removed"] == 1
    tests += 1

    # Recent-output limits: 5 publications, 3 patents, 3 book/presentation.
    synthetic: list[dict[str, str]] = []
    for output_type, count in (("publication", 7), ("patent", 5), ("presentation", 5)):
        for index in range(count):
            synthetic.append(
                {
                    "output_id": f"{output_type}-{index}", "lab_id": "L1", "output_type": output_type,
                    "title": f"Title {index}", "year": str(2020 + index), "venue_or_organization": "V",
                    "authors_or_recipients": "A", "identifier": "", "url": "", "source_url": "", "crawled_at": "",
                }
            )
    recent = build_recent_outputs(synthetic)
    assert Counter(row["output_type"] for row in recent) == Counter({"publication": 5, "patent": 3, "presentation": 3})
    tests += 1

    # Duplicate professor names require exact e-mail on a homepage.
    ambiguous_soup = BeautifulSoup(
        "<html><body><h1>김동명 Lab</h1><p>other@postech.ac.kr</p><p>Research laboratory</p></body></html>",
        "lxml",
    )
    score, email_exact, conflict = homepage_identity_score(
        ambiguous_soup,
        {
            "professor_name": "김동명",
            "email": "one@postech.ac.kr",
            "lab_name_kor": "김동명 Lab",
            "_name_is_ambiguous": True,
        },
    )
    assert not email_exact and conflict and score <= 7
    tests += 1

    # Full rebuild preserves all non-invalid link observations while rebuilding unrelated fields.
    rebuild_rows = {
        "A": {
            "lab_id": "A", "professor_name": "A교수", "lab_name_kor": "Trusted Lab",
            "lab_name_eng": "Trusted Lab", "lab_url": "https://trusted.example.com",
            "lab_url_status": "verified_homepage", "keyword_source": "lab_homepage",
            "primary_field": "Card field", "research_summary": "Homepage summary", "keywords": "Homepage keyword",
            "location": "Room 101", "department_page_url": "https://dept.example.com/faculty",
        },
        "B": {
            "lab_id": "B", "professor_name": "B교수", "lab_name_kor": "Wrong Card Lab",
            "lab_url": "https://candidate.example.com", "lab_url_status": "verified_card",
            "primary_field": "Wrong field", "research_summary": "Wrong summary", "keywords": "Wrong keyword",
            "keyword_source": "department_page", "location": "Room 202",
            "department_page_url": "https://dept.example.com/faculty",
        },
    }
    reset_report = clear_non_authoritative_enrichment_for_full_rebuild(rebuild_rows)
    assert rebuild_rows["A"]["lab_url"] == "https://trusted.example.com"
    assert rebuild_rows["A"]["lab_name_kor"] == "Trusted Lab"
    assert rebuild_rows["A"]["research_summary"] == "Homepage summary"
    assert rebuild_rows["A"]["primary_field"] == ""
    assert rebuild_rows["B"]["lab_url"] == "https://candidate.example.com"
    assert rebuild_rows["B"]["lab_url_status"] == "verified_card"
    assert rebuild_rows["B"]["lab_name_kor"] == "Wrong Card Lab"
    assert reset_report["department_page_url"] == 2
    tests += 1

    # Stable IDs remain unique when same title/no year appears at different venues.
    no_year_rows = []
    for index, venue in enumerate(("Venue A", "Venue B")):
        no_year_rows.append(
            {
                "output_id": str(index), "lab_id": "L1", "researcher_id": "R1",
                "output_type": "presentation", "output_subtype": "conference", "title": "Same title",
                "year": "", "venue_or_organization": venue, "authors_or_recipients": "A",
                "identifier": "", "raw_text": f"Same title, {venue}", "url": "", "source_url": "", "crawled_at": "",
            }
        )
    no_year_cleaned, _ = clean_research_outputs_rows(no_year_rows, labs_for_outputs)
    assert len(no_year_cleaned) == 2
    assert len({row["output_id"] for row in no_year_cleaned}) == 2
    tests += 1

    # Generated clean/recent artifacts must pass the same audit used in production.
    audit_labs = [{"lab_id": "L1", "publication_count": "0", "patent_count": "1"}]
    audit_recent = build_recent_outputs(cleaned)
    artifact_report = validate_clean_output_artifacts(audit_labs, cleaned, audit_recent)
    assert artifact_report["valid"]
    tests += 1


    # Default unscoped execution is authoritative; incremental mode is opt-in.
    assert authoritative_rebuild_requested(
        argparse.Namespace(clean_only=False, department=None, test_limit=None, incremental=False)
    )
    assert not authoritative_rebuild_requested(
        argparse.Namespace(clean_only=False, department=None, test_limit=None, incremental=True)
    )
    assert not authoritative_rebuild_requested(
        argparse.Namespace(clean_only=False, department="생명과학과", test_limit=None, incremental=False)
    )
    tests += 1

    # A department-card URL from another primary department is a quarantine
    # signal, while independently verified homepage content is preserved.
    fake_departments = [{
        "department_id": "D1", "department_name_kor": "생명과학과",
        "homepage_url": "https://life.postech.ac.kr/",
    }]
    foreign_rows = {
        "L1": {
            "lab_id": "L1", "department_id": "D1", "primary_department_id": "D1",
            "department_name": "생명과학과", "professor_name": "김민성",
            "lab_name_kor": "Wrong Math Lab", "phone": "054-279-0000",
            "location": "수리과학관 223호", "primary_field": "동역학계",
            "research_summary": "Wrong summary", "keywords": "동역학계",
            "lab_url": "https://wrong.example.com", "lab_url_status": "verified_card",
            "department_page_url": "https://math.postech.ac.kr/faculty",
        },
        "L2": {
            "lab_id": "L2", "department_id": "D1", "primary_department_id": "D1",
            "department_name": "생명과학과", "professor_name": "고아라",
            "lab_name_kor": "Trusted Homepage Lab", "research_summary": "Trusted homepage summary about research",
            "keywords": "Microbiome;Cancer", "keyword_source": "lab_homepage",
            "lab_url": "https://trusted.example.com", "lab_url_status": "verified_homepage",
            "department_page_url": "https://math.postech.ac.kr/faculty",
        },
    }
    foreign_report = reset_foreign_department_provenance(
        fake_departments, foreign_rows, BUILTIN_SITE_OVERRIDES
    )
    assert foreign_report["rows"] == 2
    assert looks_placeholder_lab_name(foreign_rows["L1"]["lab_name_kor"])
    assert not foreign_rows["L1"]["location"] and not foreign_rows["L1"]["lab_url"]
    assert foreign_rows["L2"]["lab_name_kor"] == "Trusted Homepage Lab"
    assert foreign_rows["L2"]["research_summary"] == "Trusted homepage summary about research"
    tests += 1

    # Clean-only quarantine retains only exact-email-evidenced secondary
    # affiliations and keeps their evidence record intact.
    evidence_lab = {
        "L1": {
            "lab_id": "L1", "department_name": "컴퓨터공학과",
            "affiliated_programs": "컴퓨터공학과;푸드테크융합전공;오염전공",
            "crawled_at": "2026-01-01T00:00:00+09:00",
            "affiliation_evidence": compact_json({
                "푸드테크융합전공": {
                    "source_url": "https://gscst.postech.ac.kr/web/?depart=16&position=2&sub=professor&top=member",
                    "method": "email", "primary": False,
                }
            }),
        }
    }
    quarantine_unverified_affiliations([], evidence_lab, effective_builtin_overrides())
    assert evidence_lab["L1"]["affiliated_programs"] == "컴퓨터공학과;푸드테크융합전공"
    assert "푸드테크융합전공" in parse_json_dict(evidence_lab["L1"]["affiliation_evidence"])
    assert not affiliation_evidence_violations(evidence_lab.values())
    tests += 1

    # Shared-portal category discovery follows only same-depart professor
    # categories even when general link traversal is disabled.
    seed_url = "https://gscst.postech.ac.kr/web/?depart=16&position=1&sub=professor&top=member"
    same_scope_url = "https://gscst.postech.ac.kr/web/?depart=16&position=2&sub=professor&top=member"
    sibling_url = "https://gscst.postech.ac.kr/web/?depart=14&position=2&sub=professor&top=member"
    class FakeClient:
        def fetch(self, url: str, force_browser: bool = False) -> PageResult:
            if normalize_url(url) == normalize_url(seed_url):
                return PageResult(url, f"<html><body><a href='{same_scope_url}'>겸임교수</a><a href='{sibling_url}'>국방</a></body></html>", "fake")
            return PageResult(url, "<html><body><p>faculty category</p></body></html>", "fake")
    fake_dir = Path(tempfile.mkdtemp(prefix="postech-selftest-"))
    try:
        fake_paths = RuntimePaths.from_args(fake_dir, None)
        discovered = discover_department_pages(
            FakeClient(),
            {"department_id": "D16", "department_name_kor": "테스트전공", "homepage_url": ""},
            {
                "faculty_urls": [seed_url], "allowed_hosts": ["gscst.postech.ac.kr"],
                "scope_query_params": {"depart": ["16"]}, "follow_links": False, "max_depth": 0,
            },
            max_pages=4, max_depth=0, known_names=set(), paths=fake_paths, save_raw=False,
        )
        discovered_urls = {page.url for page in discovered}
        assert normalize_url(seed_url) in discovered_urls and normalize_url(same_scope_url) in discovered_urls
        assert normalize_url(sibling_url) not in discovered_urls
    finally:
        shutil.rmtree(fake_dir, ignore_errors=True)
    tests += 1

    # Full authoritative commit requires every selected department and rejects
    # both evidence-less affiliations and foreign primary source pages.
    commit_departments = [
        {"department_id": "D1", "department_name_kor": "학과A", "homepage_url": "https://a.postech.ac.kr", "enrichment_status": "success"},
        {"department_id": "D2", "department_name_kor": "학과B", "homepage_url": "https://b.postech.ac.kr", "enrichment_status": "success"},
    ]
    commit_labs = [
        {
            "lab_id": "L1", "department_id": "D1", "primary_department_id": "D1",
            "department_name": "학과A", "affiliated_programs": "학과A",
            "department_page_url": "https://a.postech.ac.kr/faculty",
        }
    ]
    reasons, metrics = authoritative_commit_failure_reasons(
        commit_departments, commit_labs, {}
    )
    assert not reasons and metrics["successful_departments"] == 2
    commit_departments[1]["enrichment_status"] = "failed"
    reasons, _ = authoritative_commit_failure_reasons(commit_departments, commit_labs, {})
    assert reasons and "학과 성공" in reasons[0]
    tests += 1

    # Roster coverage guard scales from the known first-stage e-mail roster and
    # never accepts a single accidental card for a normal-sized department.
    assert minimum_primary_roster_matches(19, {}) == 4
    assert minimum_primary_roster_matches(3, {}) == 1
    assert minimum_primary_roster_matches(0, {}) == 0
    tests += 1

    assert clean_summary_value(
        'Miao, L., Murray, D., Jung, W.-S., "The latent structure of national scientific development," '
        'Nature Human Behaviour, vol. 6, p. 1206-1217, 2022. doi: 10.1038/example'
    ) == ""
    assert clean_location_value(
        "326, POSTECH Biotech Center (PBC), 55, Jigok-ro, Nam-gu, Pohang-si"
    ) == "POSTECH Biotech Center (PBC) 326"
    assert looks_like_person_segment("트란마이란")
    assert not looks_like_person_segment("나노구조체")
    assert clean_location_value(
        "#214 LG Research Bldg, #77 Cheongam-ro Pohang-si, Republic of Korea"
    ) == "LG Research Bldg 214"
    assert clean_location_value(
        "[25.05] 김용태 교수 POSTECH 컨소시엄, 대규모 수소 국제공동연구 사업 최종 선정"
    ) == ""
    assert is_non_identity_source_url(
        "https://me.postech.ac.kr/ko/board/view?bd_id=news01&wr_id=929"
    )
    assert is_non_identity_source_url(
        "https://ph.postech.ac.kr/physics/community/news.do?mode=view&articleNo=1"
    )
    assert summary_looks_like_news_article(
        '김석 교수 연구팀, "반도체도 초고층 시대" 성능 높인다'
    )
    assert not summary_has_lab_intro_context(
        '김석 교수 연구팀, "반도체도 초고층 시대" 성능 높인다'
    )
    assert summary_has_lab_intro_context(
        "MARCH 연구실에서는 휴먼-로봇 인터페이스 연구를 수행합니다."
    )
    tests += 1

    identity_html = """
    <html><body><h2>교수진</h2><div>홍길동</div>
    <a href='mailto:hong@postech.ac.kr'>hong@postech.ac.kr</a></body></html>
    """
    identity_result = PageResult(
        "https://example.postech.ac.kr/faculty", identity_html, "test", 200
    )
    assert page_has_faculty_identity_context(identity_result, {normalize_name("홍길동")})
    assert not page_has_faculty_identity_context(
        PageResult("https://example.postech.ac.kr/news/1", identity_html, "test", 200),
        {normalize_name("홍길동")},
    )
    tests += 1

    central_result = PageResult(
        "https://www.postech.ac.kr/kor/research-industry-academia/researcher-search.do?mode=view&id=abc",
        "<html><body><h3>홍길동 교수</h3><span>hong@postech.ac.kr</span></body></html>",
        "test",
        200,
    )
    assert central_profile_identity_matches(
        central_result, {"professor_name": "홍길동", "email": "hong@postech.ac.kr"}
    )
    assert not central_profile_identity_matches(
        central_result, {"professor_name": "김철수", "email": "hong@postech.ac.kr"}
    )
    tests += 1

    fallback_departments = [
        {"department_id": "D1", "department_name_kor": "A", "enrichment_status": "success"},
        {"department_id": "D2", "department_name_kor": "B", "enrichment_status": "success_identity_fallback"},
    ]
    reasons, metrics = authoritative_commit_failure_reasons(fallback_departments, [], {})
    assert not reasons and metrics["successful_departments"] == 2
    tests += 1

    with tempfile.TemporaryDirectory() as temp_dir:
        override_path = Path(temp_dir) / "site_overrides.json"
        override_path.write_text(
            json.dumps(
                {
                    "정보통신대학원": {
                        "faculty_urls": [
                            "https://eecs.postech.ac.kr/teaching-and-research/professor/"
                        ],
                        "scope_query_params": {"dept": ["ALL"]},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        hardened = load_overrides(override_path)["정보통신대학원"]
        assert hardened["scope_query_params"] == {"dept": ["103"]}
        assert hardened["faculty_urls"] == [
            "https://eecs.postech.ac.kr/teaching-and-research/professor/?dept=103"
        ]
    tests += 1

    scoped_html = """
    <html><body><h2>교수</h2>
      <div class='professor-card'><strong>홍길동 교수</strong><span>연구분야</span></div>
    </body></html>
    """
    scoped_result = PageResult(
        "https://program.postech.ac.kr/professor", scoped_html, "test", 200
    )
    scoped_lab = {
        "LAB_X": {
            "lab_id": "LAB_X",
            "professor_name": "홍길동",
            "email": "hong@postech.ac.kr",
        }
    }
    scoped_matches = build_page_matches(
        scoped_result,
        {"max_card_emails": 2, "max_card_identities": 2},
        scoped_lab,
        {},
        {normalize_name("홍길동"): "LAB_X"},
        {normalize_name("홍길동")},
    )
    assert len(scoped_matches) == 1 and scoped_matches[0].method.startswith("name")
    tests += 1

    # Exact-email official cards must expose both the lab homepage and lab name.
    lab_card_soup = BeautifulSoup(
        """<div class='person'><h3>김도형</h3>
        <p>E-mail kimd42@postech.ac.kr</p>
        <p>Research Office Systems Neuroscience Lab for Cognition and Neural Interface</p>
        <p>Official Website <a href='https://anne.postech.ac.kr'>Homepage</a></p></div>""",
        "lxml",
    )
    link_lab = {
        "lab_id": "LAB_LINK_1", "professor_name": "김도형",
        "email": "kimd42@postech.ac.kr", "professor_profile_url": "",
    }
    link_candidates = extract_lab_link_candidates_from_block(
        link_lab, lab_card_soup.div, "https://emed.postech.ac.kr/web/?sub=lab&top=study",
        "official_directory", True, True,
    )
    assert link_candidates and link_candidates[0].url == "https://anne.postech.ac.kr/"
    assert "Systems Neuroscience" in link_candidates[0].lab_name
    tests += 1

    # Icon-only homepage links inherit their strong label from the parent card.
    icon_soup = BeautifulSoup(
        """<div class='faculty'><span>jskoh@postech.ac.kr</span>
        <div class='website'>Website <a aria-label='open website' href='https://sites.google.com/view/jesungkoh'>↗</a></div>
        <div>Lab. Mechanical Intelligence Robotic Research Laboratory</div></div>""",
        "lxml",
    )
    icon_candidates = extract_lab_link_candidates_from_block(
        {"lab_id": "L2", "professor_name": "고제성", "email": "jskoh@postech.ac.kr", "professor_profile_url": ""},
        icon_soup.div, "https://me.postech.ac.kr/page/professor32_en",
        "professor_profile", True, False,
    )
    assert icon_candidates and "sites.google.com/view/jesungkoh" in icon_candidates[0].url
    assert "Mechanical Intelligence" in icon_candidates[0].lab_name
    tests += 1

    class FakeHomepageClient:
        def fetch(self, url: str, force_browser: bool = False) -> PageResult:
            return PageResult(
                "https://lab.example.com/",
                """<html><head><title>Adaptive Robotics Laboratory</title></head><body>
                <h1>Adaptive Robotics Laboratory</h1><p>Professor Hong Gil Dong</p>
                <p>hong@postech.ac.kr</p><p>Our research focuses on adaptive robot learning.</p>
                </body></html>""",
                "fake", 200,
            )
    verified_update, verified_method = verify_lab_link_candidate(
        FakeHomepageClient(),
        {"professor_name": "홍길동", "email": "hong@postech.ac.kr", "primary_field": "Robotics", "professor_profile_url": ""},
        LabLinkCandidate(
            lab_id="L3", url="https://lab.example.com", source_url="https://dept.postech.ac.kr/faculty",
            source_kind="official_directory", evidence_method="official_exact_email_card", score=100,
            label_text="연구실 홈페이지", exact_email=True, exact_name=True,
        ),
        ambiguous_name=False,
    )
    assert verified_update["lab_url_status"] == "verified_homepage"
    assert verified_update["lab_name_kor"] == "Adaptive Robotics Laboratory"
    assert verified_method == "homepage_exact_email"
    tests += 1

    class FakeDeadClient:
        def fetch(self, url: str, force_browser: bool = False) -> PageResult:
            return PageResult(url, "<html><title>404 Not Found</title><body>404 Not Found</body></html>", "fake", 200)
    dead_update, dead_reason = verify_lab_link_candidate(
        FakeDeadClient(),
        {"professor_name": "홍길동", "email": "hong@postech.ac.kr", "professor_profile_url": ""},
        LabLinkCandidate(
            lab_id="L4", url="https://dead.example.com", source_url="https://dept.postech.ac.kr/faculty",
            source_kind="official_directory", evidence_method="official_exact_email_card", score=100,
            label_text="Official Website", exact_email=True,
        ),
        ambiguous_name=False,
    )
    assert not dead_update and dead_reason == "dead_or_generic_page"
    tests += 1

    class FakeUnavailableClient:
        def fetch(self, url: str, force_browser: bool = False) -> PageResult:
            raise requests.Timeout("temporary timeout")
    card_update, card_method = verify_lab_link_candidate(
        FakeUnavailableClient(),
        {"professor_name": "홍길동", "email": "hong@postech.ac.kr", "professor_profile_url": ""},
        LabLinkCandidate(
            lab_id="L5", url="https://lab-temporary.example.com",
            source_url="https://dept.postech.ac.kr/faculty",
            source_kind="official_directory", evidence_method="official_exact_email_card", score=120,
            label_text="연구실 홈페이지", exact_email=True, lab_name="Adaptive Systems Laboratory",
        ),
        ambiguous_name=False,
    )
    assert card_update["lab_url_status"] == "verified_card"
    assert card_method == "official_exact_email_card_unreachable"
    tests += 1

    # The lab-link transaction must reject one trusted URL assigned across departments.
    duplicate_issues = lab_link_safety_issues(
        [],
        [
            {"lab_id": "A", "email": "a@postech.ac.kr", "primary_department_id": "D1", "lab_url": "https://same.example.com", "lab_url_status": "verified_homepage", "professor_profile_url": ""},
            {"lab_id": "B", "email": "b@postech.ac.kr", "primary_department_id": "D2", "lab_url": "https://same.example.com", "lab_url_status": "verified_card", "professor_profile_url": ""},
        ],
    )
    assert any("다중 교수 충돌" in issue for issue in duplicate_issues)
    tests += 1

    # AIF deterministic list URL and unique-name official-card recovery.
    assert "article.offset=20" in aif_researcher_list_url(20)
    tests += 1
    aif_html = """
    <html><body><ul><li class='researcher-card'>
      <a href='/kor/research/researcher-search.do?articleNo=1&mode=view'>홍길동</a>
      <span>기계공학과</span><a href='https://honglab.example.com'>Website</a>
    </li></ul></body></html>
    """
    aif_candidates = defaultdict(list)
    aif_names = {}
    aif_labs = {"L6": {"lab_id": "L6", "professor_name": "홍길동", "email": "", "department_name": "기계공학과", "professor_profile_url": ""}}
    aif_match = mine_aif_unique_name_cards(
        PageResult(aif_researcher_list_url(0), aif_html, "fake"), aif_labs,
        {normalize_name("홍길동"): "L6"}, {normalize_name("홍길동")}, aif_candidates, aif_names,
    )
    assert aif_match == 1 and aif_candidates["L6"][0].url == "https://honglab.example.com/"
    tests += 1

    probe_html = """<html><body><a href='/people'>People</a><a href='/publications'>Publications</a></body></html>"""
    probes = homepage_identity_probe_urls(BeautifulSoup(probe_html, "lxml"), "https://lab.example.com/", 2)
    assert probes == ["https://lab.example.com/people"]
    tests += 1

    class FakeDepartmentClient:
        def fetch(self, url: str, force_browser: bool = False) -> PageResult:
            if url.endswith("/people"):
                return PageResult(url, "<html><h1>Faculty</h1><p>hong@postech.ac.kr</p><p>Professor Hong</p><p>Research areas</p></html>", "fake", 200)
            return PageResult(url, "<html><title>Department of Physics</title><body><a href='/people'>People</a><p>Research</p></body></html>", "fake", 200)
    department_candidate, department_reason = verify_lab_link_candidate(
        FakeDepartmentClient(),
        {"professor_name": "홍길동", "email": "hong@postech.ac.kr", "professor_profile_url": ""},
        LabLinkCandidate(
            lab_id="DHOME", url="https://dept.postech.ac.kr/", source_url="https://aif.postech.ac.kr/list",
            source_kind="aif_researcher_index", evidence_method="official_exact_email_card", score=100,
            label_text="Website", exact_email=True, exact_name=True,
        ),
        ambiguous_name=False,
        department_url_keys={canonical_url_key("https://dept.postech.ac.kr/")},
        known_professor_emails={"hong@postech.ac.kr"},
        known_professor_names={normalize_name("홍길동")},
    )
    assert not department_candidate and department_reason == "known_department_page"
    tests += 1

    assert not clean_lab_name("Our lab is funded by", "홍길동")
    assert not clean_lab_name("Head, Hana-Postech TechFin Collab", "홍길동")
    assert clean_lab_name("Welcome to Adaptive Robotics Lab", "홍길동") == "Adaptive Robotics Lab"
    assert clean_lab_name("권순호 교수 연구실(증강재료설계연구실", "권순호") == "증강재료설계연구실"
    tests += 1

    sanitize_rows = {
        "S1": {
            "lab_id": "S1", "professor_name": "홍길동", "lab_url": "https://dept.postech.ac.kr/",
            "lab_url_status": "verified_homepage", "lab_name_kor": "홍길동 교수 연구실",
            "lab_name_eng": "Adaptive Robotics Lab", "field_provenance": "{}",
        }
    }
    sanitize_metrics = sanitize_existing_lab_link_records(
        [{"homepage_url": "https://dept.postech.ac.kr/", "detail_url": "", "source_url": "", "faculty_page_urls": ""}],
        sanitize_rows,
    )
    assert sanitize_metrics["invalidated_count"] == 1
    assert not sanitize_rows["S1"]["lab_url"]
    assert sanitize_rows["S1"]["lab_name_kor"] == "Adaptive Robotics Lab"
    tests += 1

    manual_rows = {
        "M1": {
            "lab_id": "M1", "professor_name": "홍길동",
            "lab_url": "https://manual.example.com/", "lab_url_status": "manual",
            "lab_name_kor": "Adaptive Robotics Lab", "lab_name_eng": "",
            "field_provenance": "{}", "enriched_at": "2026-01-01T00:00:00+09:00",
        }
    }
    manual_metrics = sanitize_existing_lab_link_records([], manual_rows)
    assert manual_metrics["manual_provenance_backfilled"] == 1
    assert lab_url_provenance(manual_rows["M1"])["method"] == "manual_existing"
    tests += 1

    shared_rows = [
        {"lab_id": "SL1", "professor_name": "가나다", "email": "a@postech.ac.kr", "department_id": "AI", "department_name": "인공지능대학원", "lab_name_kor": "Machine Learning Lab", "lab_url": "https://ml.example.com/", "lab_url_status": "verified_homepage"},
        {"lab_id": "SL2", "professor_name": "라마바", "email": "b@postech.ac.kr", "department_id": "AI", "department_name": "인공지능대학원", "lab_name_kor": "Machine Learning Lab", "lab_url": "https://ml.example.com/", "lab_url_status": "verified_homepage"},
        {"lab_id": "SL3", "professor_name": "사아자", "email": "c@postech.ac.kr", "department_id": "AI", "department_name": "인공지능대학원", "lab_name_kor": "Machine Learning Lab", "lab_url": "https://ml.example.com/", "lab_url_status": "verified_homepage"},
    ]
    for row in shared_rows:
        row["field_provenance"] = compact_json({"lab_url": {
            "source_url": "https://ai.postech.ac.kr/faculty",
            "verified_url": "https://ml.example.com/",
            "method": "homepage_exact_email",
            "verified_at": "2026-01-01T00:00:00+09:00",
        }})
    assert mark_shared_lab_verified(shared_rows) == 3
    assert shared_lab_group_is_verified(shared_rows)
    assert not lab_link_safety_issues([], shared_rows)
    shared_report = CleanReport()
    remove_repeated_generic_values(shared_rows, shared_report)
    assert all(row["lab_name_kor"] == "Machine Learning Lab" for row in shared_rows)
    tests += 1

    generic_rows = [
        {"lab_id": "G1", "professor_name": "가나다", "email": "g1@postech.ac.kr", "department_name": "인공지능대학원", "lab_name_kor": "Machine Learning Lab", "lab_name_eng": "Machine Learning Lab", "lab_url": "", "lab_url_status": "unverified", "field_provenance": "{}"},
        {"lab_id": "G2", "professor_name": "라마바", "email": "g2@postech.ac.kr", "department_name": "인공지능대학원", "lab_name_kor": "Machine Learning Lab", "lab_name_eng": "Machine Learning Lab @ Postech", "lab_url": "", "lab_url_status": "unverified", "field_provenance": "{}"},
        {"lab_id": "G3", "professor_name": "사아자", "email": "g3@postech.ac.kr", "department_name": "인공지능대학원", "lab_name_kor": "Machine Learning Lab", "lab_name_eng": "Machine Learning Lab @ Postech", "lab_url": "", "lab_url_status": "unverified", "field_provenance": "{}"},
    ]
    generic_report = CleanReport()
    remove_repeated_generic_values(generic_rows, generic_report)
    assert all(looks_placeholder_lab_name(row["lab_name_kor"]) for row in generic_rows)
    assert all(not row["lab_name_eng"] for row in generic_rows)
    tests += 1

    # Clean-only affiliation quarantine is idempotent and preserves the exact
    # faculty page needed by scoped unique-name evidence.
    q_url = "https://gscst.postech.ac.kr/web/?depart=16&position=2&sub=professor&top=member"
    q_departments = [{
        "department_id": "D16", "department_name_kor": "푸드테크융합전공",
        "faculty_page_urls": q_url, "homepage_url": "", "detail_url": "",
    }]
    q_rows = {"Q1": {
        "lab_id": "Q1", "department_name": "기계공학과",
        "affiliated_programs": "기계공학과;푸드테크융합전공",
        "affiliation_evidence": compact_json({
            "기계공학과": {"method": "stage1_primary_department", "primary": True, "source_url": "https://postech.ac.kr/profile"},
            "푸드테크융합전공": {"method": "unique_name_scoped_faculty_page", "primary": False, "source_url": q_url},
        }),
    }}
    q_overrides = effective_builtin_overrides()
    assert quarantine_unverified_affiliations(q_departments, q_rows, q_overrides) == 0
    assert quarantine_unverified_affiliations(q_departments, q_rows, q_overrides) == 0
    assert q_rows["Q1"]["affiliated_programs"] == "기계공학과;푸드테크융합전공"
    assert q_departments[0]["faculty_page_urls"] == q_url
    tests += 1

    # A trusted legacy URL with unchanged values still receives field-level
    # provenance after successful revalidation.
    legacy = {
        "lab_url": "https://lab.example.com/", "lab_url_status": "verified_homepage",
        "lab_name_kor": "Adaptive Robotics Lab", "lab_name_eng": "Adaptive Robotics Lab",
        "field_provenance": "{}", "enrichment_source_urls": "https://lab.example.com/",
        "enricher_version": ENRICHER_VERSION,
    }
    same_update = {"lab_url": "https://lab.example.com/", "lab_url_status": "verified_homepage"}
    legacy_merged, legacy_changed = merge_lab_update(legacy, same_update, "")
    assert not legacy_changed
    legacy_candidate = LabLinkCandidate(
        lab_id="LEGACY", url="https://lab.example.com/",
        source_url="https://aif.postech.ac.kr/official", source_kind="existing_trusted_revalidation",
        evidence_method="legacy_trusted_revalidation", score=82,
    )
    record_lab_link_provenance(legacy_merged, ["lab_url", "lab_url_status"], legacy_candidate, same_update, "homepage_exact_email")
    assert lab_url_provenance(legacy_merged)["verified_url"] == "https://lab.example.com/"
    assert lab_url_provenance_complete(legacy_merged)
    assert lab_link_target_required(legacy, refresh_all=False)
    assert lab_link_revalidation_required(legacy, refresh_all=False)
    assert not lab_link_target_required(legacy_merged, refresh_all=False)
    assert not lab_link_revalidation_required(legacy_merged, refresh_all=False)
    assert lab_link_target_required(legacy_merged, refresh_all=True)
    assert lab_link_revalidation_required(legacy_merged, refresh_all=True)
    tests += 1

    department_candidate = LabLinkCandidate(
        lab_id="P", url="https://new.example.com/", source_url="https://dept.postech.ac.kr/faculty/hong",
        source_kind="department_profile", evidence_method="official_exact_email_card", score=90, exact_email=True,
    )
    aif_candidate = LabLinkCandidate(
        lab_id="P", url="https://old.example.com/", source_url=aif_researcher_list_url(0),
        source_kind="aif_researcher_index", evidence_method="official_exact_email_card", score=140, exact_email=True,
    )
    assert candidate_preference_key(department_candidate) > candidate_preference_key(aif_candidate)
    tests += 1

    same_department_unverified = [
        {"lab_id": "U1", "email": "u1@postech.ac.kr", "department_id": "D", "lab_url": "https://same.example.com/", "lab_url_status": "verified_homepage", "field_provenance": "{}", "professor_profile_url": ""},
        {"lab_id": "U2", "email": "u2@postech.ac.kr", "department_id": "D", "lab_url": "https://same.example.com/", "lab_url_status": "verified_homepage", "field_provenance": "{}", "professor_profile_url": ""},
    ]
    assert any("공유 연구실 근거 부족" in issue for issue in lab_link_safety_issues([], same_department_unverified))
    tests += 1

    cross_listed = {
        "X": {
            "lab_id": "X", "department_id": "AI", "primary_department_id": "AI",
            "department_name": "인공지능대학원", "professor_name": "홍길동",
            "email": "hong@postech.ac.kr", "department_page_url": "https://cse.postech.ac.kr/faculty",
            "lab_url": "https://hong.example.com/", "lab_url_status": "verified_card",
            "lab_name_kor": "Hong Lab", "lab_name_eng": "Hong Lab",
            "field_provenance": compact_json({"lab_url": {
                "source_url": "https://cse.postech.ac.kr/faculty",
                "verified_url": "https://hong.example.com/",
                "method": "department_faculty_card_exact_email_direct_lab_link",
                "verified_at": "2026-01-01T00:00:00+09:00",
            }}),
            "affiliated_programs": "인공지능대학원", "enrichment_source_urls": "",
        }
    }
    cross_departments = [{
        "department_id": "AI", "department_name_kor": "인공지능대학원",
        "homepage_url": "https://ai.postech.ac.kr/", "detail_url": "https://ai.postech.ac.kr/",
    }]
    assert not reset_foreign_department_provenance(cross_departments, cross_listed, {})
    assert cross_listed["X"]["lab_url"] == "https://hong.example.com/"
    tests += 1

    state_rows = {
        "A": {"lab_id": "A", "data_state": "authoritative_rebuilt", "enrichment_status": "success"},
        "B": {"lab_id": "B", "data_state": "clean_only_quarantined", "enrichment_status": "no_match"},
        "C": {"lab_id": "C", "data_state": "clean_only_quarantined", "enrichment_status": "matched_identity_only"},
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_dir = Path(temp_dir)
        atomic_write_csv(
            backup_dir / "labs_before_stage2_20260101.csv",
            [{"lab_id": "B", "data_state": "authoritative_central_identity_fallback"}],
            ["lab_id", "data_state"],
        )
        state_metrics = recover_data_states_from_backups(state_rows, backup_dir)
    assert state_rows["A"]["data_state"] == "authoritative_rebuilt"
    assert state_rows["B"]["data_state"] == "authoritative_central_identity_fallback"
    assert state_rows["C"]["data_state"] == "authoritative_identity_only"
    assert state_metrics == {"preserved": 1, "restored_from_backup": 1, "reconstructed": 1}
    tests += 1

    assert classify_lab_link_verification_failure("fetch_failed: timeout") == "transient_network_failure"
    assert classify_lab_link_verification_failure("identity_conflict") == "identity_insufficient"
    assert classify_lab_link_verification_failure("dead_or_generic_page") == "dead_homepage"
    assert classify_lab_link_verification_failure("known_department_page") == "false_positive_page"
    tests += 1

    legacy_schema_row = {
        "lab_url": "https://legacy.example.com/",
        "lab_url_status": "verified_homepage",
        "field_provenance": compact_json({"lab_url": {
            "source_url": "https://dept.postech.ac.kr/faculty/a",
            "method": "homepage_exact_email",
            "verified_at": "2026-01-01T00:00:00+09:00",
        }}),
    }
    assert migrate_legacy_lab_url_provenance(legacy_schema_row)
    assert lab_url_provenance_complete(legacy_schema_row)
    assert not migrate_legacy_lab_url_provenance(legacy_schema_row)
    tests += 1

    reconstructed_row = {
        "lab_url": "https://recover.example.com/",
        "lab_url_status": "verified_homepage",
        "professor_profile_url": "https://www.postech.ac.kr/kor/research-industry-academia/researcher-search.do?mode=view&id=abc",
        "department_page_url": "",
        "source_url": "",
        "enrichment_source_urls": "https://recover.example.com/;https://www.postech.ac.kr/kor/research-industry-academia/researcher-search.do?mode=view&id=abc",
        "field_provenance": "{}",
        "enriched_at": "2026-01-01T00:00:00+09:00",
    }
    assert reconstruct_missing_lab_url_provenance(reconstructed_row)
    assert lab_url_provenance_complete(reconstructed_row)
    assert lab_url_provenance(reconstructed_row)["source_kind"] == "legacy_provenance_reconstruction"
    tests += 1

    guard_rows = {"L": {
        "lab_url": "", "lab_url_status": "unverified",
        "lab_name_kor": "홍길동 교수 연구실", "lab_name_eng": "",
        "field_provenance": "",
    }}
    guard_before = {"L": {
        "lab_url": "https://preserve.example.com/",
        "lab_url_status": "verified_card",
        "lab_name_kor": "Preservation Lab", "lab_name_eng": "Preservation Lab",
        "field_provenance": compact_json({"lab_url": {
            "source_url": "https://dept.postech.ac.kr/faculty",
            "verified_url": "https://preserve.example.com/",
            "method": "official_exact_email_card_reachable",
            "verified_at": "2026-01-01T00:00:00+09:00",
        }}),
        "professor_profile_url": "", "department_page_url": "",
        "enrichment_source_urls": "",
    }}
    guard_report = restore_unexplained_link_regressions(guard_rows, guard_before)
    assert guard_rows["L"]["lab_url"] == "https://preserve.example.com/"
    assert guard_rows["L"]["lab_url_status"] == "verified_card"
    assert guard_rows["L"]["lab_name_kor"] == "Preservation Lab"
    assert guard_report["url_restored"] == 1
    tests += 1

    assert clean_location_value("37673 경상북도 포항시 남구 청암로 77(효자동 산31)") == ""
    tests += 1
    assert clean_location_value("3동 3329호") == "3동 3329호"
    tests += 1
    assert clean_summary_value("대학원생 및 Post-Doc 모집 본 연구실에서는 연구원을 모집하고 있습니다. 관심 있는 학생은 연락 주세요~ more") == ""
    tests += 1
    assert clean_summary_value("고준위방사성폐기물 관리 특별법 통과! 국회를 통과해 법적 제도적 기반을 갖추게 되었습니다.") == ""
    tests += 1
    assert clean_summary_value("We are hiring highly motivated graduate students and postdoctoral scholars") == ""
    tests += 1
    assert clean_summary_value("첨단에너지AI연구실 / Numerical Investigation for Nature & Energy Lab") == ""
    tests += 1

    print(f"SELF TEST PASSED: {tests} tests")


# ============================================================
# 14. CLI
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
    parser.add_argument("--connect-timeout", type=int, default=DEFAULT_CONNECT_TIMEOUT_SECONDS)
    parser.add_argument("--http-retries", type=int, default=DEFAULT_HTTP_RETRIES)
    parser.add_argument("--force", action="store_true", help="부분/증분 실행에서도 이전 성공 상태를 다시 수집")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="기존 성공 학과를 건너뛰는 증분 모드. 기본 전체 실행은 권위 소스 재구축",
    )
    parser.add_argument("--dry-run", action="store_true", help="CSV를 수정하지 않고 정제/수집 결과만 출력")
    parser.add_argument("--clean-only", action="store_true", help="네트워크 요청 없이 기존 CSV 오염값만 정제")
    parser.add_argument(
        "--reset-affiliations",
        action="store_true",
        help="전체 강제 재수집 전에 affiliated_programs를 주 소속으로 초기화하여 과거 교차오염 제거",
    )
    parser.add_argument("--skip-lab-homepages", action="store_true", help="개별 연구실 홈페이지 검증·보완 생략")
    parser.add_argument(
        "--lab-links-only",
        action="store_true",
        help="학과·연구실적은 건드리지 않고 labs.csv의 연구실 링크와 연구실명만 집중 보완",
    )
    parser.add_argument(
        "--lab-link-max-pages",
        type=int,
        default=DEFAULT_LAB_LINK_MAX_PAGES,
        help="랩 링크 탐색에 사용할 공식 소스 페이지 전체 상한",
    )
    parser.add_argument(
        "--lab-link-max-depth",
        type=int,
        default=DEFAULT_LAB_LINK_MAX_DEPTH,
        help="공식 교수 목록에서 상세 프로필·페이지네이션을 따라갈 깊이",
    )
    parser.add_argument(
        "--lab-link-candidates-per-lab",
        type=int,
        default=DEFAULT_LAB_LINK_CANDIDATES_PER_LAB,
        help="연구실별로 실제 접근·신원 검증할 URL 후보 상한",
    )
    parser.add_argument(
        "--lab-link-identity-sources-per-lab",
        type=int,
        default=DEFAULT_LAB_LINK_IDENTITY_SOURCES_PER_LAB,
        help="전역 페이지 상한과 별개로 교수별 직접 확인할 공식 신원 페이지 상한",
    )
    parser.add_argument(
        "--lab-link-host-page-cap",
        type=int,
        default=DEFAULT_LAB_LINK_HOST_PAGE_CAP,
        help="한 호스트에서 수집할 공식 페이지 상한. 0이면 제한 없음",
    )
    parser.add_argument(
        "--lab-link-max-host-failures",
        type=int,
        default=DEFAULT_MAX_HOST_FAILURES,
        help="같은 호스트가 연속 실패하면 이번 실행에서 차단할 횟수. 0이면 차단 안 함",
    )
    parser.add_argument(
        "--lab-link-progress-every",
        type=int,
        default=DEFAULT_LAB_LINK_PROGRESS_EVERY,
        help="몇 건마다 진행 로그를 출력할지",
    )
    parser.add_argument(
        "--lab-link-time-budget-minutes",
        type=float,
        default=DEFAULT_LAB_LINK_TIME_BUDGET_MINUTES,
        help="랩 링크 단계 전체 시간 예산(분). 0이면 제한 없음",
    )
    parser.add_argument(
        "--lab-link-homepage-probe-pages",
        type=int,
        default=DEFAULT_LAB_LINK_HOMEPAGE_PROBE_PAGES,
        help="후보 홈페이지에서 About/People/Contact 등 신원 확인용 내부 페이지 상한",
    )
    parser.add_argument(
        "--refresh-lab-links",
        action="store_true",
        help="이미 검증된 링크도 다시 접근해 URL·연구실명을 갱신",
    )
    parser.add_argument(
        "--backup-keep",
        type=int,
        default=3,
        help="성공 실행 후 종류별 최신 백업 보관 개수. 0이면 정리하지 않음",
    )
    parser.add_argument("--browser-fallback", action="store_true", help="정적 HTML 부족 시 Playwright 사용")
    parser.add_argument("--allow-insecure", action="store_true", help="SSL 인증서 검증 실패 사이트 허용")
    parser.add_argument("--ignore-robots", action="store_true", help="robots.txt 검사 생략")
    parser.add_argument("--save-raw-html", action="store_true", help="수집 HTML을 <data-dir>/raw_stage2에 저장")
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="네트워크·CSV 수정 없이 departments/labs/research_outputs 데이터 무결성 감사",
    )
    parser.add_argument(
        "--clean-research-outputs",
        action="store_true",
        help="원본 research_outputs.csv는 유지하고 clean/recent 파일 생성 및 labs 집계 갱신",
    )
    parser.add_argument(
        "--skip-research-cleaning",
        action="store_true",
        help="기본 전체 재구축 후 research_outputs_clean/recent 생성 생략",
    )
    parser.add_argument(
        "--skip-final-audit",
        action="store_true",
        help="기본 전체 재구축 후 최종 데이터 감사 생략",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="내장 범위 잠금·매칭·출처격리·동명이인·연구실적 정제 테스트 실행",
    )
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
    if args.connect_timeout < 1:
        parser.error("--connect-timeout은 1 이상이어야 합니다.")
    if args.http_retries < 0:
        parser.error("--http-retries는 0 이상이어야 합니다.")
    if args.lab_link_max_pages < 1:
        parser.error("--lab-link-max-pages는 1 이상이어야 합니다.")
    if args.lab_link_max_depth < 0:
        parser.error("--lab-link-max-depth는 0 이상이어야 합니다.")
    if args.lab_link_candidates_per_lab < 1:
        parser.error("--lab-link-candidates-per-lab은 1 이상이어야 합니다.")
    if args.lab_link_identity_sources_per_lab < 1:
        parser.error("--lab-link-identity-sources-per-lab은 1 이상이어야 합니다.")
    if args.lab_link_host_page_cap < 0:
        parser.error("--lab-link-host-page-cap은 0 이상이어야 합니다.")
    if args.lab_link_max_host_failures < 0:
        parser.error("--lab-link-max-host-failures는 0 이상이어야 합니다.")
    if args.lab_link_progress_every < 1:
        parser.error("--lab-link-progress-every는 1 이상이어야 합니다.")
    if args.lab_link_time_budget_minutes < 0:
        parser.error("--lab-link-time-budget-minutes는 0 이상이어야 합니다.")
    if args.lab_link_homepage_probe_pages < 0:
        parser.error("--lab-link-homepage-probe-pages는 0 이상이어야 합니다.")
    if args.backup_keep < 0:
        parser.error("--backup-keep는 0 이상이어야 합니다.")
    if args.test_limit is not None and args.test_limit < 1:
        parser.error("--test-limit은 1 이상이어야 합니다.")
    if args.reset_affiliations and args.clean_only:
        parser.error("--reset-affiliations는 --clean-only와 함께 사용할 수 없습니다.")
    if args.reset_affiliations and (args.department or args.test_limit is not None):
        parser.error("--reset-affiliations는 일부 학과 실행과 함께 사용할 수 없습니다. 전체 재수집에만 사용하세요.")
    if args.incremental and args.reset_affiliations:
        parser.error("--incremental과 --reset-affiliations는 함께 사용할 수 없습니다.")
    exclusive_modes = sum(
        bool(value)
        for value in (args.audit_only, args.clean_research_outputs, args.self_test, args.lab_links_only)
    )
    if exclusive_modes > 1:
        parser.error(
            "--audit-only, --clean-research-outputs, --self-test, --lab-links-only는 동시에 사용할 수 없습니다."
        )
    if (args.audit_only or args.clean_research_outputs or args.self_test or args.lab_links_only) and args.clean_only:
        parser.error("감사/연구실적/자체테스트/랩링크 모드는 --clean-only와 함께 사용할 수 없습니다.")
    if args.lab_links_only and args.skip_lab_homepages:
        parser.error("--lab-links-only와 --skip-lab-homepages는 함께 사용할 수 없습니다.")
    if args.lab_links_only and (args.department or args.test_limit is not None or args.reset_affiliations):
        parser.error("--lab-links-only는 학과 범위·소속 초기화 옵션과 함께 사용할 수 없습니다.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)
    if args.self_test:
        run_self_test()
        return
    if args.audit_only:
        run_data_audit(args)
        return
    if args.clean_research_outputs:
        run_research_output_cleaner(args)
        return
    if args.lab_links_only:
        run_lab_links_only(args)
        return
    run_stage2(args)


if __name__ == "__main__":
    main()
