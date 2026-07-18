from __future__ import annotations

import json

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import UserProfile
from app.schemas.email import EmailDraftRequest, EmailDraftResponse, GeneratedEmail
from app.services.lab_search import LabSearchService


class EmailDraftingError(Exception):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


def create_email_draft(
    session: Session,
    request: EmailDraftRequest,
    *,
    api_key: str | None,
    model: str,
    timeout_seconds: float,
) -> EmailDraftResponse:
    lab = LabSearchService(session).get_detail(request.lab_id)
    if lab is None:
        raise EmailDraftingError("lab_not_found", 404, "The selected lab was not found")

    profile = session.get(UserProfile, request.user_id)
    if profile is None:
        raise EmailDraftingError("profile_not_found", 404, "The user profile was not found")

    if api_key:
        generated = _generate_with_openai(
            lab.model_dump(mode="json"),
            {
                "name": profile.name,
                "affiliation": profile.affiliation,
                "status": profile.status,
                "program": profile.program,
                "interests": profile.interests_json,
                "skills": profile.skills_json,
                "methodologies": profile.methodologies_json,
                "projects": profile.projects_json,
            },
            request,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        mode = "ai"
        used_model: str | None = model
    else:
        generated = _generate_demo(lab, profile, request)
        mode = "demo"
        used_model = None

    return EmailDraftResponse(
        lab_id=lab.id,
        subject=generated.subject,
        body=generated.body,
        personalization_notes=generated.personalization_notes,
        generation_mode=mode,
        model=used_model,
    )


def _generate_with_openai(
    lab: dict,
    profile: dict,
    request: EmailDraftRequest,
    *,
    api_key: str,
    model: str,
    timeout_seconds: float,
) -> GeneratedEmail:
    language = "Korean" if request.language == "ko" else "English"
    instructions = f"""
Write a natural, personal academic contact email in {language}.
The sender will review and send it manually. Use only facts present in the supplied lab and
profile data. Never invent publications, achievements, research experience, or admissions
availability. Keep the tone {request.tone}, the length {request.length}, and the purpose
{request.purpose}. Mention one concrete point of fit when the data supports it. Avoid generic
AI-sounding praise, exaggerated claims, and repetitive phrasing. Return a subject, complete
email body, and short notes identifying which facts personalized the draft.
""".strip()
    payload = {
        "lab": lab,
        "profile": profile,
        "additional_context": request.additional_context,
    }
    try:
        client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format=GeneratedEmail,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("The model did not return a parsed email draft")
        return parsed
    except Exception as exc:
        raise EmailDraftingError(
            "email_generation_failed", 502, "The AI email draft could not be generated"
        ) from exc


def _generate_demo(lab, profile: UserProfile, request: EmailDraftRequest) -> GeneratedEmail:
    interests = [item for item in profile.interests_json if item]
    skills = [item for item in profile.skills_json if item]
    fit = next((item for item in interests if item.isascii()), lab.field)
    skill_sentence = ""
    if skills:
        skill_sentence = f" I have experience with {', '.join(skills[:3])}."

    if request.language == "ko":
        subject = f"[{request.purpose.replace('_', ' ')}] {lab.name} 연구 관련 문의드립니다"
        body = (
            f"{lab.professor_name} 교수님께,\n\n"
            f"안녕하세요. 저는 {profile.affiliation}의 {profile.name}입니다. "
            f"현재 {profile.program} 과정에서 {fit} 분야에 관심을 두고 있습니다.\n\n"
            f"{lab.name}의 {lab.field} 연구와 제 관심 분야가 맞닿아 있어 연락드렸습니다. "
            f"특히 연구실 소개에서 확인한 {lab.summary or lab.field} 내용이 인상 깊었습니다.\n\n"
            "제 CV를 첨부드리오니, 대학원 연구 참여 가능성과 준비해야 할 사항에 대해 "
            "간단히 조언을 구할 수 있을지 여쭙습니다.\n\n"
            "읽어주셔서 감사합니다.\n"
            f"{profile.name} 드림"
        )
    else:
        subject = f"Prospective student inquiry — {lab.name}"
        body = (
            f"Dear Professor {lab.professor_name},\n\n"
            f"My name is {profile.name}, and I am currently at {profile.affiliation}. "
            f"I am studying in {profile.program} with a strong interest in "
            f"{fit}.{skill_sentence}\n\n"
            f"I am reaching out because your work at {lab.name} in {lab.field} closely aligns "
            "with the direction I hope to pursue. I was particularly interested in the lab's "
            f"focus described as: {lab.summary or lab.field}.\n\n"
            "I would be grateful if you could let me know whether there may be an opportunity "
            "to pursue graduate research in your group and what preparation you would recommend. "
            "I have attached my CV for context.\n\n"
            "Thank you for your time and consideration.\n\n"
            f"Best regards,\n{profile.name}"
        )
    if request.additional_context.strip():
        body += f"\n\nNote for revision: {request.additional_context.strip()}"
    return GeneratedEmail(
        subject=subject,
        body=body,
        personalization_notes=[
            f"Lab: {lab.name} ({lab.field})",
            f"Profile: {profile.name}, {profile.affiliation}",
            f"Shared interest: {fit}",
        ],
    )
