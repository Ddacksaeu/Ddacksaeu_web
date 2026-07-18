from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("postech_stage2_enricher.py")
spec = importlib.util.spec_from_file_location("postech_stage2_enricher", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def test_indexes_reject_duplicate_email_and_name() -> None:
    labs = {
        "L1": {"lab_id": "L1", "email": "same@postech.ac.kr", "professor_name": "김철수"},
        "L2": {"lab_id": "L2", "email": "same@postech.ac.kr", "professor_name": "김철수"},
        "L3": {"lab_id": "L3", "email": "unique@postech.ac.kr", "professor_name": "박영희"},
    }
    by_email, unique_names, known_names, duplicate_emails = m.build_indexes(labs)
    assert "same@postech.ac.kr" not in by_email
    assert by_email["unique@postech.ac.kr"] == "L3"
    assert m.normalize_name("김철수") not in unique_names
    assert unique_names[m.normalize_name("박영희")] == "L3"
    assert "same@postech.ac.kr" in duplicate_emails
    assert m.normalize_name("김철수") in known_names


def test_department_name_matching_requires_global_uniqueness() -> None:
    labs = {
        "L1": {
            "lab_id": "L1",
            "department_id": "D1",
            "primary_department_id": "D1",
            "department_name": "수학과",
            "affiliated_programs": "수학과",
            "professor_name": "김철수",
        },
        "L2": {
            "lab_id": "L2",
            "department_id": "D2",
            "primary_department_id": "D2",
            "department_name": "물리학과",
            "affiliated_programs": "물리학과",
            "professor_name": "김철수",
        },
    }
    _, unique_names, _, _ = m.build_indexes(labs)
    index = m.build_department_name_index(
        labs,
        {"department_id": "D1", "department_name_kor": "수학과"},
        unique_names,
    )
    assert index == {}


def test_card_email_match_and_extraction() -> None:
    html = """
    <html><body>
      <article class='faculty-card'>
        <h3>이기예(Qirui Li)</h3>
        <div>연구분야: 정수론 | 산술기하학</div>
        <div>Office 수리과학관 219호</div>
        <div>Tel +82-54-279-2058</div>
        <a href='mailto:qiruili@postech.ac.kr'>qiruili@postech.ac.kr</a>
        <a href='http://qirui.li'>연구실 홈페이지</a>
        <img src='/images/qirui.jpg' alt='Qirui Li'>
      </article>
    </body></html>
    """
    result = m.PageResult("https://math.postech.ac.kr/faculty", html, "fixture")
    lab = {
        "lab_id": "L1",
        "department_name": "수학과",
        "professor_name": "",
        "email": "qiruili@postech.ac.kr",
        "professor_profile_url": "",
    }
    matches = m.build_page_matches(
        result,
        {},
        {"L1": lab},
        {"qiruili@postech.ac.kr": "L1"},
        {},
        set(),
    )
    assert len(matches) == 1
    update = m.extract_card_data(matches[0].block, result.url, lab, {})
    assert update["professor_name"] == "이기예"
    assert "정수론" in update["primary_field"]
    assert update["location"] == "수리과학관 219호"
    assert update["phone"] == "054-279-2058"
    assert update["lab_url"] == "http://qirui.li/"
    assert update["lab_url_status"] == "verified_card"


def test_summary_trims_publication_tail() -> None:
    raw = (
        "본 연구에서는 새로운 촉매 반응을 개발하고 다양한 기질에서 높은 선택성을 확인하였다. "
        "또한 계산화학 분석을 통해 반응 중간체와 선택성의 기원을 규명하였다. "
        "본 연구 결과는 2026년 국제학술지에 게재되었다."
    )
    cleaned = m.clean_summary_value(raw)
    assert "개발" in cleaned
    assert "규명" in cleaned
    assert "게재" not in cleaned


def test_discovery_follows_profile_and_pagination_links() -> None:
    faculty_url = "https://dept.postech.ac.kr/faculty"
    page2_url = "https://dept.postech.ac.kr/faculty?page=2"
    detail_url = "https://dept.postech.ac.kr/faculty?wr_id=13"

    pages = {
        faculty_url: """
            <html><body>
              <h1>Faculty</h1>
              <div>Qirui Li qiruili@postech.ac.kr</div>
              <div>Valentin Buciumas buciumas@postech.ac.kr</div>
              <a href='/faculty?page=2'>2</a>
              <a href='/faculty?wr_id=13'>Qirui Li</a>
              <a href='https://news.postech.ac.kr/faculty'>Faculty News</a>
            </body></html>
        """,
        page2_url: "<html><body><h1>Faculty</h1><div>Another Professor</div></body></html>",
        detail_url: "<html><body><h1>Qirui Li</h1><div>qiruili@postech.ac.kr</div></body></html>",
    }

    class FakeClient:
        def fetch(self, url: str, force_browser: bool = False):
            normalized = m.normalize_url(url)
            if normalized not in pages:
                raise RuntimeError("fixture URL not found")
            return m.PageResult(normalized, pages[normalized], "fixture")

    with tempfile.TemporaryDirectory() as tmp:
        paths = m.RuntimePaths.from_args(Path(tmp), Path(tmp) / "site_overrides.json")
        results = m.discover_department_pages(
            FakeClient(),
            {
                "department_id": "D1",
                "department_name_kor": "테스트학과",
                "homepage_url": faculty_url,
            },
            {"faculty_urls": [faculty_url], "allowed_hosts": ["dept.postech.ac.kr"]},
            max_pages=5,
            max_depth=2,
            known_names={m.normalize_name("Qirui Li"), m.normalize_name("Valentin Buciumas")},
            paths=paths,
            save_raw=False,
        )
    urls = {result.url for result in results}
    assert faculty_url in urls
    assert page2_url in urls
    assert detail_url in urls
    assert "https://news.postech.ac.kr/faculty" not in urls


def test_schema_retains_base_and_stage2_fields() -> None:
    fields = m.ensure_fields(
        ["lab_id", "professor_name"],
        m.BASE_LAB_FIELDS + m.STAGE2_LAB_FIELDS,
    )
    assert "keyword_source" in fields
    assert "lab_url_status" in fields
    assert "primary_department_id" in fields



def test_summary_rejects_recruiting_and_paper_announcement() -> None:
    assert m.clean_summary_value(
        "Open positions Graduate students and post-doc positions are open. "
        "Interested candidates are welcome to contact Prof. Lee."
    ) == ""
    assert m.clean_summary_value(
        "1 paper accepted: FOCUS & RePAIR, a token-level guidance framework."
    ) == ""


def test_clean_row_restores_placeholder_and_compacts_provenance() -> None:
    row = {
        "lab_id": "L1",
        "department_id": "D1",
        "primary_department_id": "D1",
        "department_name": "수학과",
        "department_name_raw": "수학과",
        "professor_name": "김철수",
        "lab_name_kor": "",
        "email": "kim@postech.ac.kr",
        "phone": "",
        "location": "",
        "primary_field": "",
        "keywords": "",
        "research_summary": "",
        "profile_image_url": "",
        "lab_url": "https://kimlab.example.com/",
        "lab_url_status": "verified_homepage",
        "source_url": "https://www.postech.ac.kr/researcher?id=1",
        "professor_profile_url": "https://www.postech.ac.kr/researcher?id=1",
        "department_page_url": "https://math.postech.ac.kr/faculty",
        "enrichment_source_urls": (
            "https://math.postech.ac.kr/faculty;"
            "https://math.postech.ac.kr/news/view?id=3;"
            "https://facultyapplication.postech.ac.kr/invitation/test/"
        ),
        "affiliated_programs": "수학과",
        "recruiting_status": "unknown",
    }
    report = m.CleanReport()
    cleaned = m.clean_existing_lab_row(row, report)
    assert cleaned["lab_name_kor"] == "김철수 교수 연구실"
    assert "facultyapplication" not in cleaned["enrichment_source_urls"]
    assert "/news/" not in cleaned["enrichment_source_urls"]
    assert len(m.split_multi(cleaned["enrichment_source_urls"])) <= m.MAX_ENRICHMENT_SOURCE_URLS


def test_duplicate_portrait_is_removed_for_two_professors() -> None:
    rows = [
        {
            "lab_id": "L1",
            "researcher_id": "R1",
            "email": "a@postech.ac.kr",
            "department_name": "테스트학과",
            "profile_image_url": "https://dept.postech.ac.kr/a.png",
        },
        {
            "lab_id": "L2",
            "researcher_id": "R2",
            "email": "b@postech.ac.kr",
            "department_name": "테스트학과",
            "profile_image_url": "https://dept.postech.ac.kr/a.png",
        },
    ]
    report = m.CleanReport()
    m.remove_duplicate_profile_images(rows, report)
    assert rows[0]["profile_image_url"] == ""
    assert rows[1]["profile_image_url"] == ""


def test_homepage_professor_name_recovery() -> None:
    soup = m.BeautifulSoup(
        "<html><head><title>Valentin Buciumas | Homepage</title></head>"
        "<body><h1>Valentin Buciumas</h1></body></html>",
        "lxml",
    )
    name = m.extract_homepage_professor_name(
        soup,
        {
            "professor_name": "",
            "department_name": "수학과",
            "email": "buciumas@postech.ac.kr",
        },
    )
    assert name == "Valentin Buciumas"

def run_all() -> None:
    tests = [
        test_indexes_reject_duplicate_email_and_name,
        test_department_name_matching_requires_global_uniqueness,
        test_card_email_match_and_extraction,
        test_summary_trims_publication_tail,
        test_discovery_follows_profile_and_pagination_links,
        test_schema_retains_base_and_stage2_fields,
        test_summary_rejects_recruiting_and_paper_announcement,
        test_clean_row_restores_placeholder_and_compacts_provenance,
        test_duplicate_portrait_is_removed_for_two_professors,
        test_homepage_professor_name_recovery,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print(f"All {len(tests)} tests passed. Version={m.ENRICHER_VERSION}")


if __name__ == "__main__":
    run_all()
