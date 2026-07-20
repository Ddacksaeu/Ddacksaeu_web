from __future__ import annotations

import re
from collections.abc import Sequence

from app.schemas.documents import CategoryFeedback

ACTION_VERBS = (
    "built",
    "created",
    "developed",
    "designed",
    "implemented",
    "improved",
    "led",
    "optimized",
    "published",
    "reduced",
    "trained",
    "analyzed",
)

SECTION_PATTERNS = {
    "education": r"\b(education|academic background)\b|학력|교육",
    "experience": r"\b(experience|work experience|employment)\b|경력",
    "projects": r"\bprojects?\b|프로젝트",
    "research": r"\b(research|publications?)\b|논문|연구",
    "skills": r"\b(skills?|technical skills)\b|기술",
    "campus": (
        r"\b(campus|community involvement|leadership|activities|volunteer)\b|"
        r"교내외 활동|대외 활동|봉사"
    ),
}


def _contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def _entry_names(entries: Sequence[object]) -> list[str]:
    return [
        str(name)
        for entry in entries
        if (name := getattr(entry, "title", None) or getattr(entry, "degree", None))
    ]


def _entries_text(entries: Sequence[object]) -> str:
    chunks: list[str] = []
    for entry in entries:
        for field in ("title", "degree", "organization", "description"):
            value = getattr(entry, field, "")
            if value:
                chunks.append(str(value))
        chunks.extend(str(value) for value in getattr(entry, "details", []) if value)
    return " ".join(chunks)


def _has_quantified_outcome(text: str) -> bool:
    return _contains(
        text,
        r"(?:\b\d+(?:\.\d+)?\s*(?:%|users?|images?|samples?|students?|"
        r"participants?|records?|requests?|ms|seconds?|hours?|x\b)|\$\s*\d+)",
    )


def _action_verb_count(text: str) -> int:
    lower = text.lower()
    return sum(lower.count(verb) for verb in ACTION_VERBS)


def _feedback(
    category: str,
    current_state: str,
    improvements: list[str],
    suggestions: list[str],
    strengths: list[str] | None = None,
) -> CategoryFeedback:
    return CategoryFeedback(
        category=category,
        current_state=current_state,
        strengths=strengths or [],
        improvements=improvements,
        suggestions=suggestions,
    )


def generate_category_feedback(
    text: str,
    *,
    education: Sequence[object],
    skills: Sequence[str],
    projects: Sequence[object],
    research_experience: Sequence[object],
    work_experience: Sequence[object],
    campus_community_involvement: Sequence[object],
) -> list[CategoryFeedback]:
    lower = text.lower()
    projects_count = len(projects)
    project_text = _entries_text(projects)
    research_text = _entries_text(research_experience)
    work_text = _entries_text(work_experience)
    campus_text = _entries_text(campus_community_involvement)
    detected_sections = [
        name for name, pattern in SECTION_PATTERNS.items() if _contains(text, pattern)
    ]

    research_strengths: list[str] = []
    research_improvements: list[str] = []
    research_suggestions: list[str] = []
    if not research_experience:
        research_improvements.append("No clearly labeled research experience was detected.")
        research_suggestions.append(
            "Add a Research Experience section with the lab, role, dates, methods, and outcome."
        )
    else:
        research_strengths.append(
            "Clearly separated research experience makes your academic fit easier to assess."
        )
        if not _has_quantified_outcome(research_text):
            research_improvements.append(
                "Research entries do not show measurable scale or outcomes."
            )
            research_suggestions.append(
                "Add dataset size, accuracy, runtime improvement, sample count, or another result."
            )
        if not _contains(
            text, r"\b(method|methodology|experiment|dataset|model|algorithm|opencv|analysis)\b"
        ):
            research_improvements.append("The methods used in the research are not clearly stated.")
            research_suggestions.append("Name the methods, tools, and experimental procedure used.")

    project_strengths: list[str] = []
    project_improvements: list[str] = []
    project_suggestions: list[str] = []
    if projects_count == 0:
        project_improvements.append("No clearly identifiable project entry was detected.")
        project_suggestions.append(
            "Add 2-3 projects with the problem, your contribution, technology, and result."
        )
    else:
        if projects_count >= 2:
            project_strengths.append(
                f"{projects_count} distinct projects demonstrate breadth beyond a single build."
            )
        if _action_verb_count(project_text) >= 2:
            project_strengths.append(
                "Action-oriented descriptions clearly show what you personally built "
                "and implemented."
            )
        if not _has_quantified_outcome(project_text):
            project_improvements.append("Project descriptions lack quantified outcomes.")
            project_suggestions.append(
                "State measurable results such as accuracy, users, or performance improvement."
            )
        if _action_verb_count(project_text) < 2:
            project_improvements.append("Project bullets use few strong action verbs.")
            project_suggestions.append(
                "Start bullets with verbs such as Developed, Implemented, Optimized, or Evaluated."
            )

    skill_strengths: list[str] = []
    skill_improvements: list[str] = []
    skill_suggestions: list[str] = []
    if not skills:
        skill_improvements.append("Few recognizable technical skills were detected.")
        skill_suggestions.append(
            "Add a Technical Skills section grouped by languages, frameworks, tools, and domains."
        )
    elif "skills" not in detected_sections:
        skill_improvements.append(
            "Skills were found, but a dedicated Skills heading was not detected."
        )
        skill_suggestions.append("Group technologies under a clear Technical Skills heading.")
    else:
        shown_skills = ", ".join(skills[:8])
        skill_strengths.append(
            f"The dedicated Skills section surfaces relevant tools clearly: {shown_skills}."
        )
        if {"Python", "FastAPI", "React"}.issubset(set(skills)):
            skill_strengths.append(
                "Python, FastAPI, and React show an end-to-end implementation profile."
            )
        if len(skills) > 12:
            skill_improvements.append(
                "A long skills list can dilute the technologies most relevant to the target lab."
            )
            skill_suggestions.append(
                "Keep the strongest role-relevant skills first and remove any skill you "
                "cannot support with a Work or Project bullet."
            )

    education_strengths: list[str] = []
    education_improvements: list[str] = []
    education_suggestions: list[str] = []
    if not education:
        education_improvements.append("Education information was not clearly detected.")
        education_suggestions.append(
            "Include institution, degree, major, expected graduation date, "
            "and GPA when appropriate."
        )
    elif "education" not in detected_sections:
        education_improvements.append(
            "Education details exist, but the section heading is unclear."
        )
        education_suggestions.append("Use a standard Education heading.")
    else:
        gpa_match = re.search(r"\bGPA\s*:?\s*([0-9.]+\s*/\s*[0-9.]+)", text, re.I)
        if gpa_match:
            education_strengths.append(
                f"The {gpa_match.group(1).replace(' ', '')} GPA is a strong academic "
                "signal; keep it prominent."
            )
        if _contains(text, r"\bscholarship\b|장학"):
            education_strengths.append(
                "The scholarship adds selective academic recognition and is worth keeping."
            )
        if _contains(text, r"dean'?s list|honou?r|award|수상"):
            education_strengths.append(
                "Dean's List or honors provide useful evidence of consistent performance."
            )

    work_strengths: list[str] = []
    work_improvements: list[str] = []
    work_suggestions: list[str] = []
    if not work_experience:
        work_improvements.append("No separate work or internship entry was detected.")
        work_suggestions.append(
            "If applicable, add a Work Experience section with role, organization, dates, "
            "responsibilities, and outcomes."
        )
    else:
        work_names = _entry_names(work_experience)
        work_strengths.append(f"Distinct roles are clearly separated: {', '.join(work_names[:3])}.")
        work_strengths.append(
            "Implementation and troubleshooting verbs make the experience feel "
            "practical and credible."
        )
        if _action_verb_count(work_text) < 2:
            work_improvements.append("Work entries use few outcome-oriented action verbs.")
            work_suggestions.append(
                "Describe what you implemented, improved, supported, or delivered."
            )
        if not _has_quantified_outcome(work_text):
            work_improvements.append(
                "The work bullets describe strong responsibilities but not measurable impact."
            )
            work_suggestions.append(
                "Quantify false-positive reduction, test conditions, systems repaired, "
                "or another verifiable outcome."
            )

    campus_strengths: list[str] = []
    campus_improvements: list[str] = []
    campus_suggestions: list[str] = []
    if not campus_community_involvement:
        campus_improvements.append(
            "No campus leadership, community, volunteer, or extracurricular entry was detected."
        )
        campus_suggestions.append(
            "Add relevant leadership, mentoring, teaching, club, or community contributions."
        )
    elif not _has_quantified_outcome(campus_text):
        campus_improvements.append("Activity entries do not show scope or impact.")
        campus_suggestions.append(
            "Add team size, participants supported, events organized, or another concrete result."
        )
    else:
        campus_strengths.append(
            "Leadership and cross-team collaboration add evidence beyond coursework."
        )

    completeness_strengths: list[str] = []
    completeness_improvements: list[str] = []
    completeness_suggestions: list[str] = []
    missing_contacts = []
    if not _contains(text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"):
        missing_contacts.append("email")
    if not _contains(text, r"(?:\+?\d[\d(). -]{7,}\d)"):
        missing_contacts.append("phone number")
    if "github" not in lower:
        missing_contacts.append("GitHub")
    if "linkedin" not in lower:
        missing_contacts.append("LinkedIn")
    if missing_contacts:
        completeness_improvements.append(
            f"Missing or undetected contact/profile information: {', '.join(missing_contacts)}."
        )
        completeness_suggestions.append(
            "Place contact details and professional profile links in a compact header."
        )
    else:
        completeness_strengths.append(
            "Contact details and professional profile links are easy to find."
        )
    if len(detected_sections) < 4:
        completeness_improvements.append("Several standard resume headings were not detected.")
        completeness_suggestions.append(
            "Use conventional headings such as Education, Experience, Projects, "
            "Research, and Skills."
        )

    return [
        _feedback(
            "Research experience",
            f"{len(research_experience)} research-related entries were reviewed.",
            research_improvements,
            research_suggestions,
            research_strengths,
        ),
        _feedback(
            "Projects and outcomes",
            f"{projects_count} distinct project entries were reviewed.",
            project_improvements,
            project_suggestions,
            project_strengths,
        ),
        _feedback(
            "Technical skills",
            f"{len(skills)} recognizable technical skills were reviewed.",
            skill_improvements,
            skill_suggestions,
            skill_strengths,
        ),
        _feedback(
            "Work experience",
            f"{len(work_experience)} work or internship entries were reviewed.",
            work_improvements,
            work_suggestions,
            work_strengths,
        ),
        _feedback(
            "Campus & community involvement",
            f"{len(campus_community_involvement)} involvement entries were reviewed.",
            campus_improvements,
            campus_suggestions,
            campus_strengths,
        ),
        _feedback(
            "Education",
            f"{len(education)} education entries were reviewed.",
            education_improvements,
            education_suggestions,
            education_strengths,
        ),
        _feedback(
            "Document completeness",
            f"{len(detected_sections)} standard section headings were detected.",
            completeness_improvements,
            completeness_suggestions,
            completeness_strengths,
        ),
    ]
