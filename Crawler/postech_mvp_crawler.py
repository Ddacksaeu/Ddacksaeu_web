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
ENRICHER_VERSION = "0.10.1-source-of-truth"

DEFAULT_DATA_DIR = Path("./data")
DEFAULT_REQUEST_DELAY_SECONDS = 0.55
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_DEPARTMENT_PAGES = 12
DEFAULT_MAX_DEPTH = 2
DEFAULT_CHECKPOINT_EVERY = 1
DEFAULT_RESPECT_ROBOTS = True
MIN_AUTHORITATIVE_SUCCESS_RATIO = 1.0
DEFAULT_MIN_PRIMARY_ROSTER_COVERAGE = 0.20
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
            try:
                page = browser.new_page(user_agent=USER_AGENT, locale="ko-KR")
                # networkidle is unreliable on university sites that keep
                # analytics/websocket connections open. DOMContentLoaded plus
                # a short settle period is more deterministic.
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)
                page.wait_for_timeout(1200)
                html = page.content()
                final_url = page.url
            finally:
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

        static_result: Optional[PageResult] = None
        try:
            static_result = self._static_fetch(url)
            result = static_result
            should_render = force_browser or (
                self._needs_browser(static_result.html) and self.browser_fallback
            )
            if should_render:
                try:
                    rendered = self._browser_fetch(static_result.url)
                    # Never replace a usable static page with an empty rendered
                    # shell. This is important for life.postech.ac.kr, which can
                    # intermittently fail under headless Chromium.
                    if not self._needs_browser(rendered.html) or self._needs_browser(static_result.html):
                        result = rendered
                except Exception:
                    if self._needs_browser(static_result.html):
                        raise
                    result = static_result
        except PermissionError:
            raise
        except Exception:
            if static_result is not None and not self._needs_browser(static_result.html):
                result = static_result
            elif not (force_browser or self.browser_fallback):
                raise
            else:
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
    return deep_merge_dict(BUILTIN_SITE_OVERRIDES, external)


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
    if text.startswith("[") or re.search(
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
        repeated_generic = (
            (len(professor_ids) >= 4 and len(departments) >= 2 and compact_generic)
            or (len(professor_ids) >= 3 and (compact_generic or english_generic))
            or repeated_wrapper_title
        )
        if repeated_generic:
            for row in group:
                professor = clean_text(row.get("professor_name", ""))
                row["lab_name_kor"] = f"{professor} 교수 연구실" if professor else ""
                report.duplicate_noise["generic_lab_name"] += 1
                report.changed_fields["lab_name_kor"] += 1

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

        if not homepage_trusted:
            if clean_text(lab.get("lab_url", "")):
                lab["lab_url"] = ""
                report["lab_url"] += 1
            if clean_text(lab.get("lab_url_status", "")) != "unverified":
                lab["lab_url_status"] = "unverified"
                report["lab_url_status"] += 1

        if not homepage_trusted:
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
) -> int:
    """Keep only primary affiliations when legacy rows have no evidence trail."""
    changed = 0
    for row in labs_by_id.values():
        primary = clean_text(row.get("department_name", ""))
        evidence = parse_json_dict(row.get("affiliation_evidence", ""))
        valid_secondary = [
            name for name, item in evidence.items()
            if name != primary and isinstance(item, dict)
            and clean_text(item.get("method", "")).startswith("email")
            and normalize_url(item.get("source_url", ""))
        ]
        new_value = merge_multi(primary, valid_secondary)
        if new_value != clean_text(row.get("affiliated_programs", "")):
            row["affiliated_programs"] = new_value
            changed += 1
        retained_evidence = parse_json_dict(primary_affiliation_evidence(row))
        for affiliation in valid_secondary:
            retained_evidence[affiliation] = evidence[affiliation]
        row["affiliation_evidence"] = compact_json(retained_evidence)
        row["data_state"] = "affiliations_quarantined"
    for department in departments:
        department["faculty_page_urls"] = ""
        department["faculty_match_count"] = "0"
        department["enrichment_status"] = "pending"
        department["enrichment_message"] = "증거 없는 과거 복수소속 격리 후 전체 재수집 대기"
        department["enriched_at"] = ""
    return changed


def exact_page_email_lab_ids(result: PageResult, labs_by_email: dict[str, str]) -> set[str]:
    return {
        labs_by_email[email]
        for email in {normalize_email(value) for value in EMAIL_RE.findall(result.html)}
        if email in labs_by_email
    }


def affiliation_evidence_violations(labs: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for row in labs:
        primary = clean_text(row.get("department_name", ""))
        evidence = parse_json_dict(row.get("affiliation_evidence", ""))
        for affiliation in split_multi(row.get("affiliated_programs", "")):
            if affiliation == primary:
                continue
            item = evidence.get(affiliation)
            if not isinstance(item, dict):
                violations.append({"lab_id": row.get("lab_id", ""), "affiliation": affiliation, "reason": "missing_evidence"})
                continue
            method = clean_text(item.get("method", ""))
            source_url = normalize_url(item.get("source_url", ""))
            if method == "manual":
                continue
            if not method.startswith("email") or not source_url:
                violations.append({"lab_id": row.get("lab_id", ""), "affiliation": affiliation, "reason": "weak_evidence"})
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
) -> tuple[list[str], dict[str, int]]:
    successful_departments = sum(
        clean_text(row.get("enrichment_status", "")) == "success"
        for row in selected_departments
    )
    minimum_successes = max(
        1, int(len(selected_departments) * MIN_AUTHORITATIVE_SUCCESS_RATIO + 0.999)
    ) if selected_departments else 0
    lab_rows = list(labs)
    evidence_violations = affiliation_evidence_violations(lab_rows)
    foreign_violations = foreign_department_page_violations(
        selected_departments, lab_rows, overrides
    )
    reasons: list[str] = []
    if successful_departments < minimum_successes:
        reasons.append(
            f"학과 성공 {successful_departments}/{len(selected_departments)} < 최소 {minimum_successes}"
        )
    if evidence_violations:
        reasons.append(f"복수소속 증거 위반 {len(evidence_violations)}건")
    if foreign_violations:
        reasons.append(f"주 소속 외부 페이지 출처 {len(foreign_violations)}건")
    return reasons, {
        "successful_departments": successful_departments,
        "minimum_successes": minimum_successes,
        "affiliation_evidence_violations": len(evidence_violations),
        "foreign_department_page_violations": len(foreign_violations),
    }


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
            departments, labs_by_id
        )
    elif args.reset_affiliations or authoritative_rebuild:
        reset_affiliation_count = reset_affiliations_for_full_rebuild(departments, labs_by_id)
        for lab in labs_by_id.values():
            lab["affiliation_evidence"] = primary_affiliation_evidence(lab)
            lab["field_provenance"] = ""
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
            lab["data_state"] = "clean_only_quarantined"
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
            save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run)
            continue

        department_match_ids: set[str] = set()
        faculty_pages: set[str] = set()
        field_update_counts: Counter[str] = Counter()
        page_exact_evidence_ids: set[str] = set()
        primary_name_evidence_ids: set[str] = set()

        for result in pages:
            page_exact_evidence_ids.update(exact_page_email_lab_ids(result, labs_by_email))
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
                if not is_primary_source and not match.method.startswith("email"):
                    print(
                        f"    [REJECT] 학과={department_name} | 교수={current.get('professor_name', '-') or '-'} | "
                        f"방식={match.method} | 보조소속은 정확 이메일 증거 필요"
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

        supported_ids = page_exact_evidence_ids | primary_name_evidence_ids
        expected_primary_ids = primary_lab_ids_by_department.get(department_id, set())
        recovered_primary_ids = supported_ids & expected_primary_ids
        required_primary_matches = minimum_primary_roster_matches(
            len(expected_primary_ids), override
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
            allowed_matches = max(len(supported_ids) + 3, int(len(supported_ids) * 1.20) + 1)
            unsupported_ids = department_match_ids - supported_ids
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
                    f"페이지 신원증거={len(supported_ids)}, 매칭={len(department_match_ids)}, "
                    f"설명불가={len(unsupported_ids)}; 학과 변경 전체 롤백"
                )
                department["faculty_match_count"] = "0"
                department["enriched_at"] = now_iso()
                department["enricher_version"] = ENRICHER_VERSION
                print(
                    f"[ROLLBACK-DEPT] 학과={department_name} | 페이지증거={len(supported_ids)} | "
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
            save_checkpoint(paths, departments, labs_by_id, department_fields, lab_fields, checkpoint_dry_run)

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
            lab["data_state"] = "authoritative_rebuilt" if authoritative_rebuild else "incremental_verified"
        elif authoritative_rebuild and clean_text(lab.get("data_state", "")) == "authoritative_rebuild_pending":
            lab["data_state"] = "authoritative_no_match"
        lab["enricher_version"] = ENRICHER_VERSION

    failure_reasons, commit_metrics = authoritative_commit_failure_reasons(
        selected_departments, labs_by_id.values(), overrides
    )
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
        print("\n[ABORT-COMMIT] 전체 권위 재구축 검증 실패")
        for reason in failure_reasons:
            print(f"  - {reason}")
        print("원본 departments.csv/labs.csv는 변경하지 않았습니다. 백업만 생성되었습니다.")
        return

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
    field_counts["actual_lab_name"] = sum(
        bool(clean_text(row.get("lab_name_kor", "")))
        and not looks_placeholder_lab_name(row.get("lab_name_kor", ""))
        for row in labs
    )
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
    lab_name_rows: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in labs:
        name = clean_text(row.get("lab_name_kor", ""))
        if name and not looks_placeholder_lab_name(name):
            lab_name_rows[name.casefold()].append(row)
    for name, group in lab_name_rows.items():
        emails = {normalize_email(row.get("email", "")) for row in group if normalize_email(row.get("email", ""))}
        if len(emails) >= 3:
            repeated_lab_names.append(
                {
                    "lab_name": clean_text(group[0].get("lab_name_kor", "")),
                    "professor_count": len(emails),
                    "departments": sorted({clean_text(row.get("department_name", "")) for row in group}),
                }
            )

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
    affiliation_guard_violations = affiliation_evidence_violations(labs)

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
            foreign_department_page_rows.append({
                "lab_id": clean_text(row.get("lab_id", "")),
                "professor_name": clean_text(row.get("professor_name", "")),
                "primary_department": clean_text(row.get("department_name", "")),
                "department_page_url": page_url,
            })

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
        "affiliation_counts": dict(affiliation_counts.most_common()),
        "affiliation_guard_violations": affiliation_guard_violations,
        "affiliation_evidence_violation_count": len(affiliation_guard_violations),
        "foreign_department_page_rows": foreign_department_page_rows,
        "foreign_department_page_count": len(foreign_department_page_rows),
        "data_state_counts": dict(Counter(clean_text(row.get("data_state", "")) or "unknown" for row in labs)),
        "duplicate_name_groups": duplicate_name_groups,
        "repeated_lab_names": repeated_lab_names,
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
    report = build_data_audit_report(departments, labs, outputs)
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

    # Full rebuild preserves exact-homepage evidence but drops card-derived data.
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
    assert rebuild_rows["B"]["lab_url"] == ""
    assert looks_placeholder_lab_name(rebuild_rows["B"]["lab_name_kor"])
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
    quarantine_unverified_affiliations([], evidence_lab)
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
    if args.test_limit is not None and args.test_limit < 1:
        parser.error("--test-limit은 1 이상이어야 합니다.")
    if args.reset_affiliations and args.clean_only:
        parser.error("--reset-affiliations는 --clean-only와 함께 사용할 수 없습니다.")
    if args.reset_affiliations and (args.department or args.test_limit is not None):
        parser.error("--reset-affiliations는 일부 학과 실행과 함께 사용할 수 없습니다. 전체 재수집에만 사용하세요.")
    if args.incremental and args.reset_affiliations:
        parser.error("--incremental과 --reset-affiliations는 함께 사용할 수 없습니다.")
    exclusive_modes = sum(bool(value) for value in (args.audit_only, args.clean_research_outputs, args.self_test))
    if exclusive_modes > 1:
        parser.error("--audit-only, --clean-research-outputs, --self-test는 동시에 사용할 수 없습니다.")
    if (args.audit_only or args.clean_research_outputs or args.self_test) and args.clean_only:
        parser.error("감사/연구실적/자체테스트 모드는 --clean-only와 함께 사용할 수 없습니다.")


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
    run_stage2(args)


if __name__ == "__main__":
    main()
