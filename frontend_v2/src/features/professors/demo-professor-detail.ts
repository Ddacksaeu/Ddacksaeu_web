import type { LabCatalogEntry } from "../../server/catalog/schema";

export type DemoResearchFocus = {
  readonly title: string;
  readonly description: string;
  readonly keywords: readonly string[];
};

export type DemoPaperPreview = {
  readonly title: string;
  readonly year: string;
  readonly summary: string;
};

export type DemoProfessorDetail = {
  readonly overview: string;
  readonly department: string;
  readonly location: string;
  readonly researchFocus: readonly DemoResearchFocus[];
  readonly methods: readonly string[];
  readonly projects: readonly string[];
  readonly papers: readonly DemoPaperPreview[];
  readonly degreePrograms: readonly string[];
  readonly recruitmentNote: string;
  readonly sourceNote: string;
};

export function createDemoProfessorDetail(lab: LabCatalogEntry): DemoProfessorDetail {
  const primary = lab.topics[0] ?? "Research topic";
  const secondary = lab.topics[1] ?? "Applied research";
  return {
    overview: `Research themes connect ${primary} with ${secondary}, from question design through reproducible evaluation. Confirm the lab’s current direction and recruitment status on its official website.`,
    department: "Computer science-related department · Verify exact affiliation",
    location: `${lab.institution} campus · Lab location unverified`,
    researchFocus: [
      {
        title: `${primary} core models and methods`,
        description: `Problem definition, model design, and evaluation for ${primary}.`,
        keywords: [primary, "Model design", "Performance evaluation"],
      },
      {
        title: `${secondary} applications and validation`,
        description: `${secondary} results evaluated under changing real-world conditions.`,
        keywords: [secondary, "Applied research", "Reproducibility"],
      },
      {
        title: "Reliable research workflow",
        description: "Data bias, experiment logs, and error analysis reviewed as one workflow.",
        keywords: ["Error analysis", "Experiment reproduction", "Research ethics"],
      },
    ],
    methods: ["Literature review", "Data preprocessing", "Model implementation", "Quantitative and qualitative evaluation", "Error and limitation analysis"],
    projects: [
      `${primary} problem-solving prototype`,
      `Integrated ${primary} and ${secondary} experiment`,
      "Reproducible benchmark for student researchers",
    ],
    papers: [
      { title: `${primary} Adaptive framework for representation learning`, year: "2026 Demo", summary: "Representation-learning framework and evaluation criteria." },
      { title: `${secondary} Reliable evaluation methods`, year: "2025 Demo", summary: "Evaluation conditions, reliability checks, and error analysis." },
      { title: `${primary} data efficiency analysis`, year: "2025 Demo", summary: "Relationship between data scale and model performance." },
      { title: "Experiment management for reproducible student research", year: "2024 Demo", summary: "Experiment logs, result tracking, and reproduction workflow." },
    ],
    degreePrograms: ["Master's", "PhD", "Integrated MS/PhD"],
    recruitmentNote: "Recruitment status, degree programs, funding, and project assignments are unverified. Check the official lab site and graduate admissions guide before contacting.",
    sourceNote: "Only official university and department links are registered. Lab descriptions and papers are demo content until the crawler is connected.",
  };
}
