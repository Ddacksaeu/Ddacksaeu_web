import type {
  CategoryFeedback,
  DocumentAnalysis,
  EvidenceItem,
} from "./document-analysis";

type Properties = Readonly<{ analysis: DocumentAnalysis }>;
type Education = DocumentAnalysis["education"][number];
type Experience = DocumentAnalysis["research_experience"][number];
type Project = DocumentAnalysis["projects"][number];

function EvidenceList({ items }: Readonly<{ items: readonly EvidenceItem[] }>) {
  if (items.length === 0) return null;
  return (
    <details className="cv-evidence">
      <summary>View source evidence</summary>
      <ul>{items.map((item) => <li key={`${item.value}-${item.evidence}`}><strong>{Math.round(item.confidence * 100)}%</strong> {item.evidence}</li>)}</ul>
    </details>
  );
}

function EntryMeta({ values }: Readonly<{ values: readonly string[] }>) {
  const visible = values.filter(Boolean);
  return visible.length > 0 ? <div className="cv-entry-meta">{visible.map((value) => <span key={value}>{value}</span>)}</div> : null;
}

function SectionShell({ title, count, priority = false, children }: Readonly<{ title: string; count: number; priority?: boolean; children: React.ReactNode }>) {
  return (
    <section className={`cv-structured-section${priority ? " is-priority" : ""}`}>
      <header><h3>{title}</h3><span>{count}</span></header>
      <div className="cv-entry-list">{children}</div>
    </section>
  );
}

function DetailList({ details }: Readonly<{ details: readonly string[] }>) {
  return details.length > 0 ? <ul className="cv-detail-list">{details.map((detail, index) => <li key={`${detail}-${index}`}>{detail}</li>)}</ul> : null;
}

function ExperienceSection({ title, items, priority = false }: Readonly<{ title: string; items: readonly Experience[]; priority?: boolean }>) {
  if (items.length === 0) return null;
  return (
    <SectionShell title={title} count={items.length} priority={priority}>
      {items.map((item, index) => (
        <article className="cv-entry" key={`${item.title}-${item.organization}-${index}`}>
          <h4>{item.title || "Experience entry"}</h4>
          <EntryMeta values={[item.organization, item.location, [item.start_date, item.end_date].filter(Boolean).join(" – ")]} />
          <DetailList details={item.details} />
        </article>
      ))}
    </SectionShell>
  );
}

function EducationSection({ items }: Readonly<{ items: readonly Education[] }>) {
  if (items.length === 0) return null;
  return (
    <SectionShell title="Education" count={items.length}>
      {items.map((item, index) => (
        <article className="cv-entry" key={`${item.degree}-${item.institution}-${index}`}>
          <h4>{item.degree || "Education entry"}</h4>
          <EntryMeta values={[item.institution, item.location, [item.start_date, item.end_date].filter(Boolean).join(" – ")]} />
          <DetailList details={item.details} />
        </article>
      ))}
    </SectionShell>
  );
}

function ProjectsSection({ items }: Readonly<{ items: readonly Project[] }>) {
  if (items.length === 0) return null;
  return (
    <SectionShell title="Projects" count={items.length} priority>
      {items.map((project, index) => (
        <article className="cv-entry cv-project-entry" key={`${project.name}-${index}`}>
          <h4>{project.name}</h4>
          <EntryMeta values={[project.organization, project.location, [project.start_date, project.end_date].filter(Boolean).join(" – ")]} />
          <DetailList details={project.details.length > 0 ? project.details : project.description ? [project.description] : []} />
          {project.technologies.length > 0 && <div className="cv-technology-list">{project.technologies.map((technology) => <span key={technology}>{technology}</span>)}</div>}
        </article>
      ))}
    </SectionShell>
  );
}

function FeedbackList({ label, tone, items }: Readonly<{ label: string; tone: "positive" | "warning" | "action"; items: readonly string[] }>) {
  if (items.length === 0) return null;
  return <div className={`cv-feedback-list is-${tone}`}><strong>{label}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}

function FeedbackCard({ feedback }: Readonly<{ feedback: CategoryFeedback }>) {
  return (
    <article className="cv-feedback-card">
      <header><h3>{feedback.category}</h3></header>
      <p className="cv-feedback-snapshot">{feedback.current_state}</p>
      <FeedbackList label="What works" tone="positive" items={feedback.strengths} />
      <FeedbackList label="Needs attention" tone="warning" items={feedback.improvements} />
      <FeedbackList label="Recommended edit" tone="action" items={feedback.suggestions} />
    </article>
  );
}

export function CvAnalysisResult({ analysis }: Properties) {
  return (
    <section className="cv-analysis-result" aria-labelledby="cv-analysis-title">
      <div className="profile-section-heading"><div><p>Latest analysis</p><h2 id="cv-analysis-title">{analysis.original_filename ?? "CV analysis"}</h2></div><span>{analysis.file_type ?? "Unknown format"}</span></div>
      <p className="cv-origin-note">Analyzed locally on the server. No OpenAI or external AI API was used.</p>
      <p className="cv-summary">{analysis.short_summary}</p>
      {analysis.warnings.length > 0 && <div className="cv-warning" role="alert"><strong>Warnings</strong><ul>{analysis.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}

      <section className="cv-keyword-board" aria-label="Extracted matching profile">
        {analysis.research_interests.length > 0 && <div><h3>Research interests</h3><p>{analysis.research_interests.map((interest) => <span key={interest}>{interest}</span>)}</p><EvidenceList items={analysis.evidence_items["research_interests"] ?? []} /></div>}
        {analysis.skills.length > 0 && <div><h3>Technical skills</h3><p>{analysis.skills.map((skill) => <span key={skill}>{skill}</span>)}</p><EvidenceList items={analysis.evidence_items["skills"] ?? []} /></div>}
        {analysis.keywords.length > 0 && <div className="is-wide"><h3>Lab matching keywords</h3><p>{analysis.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}</p><EvidenceList items={analysis.evidence_items["keywords"] ?? []} /></div>}
      </section>

      <div className="cv-section-title"><div><p>Structured CV</p><h2>Experience and projects</h2></div><span>Prioritized for lab matching</span></div>
      <div className="cv-priority-stack">
        <ExperienceSection title="Work experience" items={analysis.work_experience} priority />
        <ProjectsSection items={analysis.projects} />
      </div>
      <div className="cv-secondary-grid">
        <EducationSection items={analysis.education} />
        <ExperienceSection title="Research experience" items={analysis.research_experience} />
        <ExperienceSection title="Campus & community involvement" items={analysis.campus_community_involvement} />
      </div>

      {analysis.missing_information.length > 0 && <section className="cv-missing-card"><strong>Not clearly detected</strong><p>{analysis.missing_information.join(" · ")}</p></section>}
      {analysis.category_feedback.length > 0 && <section className="cv-feedback-section" aria-labelledby="cv-feedback-title"><div className="cv-section-title"><div><p>Category review</p><h2 id="cv-feedback-title">CV improvement feedback</h2></div><span>Strengths, gaps, and next edits</span></div><div className="cv-feedback-grid">{analysis.category_feedback.map((feedback) => <FeedbackCard key={feedback.category} feedback={feedback} />)}</div></section>}
    </section>
  );
}
