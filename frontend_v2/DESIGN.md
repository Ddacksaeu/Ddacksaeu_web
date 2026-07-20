# Graduate Contact Assistant — Design System

## 0. Research log

- **LinkedIn Jobs:** 검색어·위치 뒤에 날짜, 회사, 경력, 고용 형태 필터를 단계적으로 적용하고 적용 중인 조건과 결과 수를 명확히 보여주는 방식을 참고한다.
- **RocketPunch Jobs:** 직군·숙련도·기업 규모·근무 방식 필터, 정렬, 카드형 목록이 한 흐름에 연결되는 패턴을 연구 분야·지역·대학·학위 과정 필터와 랩 카드로 번역한다.
- **Toss-like craft:** plain English, 넉넉한 여백, 흰 배경, 한 화면의 단일 주요 행동과 절제된 파란 포인트를 차용한다. 브랜드 자산·문구·고유 컴포넌트는 복제하지 않는다.
- **Decision:** 어두운 SaaS 대시보드 대신 채용 사이트처럼 빠르게 탐색하고 출처와 추천 이유를 비교하는 밝은 English-first 제품을 만든다.
- **2026-07 home direction:** 검색→연구 테마→추천 후보→일정의 정보 구조는 유지하되, 표면은 초기 버전의 흰 배경, 연한 블루, 둥근 카드와 약한 그림자를 사용한다. 진한 네이비 블록과 각진 편집형 표면은 사용하지 않는다.
- **2026-07 signed-in dashboard research:** Lazyweb에서 Teal, Wellfound, Peerlist의 실제 desktop 화면을 확인했다. Teal의 상태·일정 밀도, Wellfound의 평평한 목록 구획, Peerlist의 중심 피드 + 좁은 우측 레일을 조합한다. Teal의 차트/프로모션 블록, Wellfound의 큰 빈 일러스트, Peerlist의 소셜 피드 자체는 가져오지 않는다.
- **LinkedIn / Indeed tracker behavior:** 추천 근거는 프로필·선호와 연결해 설명하고, 저장→진행→지원처럼 현재 상태와 다음 행동을 한 공간에서 추적하는 원칙만 차용한다. 출처: LinkedIn Help의 recommendation/job tracker, Indeed My Jobs 문서.
- **Dashboard decision:** 큰 환영 문구, 동일 크기 3열 CTA 카드, 카드 안의 또 다른 카드, 장식적인 점수 숫자를 제거한다. 로그인 후 홈은 `추천 교수 목록(주요 열) + 프로필/마감/저장 현황(320px 보조 레일)`의 실무형 워크스페이스로 구성한다.

## 1. Authoritative IA

Primary product flow:

1. **로그인 / 초기 설정** — 학교, 연구 분야, 지원 과정, CV/포트폴리오를 설정한다.
2. **홈 대시보드** — 추천 교수, 저장 교수, 최근 분석, 지원 일정을 보여준다.
3. **교수 탐색** — 검색 결과와 교수 상세, 논문, 적합도, 저장, 컨택 진입을 연결한다.
4. **CV 분석 / 컨택 메일 / 스케줄러** — 준비 자료와 실행 작업을 분리한다.
5. **마이페이지** — 프로필, 파일, 관심 교수, 저장 메일, 설정을 모은다.

독립 랩 리스트는 제거하고 검색 결과는 교수 탐색에, 저장 목록은 홈과 마이페이지에 둔다. 커뮤니티는 일주일 MVP에서 제외하며 기존 /labs 경로는 교수 탐색으로 호환 연결한다.

## 2. Tokens

- Canvas `#ffffff`, subtle canvas `#f7f9fc`, surface `#ffffff`.
- Text `#191f28`, secondary `#4e5968`, muted `#8b95a1`.
- Single blue accent: 50 `#eff6ff`, 100 `#dbeafe`, 500 `#3182f6`, 600 `#1b64da`, 700 `#1957bd`. 선택, 링크, 포커스, 진행 상태, 화면당 하나의 주요 CTA에만 쓴다.
- Border `#e5e8eb`; strong border `#d1d6db`; focus `#1b64da` 3px ring.
- Success `#0b6b32` with soft background `#edf8f1`, warning `#b54708`, danger `#d92d20`은 텍스트/아이콘 라벨과 함께만 사용한다.
- English-first system type: display 40/1.2/700, page 32/1.3/700, section 24/1.4/700, card 18/1.45/650, body 16/1.65, label 14/1.5/600.
- Editorial index type: 14/1.4/800 with tabular numerals. Use it for numbered discovery and journey rows so the sequence stays legible without competing with titles.
- 4px spacing base; controls 10px radius, cards 16px, chips pill. 기본 목록은 평평하게, 선택/부유 요소에만 약한 그림자를 쓴다.

## 2A. Language and content contract

- Shipping product copy is English only. This includes navigation, forms, validation, loading and empty states, source labels, metadata, and accessibility text.
- Render the brand name as `Ddaksaeu`; never translate it literally. Use sentence case for headings, buttons, chips, and status messages.
- Prefer concise, concrete product language. Avoid generic AI phrases, inflated claims, and admission-probability language.
- English labels may grow longer than their Korean equivalents. Controls and cards must wrap without clipping at 375/768/1280 widths and at 200% zoom.
- A residual Hangul scan across `app`, `src`, and `tests` is a release gate for the English product.

## 3. Layout and responsive behavior

- Sticky 64px header, max width 1200px, desktop/tablet/mobile gutters 32/24/20px.
- Layout grammar is page-specific: public home uses a search-first discovery feed; dashboard uses a compact work queue; professor search uses a dense filter/results board; professor detail uses a long-form report; My Page uses a saved workspace overview. 모든 화면은 초기 버전의 밝고 부드러운 표면 언어를 공유한다.
- Professor detail uses a single-column editorial flow: research profile, application context, contact, recruitment and source checks, actions, then similar labs. Separate information sections with whitespace and dividers; reserve a bordered surface for the save and contact-draft actions instead of wrapping every section in a card.
- Professor detail is data-adaptive: render overview, publication, verified facts, contact fields, and official links only when the backend provides them. Never reserve a full empty section for unavailable data. Keep the indexed keywords in the hero, use singular publication headings when only one record exists, and replace a completely empty research body with one compact source-directed recovery message.
- Signed-in dashboard: 짧은 `Home` 제목과 현재 상태 요약 뒤에 desktop `minmax(0, 1fr) 320px` grid를 사용한다. 주요 열은 추천 교수와 모집 확인 목록을 평평한 divider list로, 보조 레일은 profile readiness, upcoming deadlines, saved work를 작은 패널로 쌓는다. 900px 미만에서는 한 열로 합치되 제목→readiness→추천→일정 순으로 다음 행동이 먼저 보이게 한다.
- Dashboard sections may use one outer border and subtle canvas contrast, but repeated rows must use dividers instead of individually elevated cards. Section labels are sentence case; decorative uppercase kickers and rank numbers are not used.
- 1024px 이상: 280px filter rail + flexible results. 768–1023px: labelled filter drawer. 768px 미만: sticky search/filter triggers + single-column results.
- Lab cards order: lab/professor, university, keywords, recommendation reason, official source/verified date, save action.
- My Page order: saved-profile overview, quick actions, research keywords/CV, saved professors, similarity recommendations, then secondary data management. The creation/editor form is shown only for empty or explicit editing states. Empty, loading, saved, editing, saving, invalid, and error states are distinct.
- Calendar: desktop month grid + upcoming rail; mobile chronological agenda first. University/lab, source, timezone, and verified/user-entered/unverified status remain visible.
- No horizontal scroll at 375px, 768px, 1280px. Deadline, source, action, recovery text must never be truncated away.

## 4. Material and motion

White space, typography, pale-blue selection, restrained borders and one shadow tier create hierarchy. No decorative gradients or glass. State transitions stay under 220ms. 랜딩의 `UniversityMarquee`만 탐색 가능한 대학 범위를 전달하기 위해 느린 선형 무한 이동을 허용하며, 마우스·키보드 포커스 시 정지한다. `prefers-reduced-motion`에서는 자동 이동을 제거하고 정적 가로 목록으로 제공한다.

The featured research story keeps the original content-first layout on one quiet pale-blue surface. One real Erlenmeyer-flask experiment photograph may span the full card at low opacity as a research-specific watermark behind the copy; it must remain low-contrast and non-interactive. People, split panels, rings, blobs, and decorative gradients are not used.

## 5. Required primitives and states

- `AppHeader`, buttons/links, `SearchField`, `SelectField`, `FilterGroup/Chip/Drawer`, `ResultToolbar`. Single-select controls use one centered chevron, a 36px end inset, and a 1px optical bottom correction across every form.
- `UniversityMarquee`: 사용자가 제공한 대학 로고 이미지를 원본 비율로 표시하는 탐색 가능 마키. 각 로고는 고정 높이 안에서 `contain`으로 맞추고 대체 텍스트를 제공하며, 중복 트랙은 보조기술에서 숨긴다. reduced-motion과 모바일에서는 정적 가로 목록으로 전환한다.
- `LabCard/ListRow`: default, focus, saved, recommended, selected, unavailable-source.
- `SourceBadge`: official, verified date, user-entered, stale/unknown.
- `UploadDropzone`: idle, drag, validating, analyzing, success, unsupported, oversized, failed.
- `KeywordChipEditor`: extracted, user-added, edited, removed, keyboard-selected.
- `ProfileOverview/ProfileEditor`: a saved summary is the default after creation and reload; editing is explicit, prefilled, cancellable, and returns to the overview after save.
- `SavedContactDraft`: saved professor and mail preview, resume action, and explicit removal; hidden when no draft exists.
- `SavedProfessorCard/Button`: use a 44×44 icon-only bookmark control in professor search and detail. The unsaved state is outlined, the saved state is filled with the blue accent, and every state keeps an action-based accessible name, `aria-pressed`, focus ring, and non-color feedback. Unsaved, saving, saved, removing, failed, and empty-list states persist through the owner workspace and remain consistent across list, detail, and My Page.
- `ProfessorDetail`: research overview, focus areas, paper previews, recruitment check, fit evidence, source freshness, and contact drafting. Inferred and unverified values are labeled at section or field level.
- `RecommendationReason`: score band, overlap, explanation, uncertainty.
- `CalendarEvent/DeadlineListItem`: upcoming, today, past, unverified, user-entered.
- `EmptyState/ErrorState/Skeleton`, `DetailDrawer/Dialog` with focus trap and focus restoration.

## 6. Accessibility and QA

- Semantic landmarks, one page heading, `aria-current`, visible keyboard focus, 44×44px touch targets, WCAG AA.
- Filter/result count uses a polite live region; upload/analysis exposes text progress. Selecting a filter never navigates unexpectedly.
- Explain keyword similarity in plain English and never present it as admission probability.
- Mandatory QA: 375/768/1280 screenshots, 200% zoom, long English labels and lab names, keyboard-only operation, screen reader labels, reduced motion, and non-color status cues.

Personas: first-time applicant under deadline pressure; keyboard-first applicant with temporary motor limitation; low-vision mobile user. Accepted one-week debt: no personalized theming and no live calendar provider integration. Accessibility, source clarity, the four-item IA, and primary-task completion are not deferrable.
