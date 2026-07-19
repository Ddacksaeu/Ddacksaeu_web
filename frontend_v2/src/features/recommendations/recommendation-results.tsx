import Link from "next/link";

import type { Recommendation } from "./recommendations-api";

type Properties = Readonly<{
  items: readonly Recommendation[];
}>;

export function RecommendationResults({ items }: Properties) {
  if (items.length === 0) {
    return <section className="catalog-empty"><h2>No professor matches yet</h2><p>Try analyzing a CV with more research experience or keywords.</p></section>;
  }

  return <section aria-label="CV-based professor recommendations" className="profile-recommendation">
    <div className="profile-recommendation-heading">
      <div><p>CV RESEARCH MATCH</p><h2>Best professor matches</h2></div>
      <span>Research overlap, not admission probability</span>
    </div>
    <ol className="profile-recommendation-list">
      {items.slice(0, 3).map((item, index) => <li key={item.labId}>
        <div className="profile-recommendation-card-topline">
          <span>{index === 0 ? "#1 Best match" : "#" + (index + 1)} · {item.totalScore.toFixed(1)} research match</span>
        </div>
        <h3>{item.labName}</h3>
        <p>{item.professorName} · {item.university}</p>
        <p>{item.department}</p>
        <p>{item.shortReason}</p>
        <div className="profile-recommendation-match">
          <strong>Matched research</strong>
          <p>{item.matchedKeywords.join(", ") || "No exact keyword overlap"}</p>
        </div>
        {item.missingKeywords.length > 0 && <p><strong>Adjacent opportunities:</strong> {item.missingKeywords.join(", ")}</p>}
        <details>
          <summary>How this score was calculated</summary>
          <ul>
            {Object.entries(item.scoreBreakdown).map(([name, part]) => <li key={name}>
              {name.replaceAll("_", " ")}: {part.available ? part.score + " / " + part.maxScore : "Unavailable"}
            </li>)}
          </ul>
        </details>
        {item.evidence.length > 0 && <details>
          <summary>Matching evidence</summary>
          <ul>{item.evidence.map((evidence, evidenceIndex) => <li key={evidence.type + "-" + evidenceIndex}>{evidence.text}</li>)}</ul>
        </details>}
        <p><strong>Suggested next step:</strong> {item.recommendedAction}</p>
        {item.warnings.length > 0 && <p>{item.warnings.join(" ")}</p>}
        <Link href={"/professors/" + item.labId}>View professor details</Link>
      </li>)}
    </ol>
  </section>;
}
