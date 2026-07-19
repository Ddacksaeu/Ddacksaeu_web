import Link from "next/link";

import { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog";
import { matchLabsByTopics } from "../recommendations/match-labs";

type ProfileRecommendationsProperties = Readonly<{
  keywords: readonly string[];
}>;

export function ProfileRecommendations({ keywords }: ProfileRecommendationsProperties) {
  const recommendations = matchLabsByTopics(LAB_CATALOG_FIXTURES, keywords);

  return (
    <section className="profile-recommendation" aria-labelledby="profile-recommendation-title">
      <div className="profile-recommendation-heading">
        <div>
          <p>Keyword similarity recommendations</p>
          <h2 id="profile-recommendation-title">Professors close to your interests</h2>
          <span>This score reflects overlap between saved keywords and current research topics. It is not an admission probability.</span>
        </div>
        <Link href="/professors">Explore all professors</Link>
      </div>
      {keywords.length === 0 ? (
        <div className="profile-recommendation-empty"><strong>Add research keywords</strong><p>Add keywords in Edit profile to see recommendations.</p></div>
      ) : recommendations.length === 0 ? (
        <div className="profile-recommendation-empty"><strong>No professors have an exact keyword match</strong><p>Try a research area filter or different keyword wording in Professor search.</p><Link href="/professors">Search with filters</Link></div>
      ) : (
        <ol className="profile-recommendation-list">
          {recommendations.map(({ lab, matchingTopics }) => (
            <li key={lab.id}>
              <div className="profile-recommendation-card-topline"><span>Research match</span><small>{lab.institution}</small></div>
              <h3>{lab.labName}</h3><p>{lab.professor}</p>
              <div className="profile-recommendation-match"><strong>{matchingTopics.length} matching keywords</strong><span>{matchingTopics.join(" · ")}</span></div>
              <Link href={"/professors/" + lab.id}>View professor details</Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
