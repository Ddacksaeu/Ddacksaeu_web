import type { DocumentAnalysis, EvidenceItem } from "./document-analysis";

type Properties = Readonly<{ analysis: DocumentAnalysis }>;

function EvidenceList({ items }: Readonly<{ items: readonly EvidenceItem[] }>) {
  if (items.length === 0) return null;
  return <details className="cv-evidence"><summary>View evidence</summary><ul>{items.map((item) => <li key={`${item.value}-${item.evidence}`}><strong>{Math.round(item.confidence * 100)}%</strong> {item.evidence}</li>)}</ul></details>;
}

function ListSection({ title, values, evidence }: Readonly<{ title: string; values: readonly string[]; evidence: readonly EvidenceItem[] }>) {
  if (values.length === 0) return null;
  return <section className="cv-result-section"><h3>{title}</h3><ul>{values.map((value) => <li key={value}>{value}</li>)}</ul><EvidenceList items={evidence} /></section>;
}

export function CvAnalysisResult({ analysis }: Properties) {
  const localRuleBased = analysis.analyzer_origin === "local_rule_based";
  return <section className="cv-analysis-result" aria-labelledby="cv-analysis-title">
    <div className="profile-section-heading"><div><p>Latest analysis</p><h2 id="cv-analysis-title">{analysis.original_filename ?? "CV analysis"}</h2></div><span>{analysis.file_type ?? "Unknown format"}</span></div>
    {localRuleBased && <p className="cv-origin-note">This CV was analyzed on the server with local rule-based analysis; no external AI API was used.</p>}
    <p className="cv-summary">{analysis.short_summary}</p>
    {analysis.warnings.length > 0 && <div className="cv-warning" role="alert"><strong>Warnings</strong><ul>{analysis.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
    <div className="cv-chip-groups">
      {analysis.skills.length > 0 && <div><h3>Skills</h3><p>{analysis.skills.map((skill) => <span key={skill}>{skill}</span>)}</p><EvidenceList items={analysis.evidence_items["skills"] ?? []} /></div>}
      {analysis.keywords.length > 0 && <div><h3>Extracted keywords</h3><p>{analysis.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}</p><EvidenceList items={analysis.evidence_items["keywords"] ?? []} /></div>}
    </div>
    <div className="cv-result-grid">
      <ListSection title="Education" values={analysis.education} evidence={analysis.evidence_items["education"] ?? []} />
      <ListSection title="Research interests" values={analysis.research_interests} evidence={analysis.evidence_items["research_interests"] ?? []} />
      <ListSection title="Research experience" values={analysis.research_experience} evidence={analysis.evidence_items["research_experience"] ?? []} />
      <ListSection title="Strengths" values={analysis.strengths} evidence={analysis.evidence_items["strengths"] ?? []} />
    </div>
    {analysis.projects.length > 0 && <section className="cv-result-section"><h3>Projects</h3><ul>{analysis.projects.map((project) => <li key={project.name}><strong>{project.name}</strong><p>{project.description}</p>{project.technologies.length > 0 && <small>{project.technologies.join(" · ")}</small>}</li>)}</ul><EvidenceList items={analysis.evidence_items["projects"] ?? []} /></section>}
  </section>;
}
