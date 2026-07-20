# Devpost Submission Draft

## Project Description

Ddacksaeu helps prospective graduate students discover research laboratories,
compare their interests with available lab evidence, and organize application
work in one place. Users can search labs and professors, upload a PDF, DOCX,
or TXT CV for deterministic local analysis, review explainable lab
recommendations, save labs, prepare an outreach draft, and track admission
dates. The app uses a Next.js frontend and same-origin BFF with a FastAPI
backend; CV analysis and recommendations do not call an OpenAI API.

## Codex and GPT-5.6 Usage - Short Version

We used Codex throughout Dacksaeu's development as a collaborator for more
than initial scaffolding. It helped us inspect the existing frontend and
FastAPI backend, implement and connect API-backed CV analysis and explainable
lab recommendations, review the same-origin BFF that keeps backend credentials
out of browser code, and diagnose integration issues around uploads, session
handling, and API errors. Codex also assisted with targeted tests, the
release-smoke workflow, and submission documentation.

GPT-5.6 was used inside Codex for those development tasks: repository analysis,
implementation suggestions, debugging, test interpretation, and documentation
drafting. It was not used as a direct product feature. The shipped CV-analysis
and recommendation flows do not call GPT-5.6 or an OpenAI API; they use local,
deterministic parsing, keyword rules, scikit-learn TF-IDF, and rule-based
explanations. Our team set the product decisions, reviewed and revised the
generated changes, ran validation, checked real user flows, and made the final
submission decisions. We did not submit AI-generated output without review.

## Suggested Devpost Gallery

![Ddacksaeu product overview](assets/devpost-product-overview.png)

This overlay-free laboratory discovery screen is suitable for the Devpost
gallery. It shows the research-topic browsing experience and
university-discovery section without user credentials or development controls.
