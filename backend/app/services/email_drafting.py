from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentAnalysis, UploadedDocument, UserProfile
from app.schemas.email import (
    EmailDraftRequest,
    EmailDraftResponse,
    EmailReviewIssue,
    EmailReviewRequest,
    EmailReviewResponse,
    GeneratedEmail,
)
from app.services.lab_search import LabSearchService
from app.services.recommendation_similarity import tokens


@dataclass(frozen=True)
class CandidateEvidence:
    interests: list[str]
    skills: list[str]
    project_name: str
    project_detail: str


class EmailDraftingError(Exception):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


def _context(session: Session, lab_id: str, user_id: str):
    lab = LabSearchService(session).get_detail(lab_id)
    if lab is None:
        raise EmailDraftingError("lab_not_found", 404, "The selected lab was not found")
    profile = session.get(UserProfile, user_id)
    if profile is None:
        raise EmailDraftingError("profile_not_found", 404, "The user profile was not found")
    analysis = session.scalar(
        select(DocumentAnalysis)
        .join(UploadedDocument)
        .where(
            UploadedDocument.user_id == user_id,
            DocumentAnalysis.status == "completed",
        )
        .order_by(DocumentAnalysis.created_at.desc(), DocumentAnalysis.id.asc())
    )
    structured = analysis.structured_analysis_json if analysis else {}
    projects = list(analysis.projects_json) if analysis else []
    first_project = projects[0] if projects else {}
    project_details = first_project.get("details", [])
    project_detail = (
        str(project_details[0])
        if isinstance(project_details, list) and project_details
        else str(first_project.get("description", ""))
    )
    evidence = CandidateEvidence(
        interests=list(structured.get("research_interests", []))
        or list(profile.interests_json),
        skills=list(analysis.skills_json) if analysis else list(profile.skills_json),
        project_name=str(first_project.get("name", "")),
        project_detail=project_detail,
    )
    return lab, profile, evidence


def create_email_draft(
    session: Session,
    request: EmailDraftRequest,
    user_id: str,
    **_: object,
) -> EmailDraftResponse:
    lab, profile, evidence = _context(session, request.lab_id, user_id)
    generated = _generate_local(lab, profile, evidence, request)
    return EmailDraftResponse(
        lab_id=lab.id,
        subject=generated.subject,
        body=generated.body,
        personalization_notes=generated.personalization_notes,
        generation_mode="local_rule_based",
        model=None,
    )


def _generate_local(
    lab,
    profile: UserProfile,
    evidence: CandidateEvidence,
    request: EmailDraftRequest,
) -> GeneratedEmail:
    interests = [item for item in evidence.interests if item]
    skills = [item for item in evidence.skills if item]
    fit = interests[0] if interests else lab.field
    summary = (lab.summary or lab.field).strip()
    candidate_text = " ".join(
        [*interests, *skills, evidence.project_name, evidence.project_detail]
    )
    candidate_tokens = tokens(candidate_text)
    papers = sorted(
        lab.papers,
        key=lambda paper: (
            -len(
                candidate_tokens
                & tokens(
                    " ".join(
                        filter(
                            None,
                            [
                                paper.title,
                                paper.summary,
                                paper.abstract,
                                *paper.keywords,
                            ],
                        )
                    )
                )
            ),
            -paper.published_year,
            paper.title,
        ),
    )
    paper = papers[0] if papers else None
    overlap = sorted(
        candidate_tokens
        & tokens(
            " ".join(
                [lab.field, lab.summary or "", *lab.keywords]
                + ([paper.title, *paper.keywords] if paper else [])
            )
        )
    )
    shared_focus = ", ".join(overlap[:4]) or fit
    project_en = (
        f"In my project '{evidence.project_name}', I {evidence.project_detail.rstrip('.')}"
        f". This work gave me practical experience with {', '.join(skills[:4])}."
        if evidence.project_name and evidence.project_detail
        else f"My relevant technical background includes {', '.join(skills[:4])}."
        if skills
        else "My CV provides further context on my research preparation."
    )
    project_ko = (
        f"CV에 기재한 '{evidence.project_name}' 프로젝트에서 "
        f"{evidence.project_detail.rstrip('.')} 업무를 수행했습니다. "
        f"이 과정에서 {', '.join(skills[:4])}을 활용했습니다."
        if evidence.project_name and evidence.project_detail
        else f"{', '.join(skills[:4])} 관련 기술 경험을 갖고 있습니다."
        if skills
        else "구체적인 연구 준비 경험은 첨부한 CV에 정리했습니다."
    )
    paper_en = (
        f"I was particularly interested in your {paper.published_year} publication "
        f"\"{paper.title}\". The topic stood out because it intersects with my background "
        f"in {shared_focus}."
        if paper
        else f"I was particularly interested in the lab's public research focus on {summary}."
    )
    paper_ko = (
        f"특히 공개 연구 실적 중 {paper.published_year}년 논문 「{paper.title}」을 관심 있게 "
        f"보았습니다. 해당 주제는 제가 경험한 {shared_focus}와 맞닿아 있다고 생각했습니다."
        if paper
        else f"연구실 공개 소개에서 확인한 '{summary}' 연구 방향을 관심 있게 보았습니다."
    )
    homepage_en = (
        "I also reviewed the lab homepage to understand the group's broader research direction."
        if lab.homepage_url
        else "I reviewed the available public lab profile to understand the group's direction."
    )
    homepage_ko = (
        "또한 연구실 홈페이지를 확인하며 연구 그룹의 전반적인 방향을 살펴보았습니다."
        if lab.homepage_url
        else "공개된 연구실 소개를 통해 연구 그룹의 전반적인 방향을 살펴보았습니다."
    )

    if request.language == "ko":
        subject = f"[{request.purpose.replace('_', ' ')}] {lab.name} 연구 참여 문의드립니다"
        body = (
            f"{lab.professor_name} 교수님께,\n\n"
            f"안녕하세요. 저는 {profile.affiliation}의 {profile.name}입니다. "
            f"현재 {profile.program} 과정에서 {fit} 분야를 중심으로 대학원 연구를 준비하고 "
            "있습니다.\n\n"
            f"{homepage_ko} {paper_ko}\n\n"
            f"{project_ko} 이러한 경험을 {lab.name}의 {lab.field} 연구에서 더 발전시키고, "
            "실험 설계와 구현에 실질적으로 기여하고 싶습니다.\n\n"
            "현재 대학원생 또는 연구 참여 기회가 있는지, 그리고 지원 전에 보완하면 좋을 "
            "연구 역량이나 읽어야 할 자료가 있는지 여쭙고 싶습니다. 검토에 참고하실 수 있도록 "
            "CV를 첨부드립니다.\n\n"
            "읽어주셔서 감사합니다.\n"
            f"{profile.name} 드림"
        )
    else:
        subject = f"Prospective student inquiry - {lab.name}"
        body = (
            f"Dear Professor {lab.professor_name},\n\n"
            f"My name is {profile.name}, and I am currently at {profile.affiliation}. "
            f"I am studying in {profile.program} and preparing for graduate research in {fit}.\n\n"
            f"{homepage_en} {paper_en}\n\n"
            f"{project_en} I would like to build on this experience through the {lab.field} "
            f"research at {lab.name} and contribute to careful implementation "
            "and experimentation.\n\n"
            "Could you please let me know whether you anticipate opportunities for graduate or "
            "research participation, and which skills or readings you would recommend I strengthen "
            "before applying? I have attached my CV for context.\n\n"
            "Thank you for your time and consideration.\n\n"
            f"Best regards,\n{profile.name}"
        )
    if request.additional_context.strip():
        body += f"\n\nAdditional context to incorporate: {request.additional_context.strip()}"
    return GeneratedEmail(
        subject=subject,
        body=body,
        personalization_notes=[
            f"Lab: {lab.name} ({lab.field})",
            f"Profile: {profile.name}, {profile.affiliation}",
            f"Shared interest: {fit}",
            *(
                [f"Recent publication: {paper.title} ({paper.published_year})"]
                if paper
                else []
            ),
            *([f"Lab homepage: {lab.homepage_url}"] if lab.homepage_url else []),
            *(
                [f"CV project evidence: {evidence.project_name}"]
                if evidence.project_name
                else []
            ),
        ],
    )


COMMON_ENGLISH_CORRECTIONS = {
    "adress": "address",
    "alot": "a lot",
    "definately": "definitely",
    "occured": "occurred",
    "professer": "professor",
    "recieve": "receive",
    "seperate": "separate",
    "wich": "which",
}
COMMON_KOREAN_CORRECTIONS = {
    "되요": "돼요",
    "안되": "안 돼",
    "할수": "할 수",
    "관심있": "관심 있",
    "연락 드립니다": "연락드립니다",
}


def _mechanical_review(text: str, language: str) -> tuple[str, list[EmailReviewIssue]]:
    reviewed = text
    issues: list[EmailReviewIssue] = []
    corrections = COMMON_KOREAN_CORRECTIONS if language == "ko" else COMMON_ENGLISH_CORRECTIONS
    for wrong, right in corrections.items():
        pattern = re.compile(rf"(?<!\w){re.escape(wrong)}(?!\w)", re.IGNORECASE)
        if pattern.search(reviewed):
            issues.append(
                EmailReviewIssue(
                    category="spelling",
                    severity="warning",
                    message=f"Possible spelling or spacing issue: '{wrong}'.",
                    suggestion=f"Consider '{right}'.",
                )
            )
            reviewed = pattern.sub(right, reviewed)
    repeated = re.search(r"\b([A-Za-z]{2,})\s+\1\b", reviewed, re.IGNORECASE)
    if repeated:
        issues.append(
            EmailReviewIssue(
                category="spelling",
                severity="warning",
                message=f"The word '{repeated.group(1)}' is repeated.",
                suggestion="Remove the duplicate word.",
            )
        )
        reviewed = re.sub(
            rf"\b({re.escape(repeated.group(1))})\s+\1\b", r"\1", reviewed, flags=re.I
        )
    if re.search(r"[ \t]{2,}", reviewed):
        issues.append(
            EmailReviewIssue(
                category="spelling",
                severity="info",
                message="Repeated spaces were detected.",
                suggestion="Use single spaces within sentences.",
            )
        )
        reviewed = re.sub(r"[ \t]{2,}", " ", reviewed)
    reviewed = re.sub(r"\s+([,.;!?])", r"\1", reviewed)
    return reviewed, issues


def review_email(
    session: Session, request: EmailReviewRequest, user_id: str
) -> EmailReviewResponse:
    lab, _profile, _evidence = _context(session, request.lab_id, user_id)
    reviewed_subject, subject_issues = _mechanical_review(request.subject.strip(), request.language)
    reviewed_body, issues = _mechanical_review(request.body.strip(), request.language)
    issues = [*subject_issues, *issues]
    body_lower = reviewed_body.casefold()

    professor_tokens = [token.casefold() for token in lab.professor_name.split() if len(token) > 1]
    has_professor = any(token in body_lower for token in professor_tokens)
    if not has_professor:
        issues.append(
            EmailReviewIssue(
                category="professor_fit",
                severity="warning",
                message="The selected professor is not clearly addressed by name.",
                suggestion=f"Address Professor {lab.professor_name} directly in the greeting.",
            )
        )

    fit_terms = [
        lab.name,
        lab.field,
        *lab.keywords,
        *(paper.title for paper in lab.papers[:3]),
    ]
    mentioned = [term for term in fit_terms if term and term.casefold() in body_lower]
    if not mentioned:
        issues.append(
            EmailReviewIssue(
                category="professor_fit",
                severity="warning",
                message="The message does not mention the lab's research by name or keyword.",
                suggestion=(
                    f"Connect your experience to {lab.field} or a verified "
                    f"{lab.name} topic."
                ),
            )
        )
    elif len(mentioned) == 1:
        issues.append(
            EmailReviewIssue(
                category="professor_fit",
                severity="info",
                message=f"One lab-specific reference was found: {mentioned[0]}.",
                suggestion=(
                    "Add one concrete sentence explaining how your experience "
                    "relates to it."
                ),
            )
        )

    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n\s*\n", reviewed_body) if paragraph.strip()
    ]
    if len(paragraphs) < 3:
        issues.append(
            EmailReviewIssue(
                category="flow",
                severity="warning",
                message=(
                    "The message has few paragraph breaks, so the purpose is "
                    "difficult to scan."
                ),
                suggestion="Separate the introduction, research fit, request, and closing.",
            )
        )
    if any(len(paragraph) > 700 for paragraph in paragraphs):
        issues.append(
            EmailReviewIssue(
                category="flow",
                severity="warning",
                message="At least one paragraph is very long.",
                suggestion="Split long paragraphs and keep one main point in each paragraph.",
            )
        )
    if len(reviewed_body) > 3500:
        issues.append(
            EmailReviewIssue(
                category="flow",
                severity="warning",
                message="The email may be too long for a first contact.",
                suggestion=(
                    "Keep the first message focused on fit, evidence, "
                    "and one clear request."
                ),
            )
        )
    request_patterns = (
        r"\b(could|would|please|opportunity|available|meeting|question)\b"
        if request.language == "en"
        else r"문의|여쭙|가능|부탁|면담|질문"
    )
    if not re.search(request_patterns, reviewed_body, re.IGNORECASE):
        issues.append(
            EmailReviewIssue(
                category="flow",
                severity="warning",
                message="A clear request or next step was not detected.",
                suggestion="End with one specific, respectful question or requested next step.",
            )
        )

    warning_count = sum(issue.severity == "warning" for issue in issues)
    info_count = len(issues) - warning_count
    score = max(0, 100 - warning_count * 12 - info_count * 4)
    summary = (
        "The draft is clear and personalized; only minor review points remain."
        if score >= 85
        else "The draft is usable, but review the highlighted flow and personalization points."
        if score >= 65
        else "Revise the highlighted issues before contacting the professor."
    )
    return EmailReviewResponse(
        score=score,
        summary=summary,
        issues=issues,
        reviewed_subject=reviewed_subject,
        reviewed_body=reviewed_body,
    )
