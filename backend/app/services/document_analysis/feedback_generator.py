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


def _feedback(
    category: str, current_state: str, improvements: list[str], suggestions: list[str]
) -> CategoryFeedback:
    return CategoryFeedback(
        category=category,
        current_state=current_state,
        improvements=improvements,
        suggestions=suggestions,
    )


def generate_category_feedback(
    text: str,
    *,
    education: Sequence[object],
    skills: Sequence[str],
    projects_count: int,
    research_experience: Sequence[object],
    work_experience: Sequence[object],
    campus_community_involvement: Sequence[object],
) -> list[CategoryFeedback]:
    lower = text.lower()
    has_number = _contains(text, r"\b\d+(?:\.\d+)?%?\b")
    action_verb_count = sum(lower.count(verb) for verb in ACTION_VERBS)
    detected_sections = [
        name for name, pattern in SECTION_PATTERNS.items() if _contains(text, pattern)
    ]

    research_improvements: list[str] = []
    research_suggestions: list[str] = []
    if not research_experience:
        research_improvements.append("No clearly labeled research experience was detected.")
        research_suggestions.append(
            "Add a Research Experience section with the lab, role, dates, methods, and outcome."
        )
    else:
        if not has_number:
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

    project_improvements: list[str] = []
    project_suggestions: list[str] = []
    if projects_count == 0:
        project_improvements.append("No clearly identifiable project entry was detected.")
        project_suggestions.append(
            "Add 2-3 projects with the problem, your contribution, technology, and result."
        )
    else:
        if not has_number:
            project_improvements.append("Project descriptions lack quantified outcomes.")
            project_suggestions.append(
                "State measurable results such as accuracy, users, or performance improvement."
            )
        if action_verb_count < 2:
            project_improvements.append("Project bullets use few strong action verbs.")
            project_suggestions.append(
                "Start bullets with verbs such as Developed, Implemented, Optimized, or Evaluated."
            )

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

    work_improvements: list[str] = []
    work_suggestions: list[str] = []
    if not work_experience:
        work_improvements.append("No separate work or internship entry was detected.")
        work_suggestions.append(
            "If applicable, add a Work Experience section with role, organization, dates, "
            "responsibilities, and outcomes."
        )
    elif action_verb_count < 2:
        work_improvements.append("Work entries use few outcome-oriented action verbs.")
        work_suggestions.append(
            "Describe what you implemented, improved, supported, or delivered."
        )

    campus_improvements: list[str] = []
    campus_suggestions: list[str] = []
    if not campus_community_involvement:
        campus_improvements.append(
            "No campus leadership, community, volunteer, or extracurricular entry was detected."
        )
        campus_suggestions.append(
            "Add relevant leadership, mentoring, teaching, club, or community contributions."
        )
    elif not has_number:
        campus_improvements.append("Activity entries do not show scope or impact.")
        campus_suggestions.append(
            "Add team size, participants supported, events organized, or another concrete result."
        )

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
    if len(detected_sections) < 4:
        completeness_improvements.append("Several standard resume headings were not detected.")
        completeness_suggestions.append(
            "Use conventional headings such as Education, Experience, Projects, "
            "Research, and Skills."
        )

    return [
        _feedback(
            "Research experience",
            f"{len(research_experience)} research-related entries were detected.",
            research_improvements,
            research_suggestions,
        ),
        _feedback(
            "Projects and outcomes",
            f"{projects_count} project-related entries were detected.",
            project_improvements,
            project_suggestions,
        ),
        _feedback(
            "Technical skills",
            f"{len(skills)} recognizable technical skills were detected.",
            skill_improvements,
            skill_suggestions,
        ),
        _feedback(
            "Work experience",
            f"{len(work_experience)} work or internship entries were detected.",
            work_improvements,
            work_suggestions,
        ),
        _feedback(
            "Campus & community involvement",
            f"{len(campus_community_involvement)} involvement entries were detected.",
            campus_improvements,
            campus_suggestions,
        ),
        _feedback(
            "Education",
            f"{len(education)} education entries were detected.",
            education_improvements,
            education_suggestions,
        ),
        _feedback(
            "Document completeness",
            f"{len(detected_sections)} standard section headings were detected.",
            completeness_improvements,
            completeness_suggestions,
        ),
    ]
