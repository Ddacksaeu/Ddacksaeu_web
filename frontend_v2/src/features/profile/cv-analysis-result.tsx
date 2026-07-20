import type {
  CategoryFeedback,
  DocumentAnalysis,
  EvidenceItem,
} from "./document-analysis";

type Properties = Readonly<{ analysis: DocumentAnalysis }>;
type Education = DocumentAnalysis["education"][number];
type Experience = DocumentAnalysis["research_experience"][number];

function EvidenceList({ items }: Readonly<{ items: readonly EvidenceItem[] }>) {
  if (items.length === 0) return null;
  return <details className="cv-evidence"><summary>View source evidence</summary><ul>{items.map((item) => <li key={`${item.value}-${item.evidence}`}><strong>{Math.round(item.confidence * 100)}%</strong> {item.evidence}</li>)}</ul></details>;
}

function EntryMeta({ values }: Readonly<{ values: readonly string[] }>) {
  const visible = values.filter(Boolean);
  return visible.length > 0 ? <p>{visible.join(" · ")}</p> : null;
}

function EducationSection({ items }: Readonly<{ items: readonly Education[] }>) {
  if (items.length === 0) return null;
  return <section className="cv-result-section"><h3>Education</h3><ul>{items.map((item, index) => <li key={`${item.degree}-${item.institution}-${index}`}><strong>{item.degree || "Education entry"}</strong><EntryMeta values={[item.institution, item.location, [item.start_date, item.end_date].filter(Boolean).join(" – ")]} />{item.details.length > 0 && <ul>{item.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>}</li>)}</ul></section>;
}

function ExperienceSection({ title, items }: Readonly<{ title: string; items: readonly Experience[] }>) {
  if (items.length === 0) return null;
  return <section className="cv-result-section"><h3>{title}</h3><ul>{items.map((item, index) => <li key={`${item.title}-${item.organization}-${index}`}><strong>{item.title || "Experience entry"}</strong><EntryMeta values={[item.organization, item.location, [item.start_date, item.end_date].filter(Boolean).join(" – ")]} />{item.details.length > 0 && <ul>{item.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>}</li>)}</ul></section>;
}

function FeedbackCard({ feedback }: Readonly<{ feedback: CategoryFeedback }>) {
  return <article className="cv-result-section">
    <h3>{feedback.category}</h3>
    <p>{feedback.current_state}</p>
    {feedback.improvements.length > 0 && <><strong>What to improve</strong><ul>{feedback.improvements.map((item) => <li key={item}>{item}</li>)}</ul></>}
    {feedback.suggestions.length > 0 && <><strong>Suggested changes</strong><ul>{feedback.suggestions.map((item) => <li key={item}>{item}</li>)}</ul></>}
  </article>;
}

export function CvAnalysisResult({ analysis }: Properties) {
  return <section className="cv-analysis-result" aria-labelledby="cv-analysis-title">
    <div className="profile-section-heading"><div><p>Latest analysis</p><h2 id="cv-analysis-title">{analysis.original_filename ?? "CV analysis"}</h2></div><span>{analysis.file_type ?? "Unknown format"}</span></div>
    <p className="cv-origin-note">Analyzed locally on the server. No OpenAI or external AI API was used.</p>
    <p className="cv-summary">{analysis.short_summary}</p>
    {analysis.warnings.length > 0 && <div className="cv-warning" role="alert"><strong>Warnings</strong><ul>{analysis.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
    <div className="cv-chip-groups">
      {analysis.research_interests.length > 0 && <div><h3>Research interests</h3><p>{analysis.research_interests.map((interest) => <span key={interest}>{interest}</span>)}</p><EvidenceList items={analysis.evidence_items["research_interests"] ?? []} /></div>}
      {analysis.skills.length > 0 && <div><h3>Technical skills</h3><p>{analysis.skills.map((skill) => <span key={skill}>{skill}</span>)}</p><EvidenceList items={analysis.evidence_items["skills"] ?? []} /></div>}
      {analysis.keywords.length > 0 && <div><h3>Lab matching keywords</h3><p>{analysis.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}</p><EvidenceList items={analysis.evidence_items["keywords"] ?? []} /></div>}
    </div>
    <div className="cv-result-grid">
      <EducationSection items={analysis.education} />
      <ExperienceSection title="Research experience" items={analysis.research_experience} />
      <ExperienceSection title="Work experience" items={analysis.work_experience} />
      <ExperienceSection title="Campus & community involvement" items={analysis.campus_community_involvement} />
    </div>
    {analysis.projects.length > 0 && <section className="cv-result-section"><h3>Projects</h3><ul>{analysis.projects.map((project, index) => <li key={`${project.name}-${index}`}><strong>{project.name}</strong><EntryMeta values={[project.organization, project.location, [project.start_date, project.end_date].filter(Boolean).join(" – ")]} />{project.description && <p>{project.description}</p>}{project.details.length > 0 && <ul>{project.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>}{project.technologies.length > 0 && <small>{project.technologies.join(" · ")}</small>}</li>)}</ul></section>}
    {analysis.missing_information.length > 0 && <section className="cv-result-section"><h3>Not clearly detected</h3><p>{analysis.missing_information.join(", ")}</p></section>}
    {analysis.category_feedback.length > 0 && <section aria-labelledby="cv-feedback-title"><h2 id="cv-feedback-title">CV improvement feedback</h2><div className="cv-result-grid">{analysis.category_feedback.map((feedback) => <FeedbackCard key={feedback.category} feedback={feedback} />)}</div></section>}
  </section>;
}
