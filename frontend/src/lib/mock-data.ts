export type Lab = {
  id: string;
  name: string;
  professor: string;
  department: string;
  field: string;
  summary: string;
  keywords: string[];
  recentTopics: string[];
  matchScore: number; // 0-100
  homepage: string;
  location: string;
  email: string;
  updatedAt: string;
  papers: { title: string; year: number; venue: string; keywords: string[] }[];
  members: { professor: number; phd: number; ms: number };
  requirements: string[];
};

export const DEPARTMENTS = [
  "컴퓨터공학과",
  "전자전기공학과",
  "기계공학과",
  "산업경영공학과",
  "생명과학과",
  "화학공학과",
  "신소재공학과",
  "물리학과",
] as const;

export const FIELDS = [
  "컴퓨터 비전",
  "자연어 처리",
  "로보틱스",
  "인간-컴퓨터 상호작용",
  "바이오인포매틱스",
  "반도체",
  "강화학습",
  "그래픽스",
  "시스템",
  "머신러닝 이론",
];

export const LABS: Lab[] = [
  {
    id: "vislab",
    name: "시각지능 연구실 (VisLab)",
    professor: "이재훈 교수",
    department: "컴퓨터공학과",
    field: "컴퓨터 비전",
    summary:
      "이미지와 영상에서 의미를 이해하는 딥러닝 기반 시각 지능 기술을 연구합니다. 3D 장면 이해, 비디오 이해, 멀티모달 학습이 주요 방향입니다.",
    keywords: [
      "Computer Vision",
      "3D Scene",
      "Video Understanding",
      "Multimodal",
      "Diffusion Model",
    ],
    recentTopics: ["멀티뷰 3D 재구성", "장기 비디오 이해", "텍스트-이미지 생성 모델의 편향 완화"],
    matchScore: 92,
    homepage: "https://vislab.postech.example",
    location: "포항공대 정보통신연구소 4층",
    email: "vislab@postech.example",
    updatedAt: "2025-07-01",
    papers: [
      {
        title: "Long-Range Video Understanding via Sparse Memory",
        year: 2025,
        venue: "CVPR",
        keywords: ["Video", "Memory"],
      },
      {
        title: "Debiasing Text-to-Image Diffusion",
        year: 2024,
        venue: "NeurIPS",
        keywords: ["Diffusion", "Fairness"],
      },
      {
        title: "Multi-View 3D Reconstruction with Neural Fields",
        year: 2024,
        venue: "ICCV",
        keywords: ["3D", "NeRF"],
      },
    ],
    members: { professor: 1, phd: 6, ms: 5 },
    requirements: ["선형대수 · 확률 기초", "PyTorch 경험", "논문 리뷰 습관"],
  },
  {
    id: "nlplab",
    name: "언어지능 연구실 (NLPLab)",
    professor: "박서연 교수",
    department: "컴퓨터공학과",
    field: "자연어 처리",
    summary:
      "대규모 언어모델의 추론 능력, 신뢰성, 도메인 적응을 중점으로 연구합니다. 한국어 특화 LLM과 의료 · 법률 도메인 응용을 다룹니다.",
    keywords: ["LLM", "Reasoning", "Alignment", "Korean NLP", "Retrieval"],
    recentTopics: ["긴 문맥 추론", "환각(hallucination) 감지", "도메인 특화 파인튜닝"],
    matchScore: 84,
    homepage: "https://nlp.postech.example",
    location: "포항공대 무은재기념관 501호",
    email: "nlplab@postech.example",
    updatedAt: "2025-06-24",
    papers: [
      {
        title: "Chain-of-Verification for Faithful LLM Reasoning",
        year: 2025,
        venue: "ACL",
        keywords: ["LLM", "Reasoning"],
      },
      {
        title: "Hallucination Detection in Long-Form QA",
        year: 2024,
        venue: "EMNLP",
        keywords: ["QA", "Reliability"],
      },
    ],
    members: { professor: 1, phd: 4, ms: 6 },
    requirements: ["파이썬 · PyTorch", "논문 구현 경험", "영어 리딩"],
  },
  {
    id: "roblab",
    name: "지능형 로보틱스 연구실",
    professor: "정민석 교수",
    department: "기계공학과",
    field: "로보틱스",
    summary:
      "매니퓰레이션과 이동 로봇을 위한 강화학습, 모방학습, 시뮬레이션-실세계 전이를 연구합니다.",
    keywords: ["Manipulation", "Reinforcement Learning", "Sim2Real", "Imitation Learning"],
    recentTopics: ["부드러운 물체 조작", "Sim2Real 도메인 랜덤화", "휴머노이드 보행 학습"],
    matchScore: 71,
    homepage: "https://roblab.postech.example",
    location: "포항공대 기계관 2층",
    email: "roblab@postech.example",
    updatedAt: "2025-06-30",
    papers: [
      {
        title: "Sim-to-Real Transfer via Adaptive Randomization",
        year: 2025,
        venue: "ICRA",
        keywords: ["Sim2Real"],
      },
      {
        title: "Learning Dexterous Manipulation from Play Data",
        year: 2024,
        venue: "CoRL",
        keywords: ["Manipulation"],
      },
    ],
    members: { professor: 1, phd: 5, ms: 4 },
    requirements: ["동역학 · 제어 이론", "ROS 경험 우대", "강화학습 지식"],
  },
  {
    id: "hcilab",
    name: "HCI 디자인 연구실",
    professor: "김지현 교수",
    department: "산업경영공학과",
    field: "인간-컴퓨터 상호작용",
    summary:
      "AI 도구와 함께 일하는 사람의 경험을 연구합니다. 창의적 작업, 협업 인터페이스, AI 리터러시가 주 관심사입니다.",
    keywords: ["HCI", "Human-AI Interaction", "Creativity Support", "Qualitative Study"],
    recentTopics: ["LLM 협업 인터페이스", "AI 리터러시 교육 도구", "창작자의 저작권 인식"],
    matchScore: 66,
    homepage: "https://hci.postech.example",
    location: "포항공대 학연산 6층",
    email: "hcilab@postech.example",
    updatedAt: "2025-05-20",
    papers: [
      {
        title: "Designing LLM Copilots for Creative Writers",
        year: 2025,
        venue: "CHI",
        keywords: ["HCI", "LLM"],
      },
      { title: "How Students Learn to Prompt", year: 2024, venue: "CSCW", keywords: ["Education"] },
    ],
    members: { professor: 1, phd: 3, ms: 5 },
    requirements: ["질적 연구 · 통계 기초", "프로토타이핑 경험", "글쓰기"],
  },
  {
    id: "biolab",
    name: "계산생명정보 연구실",
    professor: "한지수 교수",
    department: "생명과학과",
    field: "바이오인포매틱스",
    summary: "단일세포 오믹스와 유전체 데이터에서 질병 메커니즘을 규명하는 계산 방법을 개발합니다.",
    keywords: ["Single-cell", "Genomics", "Deep Learning", "Bioinformatics"],
    recentTopics: ["단일세포 궤적 추론", "다중 오믹스 통합", "질병 유전자 예측"],
    matchScore: 58,
    homepage: "https://cbio.postech.example",
    location: "포항공대 생명과학관 3층",
    email: "cbio@postech.example",
    updatedAt: "2025-06-11",
    papers: [
      {
        title: "Trajectory Inference for Single-Cell Data",
        year: 2025,
        venue: "Nature Methods",
        keywords: ["Single-cell"],
      },
      {
        title: "Multi-omics Integration via Graph Neural Networks",
        year: 2024,
        venue: "Bioinformatics",
        keywords: ["Genomics"],
      },
    ],
    members: { professor: 1, phd: 4, ms: 3 },
    requirements: ["통계 · 생물학 배경", "R · Python", "머신러닝 기초"],
  },
  {
    id: "semilab",
    name: "차세대 반도체 소자 연구실",
    professor: "오태윤 교수",
    department: "전자전기공학과",
    field: "반도체",
    summary: "저전력 뉴로모픽 소자와 3D 집적 메모리 구조를 설계하고 시뮬레이션합니다.",
    keywords: ["Neuromorphic", "3D Integration", "Device Physics", "Low-power"],
    recentTopics: ["멤리스터 기반 뉴로모픽 어레이", "3D DRAM 열관리", "이종 집적"],
    matchScore: 41,
    homepage: "https://nano.postech.example",
    location: "포항공대 나노융합기술원 5층",
    email: "nanolab@postech.example",
    updatedAt: "2025-06-02",
    papers: [
      {
        title: "Memristor Arrays for In-Memory Computing",
        year: 2025,
        venue: "IEDM",
        keywords: ["Memristor"],
      },
      { title: "Thermal Modeling of 3D DRAM Stacks", year: 2024, venue: "ISSCC", keywords: ["3D"] },
    ],
    members: { professor: 1, phd: 7, ms: 4 },
    requirements: ["반도체 소자 물리", "TCAD 시뮬레이션", "회로 기초"],
  },
  {
    id: "rllab",
    name: "결정지능 연구실",
    professor: "윤도현 교수",
    department: "컴퓨터공학과",
    field: "강화학습",
    summary: "실세계 응용을 위한 안전한 강화학습, 오프라인 RL, 멀티에이전트 협력을 연구합니다.",
    keywords: ["Reinforcement Learning", "Offline RL", "Multi-agent", "Safe RL"],
    recentTopics: ["오프라인 RL의 분포 이동 완화", "협력 멀티에이전트", "제약 조건 하 정책 최적화"],
    matchScore: 76,
    homepage: "https://rl.postech.example",
    location: "포항공대 정보통신연구소 6층",
    email: "rllab@postech.example",
    updatedAt: "2025-07-04",
    papers: [
      {
        title: "Conservative Q-Learning Revisited",
        year: 2025,
        venue: "ICML",
        keywords: ["Offline RL"],
      },
      {
        title: "Cooperative Multi-Agent RL with Communication",
        year: 2024,
        venue: "NeurIPS",
        keywords: ["Multi-agent"],
      },
    ],
    members: { professor: 1, phd: 3, ms: 4 },
    requirements: ["강화학습 기초", "PyTorch", "확률 · 최적화"],
  },
  {
    id: "gfxlab",
    name: "컴퓨터 그래픽스 연구실",
    professor: "장윤아 교수",
    department: "컴퓨터공학과",
    field: "그래픽스",
    summary:
      "실시간 렌더링, 물리 기반 시뮬레이션, 뉴럴 그래픽스를 연구하며 게임/영상 산업과 협력합니다.",
    keywords: ["Rendering", "Neural Graphics", "Simulation", "NeRF"],
    recentTopics: ["실시간 뉴럴 렌더링", "유체 시뮬레이션 가속", "가우시안 스플래팅"],
    matchScore: 64,
    homepage: "https://gfx.postech.example",
    location: "포항공대 정보통신연구소 3층",
    email: "gfxlab@postech.example",
    updatedAt: "2025-06-18",
    papers: [
      {
        title: "Real-Time Gaussian Splatting for AR",
        year: 2025,
        venue: "SIGGRAPH",
        keywords: ["Rendering"],
      },
      {
        title: "Neural Fluid Simulation",
        year: 2024,
        venue: "SIGGRAPH Asia",
        keywords: ["Simulation"],
      },
    ],
    members: { professor: 1, phd: 3, ms: 3 },
    requirements: ["선형대수 · 미적분", "그래픽스 파이프라인 이해", "C++/GLSL 우대"],
  },
];

export type UserProfile = {
  name: string;
  affiliation: string;
  status: string;
  program: string;
  interests: string[];
  skills: string[];
  methodologies: string[];
  projects: string[];
};

export const STATUS_OPTIONS = [
  "학부 재학중",
  "졸업 예정자",
  "졸업생",
  "석사과정 재학중",
  "직장인",
] as const;

export const PROGRAM_OPTIONS = ["석사과정", "박사과정", "석박통합과정", "아직 결정 못함"] as const;

export const INTEREST_SUGGESTIONS = [
  "Computer Vision",
  "Multimodal",
  "Diffusion Model",
  "3D Vision",
  "NLP",
  "LLM",
  "Reinforcement Learning",
  "Robotics",
  "HCI",
  "Bioinformatics",
  "Graphics",
  "Neuromorphic",
];

export const SKILL_SUGGESTIONS = [
  "Python",
  "PyTorch",
  "TensorFlow",
  "JAX",
  "OpenCV",
  "CUDA",
  "C++",
  "ROS",
  "R",
  "Git",
  "LaTeX",
  "Docker",
  "SQL",
];

export const USER_PROFILE: UserProfile = {
  name: "김딱새우",
  affiliation: "포항공대 컴퓨터공학과 학부",
  status: "졸업 예정자",
  program: "석박통합과정",
  interests: ["Computer Vision", "Multimodal", "Diffusion Model", "3D Vision"],
  skills: ["Python", "PyTorch", "OpenCV", "Git", "LaTeX"],
  methodologies: ["딥러닝", "생성 모델", "표현 학습"],
  projects: [
    "학부 졸업연구 — 비디오 이해를 위한 시간적 attention 모듈",
    "교내 대회 — 멀티모달 감성 분석 은상",
    "인턴십 — 국내 AI 스타트업 시각 인식 파이프라인",
  ],
};

export type EventKind = "apply" | "contact" | "docs" | "interview";

export const EVENT_KIND_LABEL: Record<EventKind, string> = {
  apply: "원서 접수",
  contact: "컨택",
  docs: "서류 준비",
  interview: "면접",
};

export const EVENT_KIND_COLOR: Record<EventKind, string> = {
  apply: "bg-[color:var(--point)]/12 text-[color:var(--deep)] border-[color:var(--point)]/30",
  contact:
    "bg-[color:var(--success)]/12 text-[color:var(--success)] border-[color:var(--success)]/30",
  docs: "bg-[color:var(--warning)]/15 text-[color:oklch(0.5_0.11_75)] border-[color:var(--warning)]/40",
  interview:
    "bg-[color:var(--info)]/15 text-[color:oklch(0.42_0.12_230)] border-[color:var(--info)]/40",
};

export const EVENT_KIND_DOT: Record<EventKind, string> = {
  apply: "bg-[color:var(--point)]",
  contact: "bg-[color:var(--success)]",
  docs: "bg-[color:var(--warning)]",
  interview: "bg-[color:var(--info)]",
};

export type CalendarEvent = {
  id: string;
  title: string;
  kind: EventKind;
  date: string; // yyyy-mm-dd
  labId?: string;
  memo?: string;
};

export const INITIAL_EVENTS: CalendarEvent[] = [
  {
    id: "e1",
    title: "VisLab 컨택 메일 보내기",
    kind: "contact",
    date: "2026-07-20",
    labId: "vislab",
    memo: "연구 관심사 소개 + CV 첨부",
  },
  {
    id: "e2",
    title: "가을학기 원서 접수 마감",
    kind: "apply",
    date: "2026-07-31",
    memo: "온라인 지원 시스템 마감 23:59",
  },
  { id: "e3", title: "자기소개서 초안 완성", kind: "docs", date: "2026-07-22" },
  { id: "e4", title: "NLPLab 사전 미팅", kind: "interview", date: "2026-07-27", labId: "nlplab" },
  { id: "e5", title: "추천서 요청", kind: "docs", date: "2026-07-16" },
];
