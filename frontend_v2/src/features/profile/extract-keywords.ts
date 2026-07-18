const RESEARCH_TOPICS = [
  { canonical: "Computer Vision", aliases: ["Computer Vision", "computer vision"] },
  { canonical: "HCI", aliases: ["hci", "human-computer interaction"] },
  { canonical: "Machine Learning", aliases: ["Machine Learning", "machine learning"] },
  { canonical: "Natural Language Processing", aliases: ["Natural Language Processing", "natural language processing", "nlp"] },
  { canonical: "Robotics", aliases: ["Robotics", "robotics"] },
  { canonical: "Databases", aliases: ["Databases", "database"] },
  { canonical: "Security", aliases: ["Security", "security"] },
  { canonical: "Distributed Systems", aliases: ["Distributed Systems", "distributed systems"] },
] as const;

export function extractResearchKeywords(text: string): readonly string[] {
  const normalized = text.toLocaleLowerCase();
  return RESEARCH_TOPICS.flatMap((topic) =>
    topic.aliases.some((alias) => normalized.includes(alias)) ? [topic.canonical] : []
  );
}
