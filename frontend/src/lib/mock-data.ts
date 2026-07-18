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
  "Computer Science and Engineering",
  "Electrical Engineering",
  "Mechanical Engineering",
  "Industrial and Management Engineering",
  "Life Sciences",
  "Chemical Engineering",
  "Materials Science and Engineering",
  "Physics",
] as const;

export const FIELDS = [
  "Computer Vision",
  "Natural Language Processing",
  "Robotics",
  "Human-Computer Interaction",
  "Bioinformatics",
  "Semiconductors",
  "Reinforcement Learning",
  "Graphics",
  "Systems",
  "Machine Learning Theory",
];

export const LABS: Lab[] = [
  {
    id: "vislab",
    name: "Visual Intelligence Lab (VisLab)",
    professor: "Professor Jaehoon Lee",
    department: "Computer Science and Engineering",
    field: "Computer Vision",
    summary:
      "We study deep learning methods for visual intelligence, with a focus on 3D scene understanding, video understanding, and multimodal learning.",
    keywords: [
      "Computer Vision",
      "3D Scene",
      "Video Understanding",
      "Multimodal",
      "Diffusion Model",
    ],
    recentTopics: [
      "Multi-view 3D reconstruction",
      "Long-form video understanding",
      "Bias mitigation in text-to-image models",
    ],
    matchScore: 92,
    homepage: "https://vislab.postech.example",
    location: "POSTECH Information Research Laboratories, 4F",
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
    requirements: [
      "Linear algebra and probability fundamentals",
      "PyTorch experience",
      "Consistent paper-review practice",
    ],
  },
  {
    id: "nlplab",
    name: "Language Intelligence Lab (NLPLab)",
    professor: "Professor Seoyeon Park",
    department: "Computer Science and Engineering",
    field: "Natural Language Processing",
    summary:
      "We study reasoning, reliability, and domain adaptation in large language models, including Korean-specialized LLMs and medical and legal applications.",
    keywords: ["LLM", "Reasoning", "Alignment", "Korean NLP", "Retrieval"],
    recentTopics: [
      "Long-context reasoning",
      "Hallucination detection",
      "Domain-specific fine-tuning",
    ],
    matchScore: 84,
    homepage: "https://nlp.postech.example",
    location: "POSTECH Mueunjae Memorial Hall, Room 501",
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
    requirements: [
      "Python and PyTorch",
      "Research paper implementation experience",
      "Academic English reading",
    ],
  },
  {
    id: "roblab",
    name: "Intelligent Robotics Lab",
    professor: "Professor Minseok Jung",
    department: "Mechanical Engineering",
    field: "Robotics",
    summary:
      "We study reinforcement learning, imitation learning, and sim-to-real transfer for manipulation and mobile robotics.",
    keywords: ["Manipulation", "Reinforcement Learning", "Sim2Real", "Imitation Learning"],
    recentTopics: [
      "Deformable object manipulation",
      "Sim-to-real domain randomization",
      "Humanoid locomotion learning",
    ],
    matchScore: 71,
    homepage: "https://roblab.postech.example",
    location: "POSTECH Mechanical Engineering Building, 2F",
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
    requirements: [
      "Dynamics and control theory",
      "ROS experience preferred",
      "Reinforcement learning knowledge",
    ],
  },
  {
    id: "hcilab",
    name: "HCI Design Lab",
    professor: "Professor Jihyun Kim",
    department: "Industrial and Management Engineering",
    field: "Human-Computer Interaction",
    summary:
      "We study how people work with AI tools, focusing on creative work, collaborative interfaces, and AI literacy.",
    keywords: ["HCI", "Human-AI Interaction", "Creativity Support", "Qualitative Study"],
    recentTopics: [
      "LLM collaboration interfaces",
      "AI literacy education tools",
      "Creators' perceptions of copyright",
    ],
    matchScore: 66,
    homepage: "https://hci.postech.example",
    location: "POSTECH RIST Building, 6F",
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
    requirements: [
      "Qualitative research and statistics fundamentals",
      "Prototyping experience",
      "Writing",
    ],
  },
  {
    id: "biolab",
    name: "Computational Bioinformatics Lab",
    professor: "Professor Jisoo Han",
    department: "Life Sciences",
    field: "Bioinformatics",
    summary:
      "We develop computational methods to uncover disease mechanisms from single-cell omics and genomic data.",
    keywords: ["Single-cell", "Genomics", "Deep Learning", "Bioinformatics"],
    recentTopics: [
      "Single-cell trajectory inference",
      "Multi-omics integration",
      "Disease gene prediction",
    ],
    matchScore: 58,
    homepage: "https://cbio.postech.example",
    location: "POSTECH Life Sciences Building, 3F",
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
    requirements: [
      "Statistics and biology background",
      "R and Python",
      "Machine learning fundamentals",
    ],
  },
  {
    id: "semilab",
    name: "Next-Generation Semiconductor Devices Lab",
    professor: "Professor Taeyoon Oh",
    department: "Electrical Engineering",
    field: "Semiconductors",
    summary:
      "We design and simulate low-power neuromorphic devices and 3D integrated memory architectures.",
    keywords: ["Neuromorphic", "3D Integration", "Device Physics", "Low-power"],
    recentTopics: [
      "Memristor-based neuromorphic arrays",
      "3D DRAM thermal management",
      "Heterogeneous integration",
    ],
    matchScore: 41,
    homepage: "https://nano.postech.example",
    location: "POSTECH National Institute for Nanomaterials Technology, 5F",
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
    requirements: ["Semiconductor device physics", "TCAD simulation", "Circuit fundamentals"],
  },
  {
    id: "rllab",
    name: "Decision Intelligence Lab",
    professor: "Professor Dohyun Yoon",
    department: "Computer Science and Engineering",
    field: "Reinforcement Learning",
    summary:
      "We study safe reinforcement learning, offline RL, and multi-agent collaboration for real-world applications.",
    keywords: ["Reinforcement Learning", "Offline RL", "Multi-agent", "Safe RL"],
    recentTopics: [
      "Distribution-shift mitigation in offline RL",
      "Cooperative multi-agent systems",
      "Constrained policy optimization",
    ],
    matchScore: 76,
    homepage: "https://rl.postech.example",
    location: "POSTECH Information Research Laboratories, 6F",
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
    requirements: [
      "Reinforcement learning fundamentals",
      "PyTorch",
      "Probability and optimization",
    ],
  },
  {
    id: "gfxlab",
    name: "Computer Graphics Lab",
    professor: "Professor Yoona Jang",
    department: "Computer Science and Engineering",
    field: "Graphics",
    summary:
      "We study real-time rendering, physics-based simulation, and neural graphics in collaboration with the game and media industries.",
    keywords: ["Rendering", "Neural Graphics", "Simulation", "NeRF"],
    recentTopics: [
      "Real-time neural rendering",
      "Accelerated fluid simulation",
      "Gaussian splatting",
    ],
    matchScore: 64,
    homepage: "https://gfx.postech.example",
    location: "POSTECH Information Research Laboratories, 3F",
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
    requirements: [
      "Linear algebra and calculus",
      "Understanding of graphics pipelines",
      "C++/GLSL preferred",
    ],
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
  "Current undergraduate",
  "Expected graduate",
  "Graduate",
  "Current master's student",
  "Working professional",
] as const;

export const PROGRAM_OPTIONS = [
  "Master's program",
  "PhD program",
  "Integrated MS/PhD program",
  "Undecided",
] as const;

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
  name: "Alex Kim",
  affiliation: "an undergraduate in Computer Science at POSTECH",
  status: "Expected graduate",
  program: "Integrated MS/PhD program",
  interests: ["Computer Vision", "Multimodal", "Diffusion Model", "3D Vision"],
  skills: ["Python", "PyTorch", "OpenCV", "Git", "LaTeX"],
  methodologies: ["Deep Learning", "Generative Models", "Representation Learning"],
  projects: [
    "Undergraduate thesis — temporal attention for video understanding",
    "Campus competition — silver award for multimodal sentiment analysis",
    "Internship — visual recognition pipeline at an AI startup",
  ],
};

export type EventKind = "apply" | "contact" | "docs" | "interview";

export const EVENT_KIND_LABEL: Record<EventKind, string> = {
  apply: "Application",
  contact: "Outreach",
  docs: "Documents",
  interview: "Interview",
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
    title: "Send outreach email to VisLab",
    kind: "contact",
    date: "2026-07-20",
    labId: "vislab",
    memo: "Introduce research interests + attach CV",
  },
  {
    id: "e2",
    title: "Fall application deadline",
    kind: "apply",
    date: "2026-07-31",
    memo: "Online application closes at 23:59",
  },
  { id: "e3", title: "Complete personal statement draft", kind: "docs", date: "2026-07-22" },
  {
    id: "e4",
    title: "NLPLab introductory meeting",
    kind: "interview",
    date: "2026-07-27",
    labId: "nlplab",
  },
  { id: "e5", title: "Request recommendation letter", kind: "docs", date: "2026-07-16" },
];
