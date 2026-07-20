import Image from "next/image";
import Link from "next/link";

import { AppHeader } from "../src/components/app-header";
import { fetchBackendLabs, type LabSummary } from "../src/server/backend/labs";

const UNIVERSITIES = [
  {
    name: "Seoul National University",
    logo: "/images/universities/snu.png",
    width: 826,
    height: 189,
  },
  {
    name: "KAIST",
    logo: "/images/universities/kaist.png",
    width: 307,
    height: 89,
  },
  {
    name: "POSTECH",
    logo: "/images/universities/postech.png",
    width: 493,
    height: 72,
  },
  {
    name: "Yonsei University",
    logo: "/images/universities/yonsei.png",
    width: 784,
    height: 236,
  },
  {
    name: "Korea University",
    logo: "/images/universities/korea.png",
    width: 686,
    height: 185,
  },
] as const;
const TRENDING_TOPICS = [
  "Computer Vision",
  "Generative AI",
  "HCI",
  "Robotics",
  "Natural Language Processing",
] as const;
export default async function HomePage() {
  let featuredLabs: readonly LabSummary[] = [];
  try {
    featuredLabs = (await fetchBackendLabs()).items.slice(0, 3);
  } catch (error) {
    if (!(error instanceof Error)) throw error;
  }

  return (
    <main className="site-shell home-discovery">
      <AppHeader />
      <section className="home-search-hero">
        <div className="home-search-copy">
          <p className="kicker">GRADUATE LAB DISCOVERY</p>
          <h1>
            <span className="home-title-desktop">
              Find professors who match
              <br />
              your research direction
            </span>
            <span className="home-title-mobile">
              Find professors who
              <br />
              match your research
              <br />
              direction
            </span>
          </h1>
          <p>
            Search by research topic, not just university. Use your interests
            and CV to move from professor discovery to{" "}
            <span className="keep-phrase">application planning.</span>
          </p>
          <form action="/professors" className="home-search-box" method="get">
            <label htmlFor="home-query">Lab or research keyword</label>
            <div>
              <span aria-hidden="true">⌕</span>
              <input
                id="home-query"
                name="q"
                placeholder="e.g. Computer Vision, Multimodal, HCI"
              />
              <button type="submit">Find professors</button>
            </div>
          </form>
          <div
            className="home-topic-links"
            aria-label="Popular research topics"
          >
            <span>Popular topics</span>
            {TRENDING_TOPICS.map((topic) => (
              <Link
                href={`/professors?q=${encodeURIComponent(topic)}`}
                key={topic}
              >
                {topic}
              </Link>
            ))}
          </div>
        </div>
        <aside className="home-radar" aria-labelledby="radar-title">
          <div className="home-radar-heading">
            <div>
              <span>This week’s lab radar</span>
              <h2 id="radar-title">Labs to explore first</h2>
            </div>
            <Link href="/professors">View all</Link>
          </div>
          <ol>
            {featuredLabs.map((lab, index) => (
              <li key={lab.id}>
                <Link href={`/professors/${lab.id}`}>
                  <span className="home-rank">0{index + 1}</span>
                  <div>
                    <strong>{lab.name}</strong>
                    <small>
                      {lab.university} · {lab.professorName}
                    </small>
                  </div>
                  <span aria-hidden="true">→</span>
                </Link>
              </li>
            ))}
          </ol>
          <p>
            Verify recruitment and research details on the official source.
          </p>
        </aside>
      </section>
      <nav
        className="home-journey"
        aria-label="Graduate school planning shortcuts"
      >
        <Link href="/professors">
          <span>01</span>
          <div>
            <strong>Professor search</strong>
            <small>Find candidates by research topic</small>
          </div>
        </Link>
        <Link href="/cv">
          <span>02</span>
          <div>
            <strong>CV analysis</strong>
            <small>Organize experience and keywords</small>
          </div>
        </Link>
        <Link href="/calendar">
          <span>03</span>
          <div>
            <strong>Admissions calendar</strong>
            <small>Track every deadline</small>
          </div>
        </Link>
        <Link href="/profile">
          <span>04</span>
          <div>
            <strong>Profile</strong>
            <small>Continue saved work</small>
          </div>
        </Link>
      </nav>
      <section className="home-editorial" aria-labelledby="editorial-title">
        <div className="home-section-heading">
          <div>
            <p className="kicker">CURATED RESEARCH</p>
            <h2 id="editorial-title">Discover professors by research topic</h2>
          </div>
          <Link href="/professors">Explore all professors →</Link>
        </div>
        <div className="home-editorial-grid">
          <Link
            className="home-lead-story"
            href="/professors?q=Computer%20Vision"
          >
            <span>This week’s theme</span>
            <div>
              <p>VISION · MULTIMODAL</p>
              <h3>
                Beyond images
                <br />
                Research that understands the world
              </h3>
              <small>Explore Computer Vision and Multimodal labs</small>
            </div>
            <strong aria-hidden="true">↗</strong>
          </Link>
          <div className="home-topic-list">
            {[
              [
                "01",
                "Generative AI",
                "From language models to learning intelligence",
                "Generative AI",
              ],
              [
                "02",
                "Technology for people",
                "HCI and accessibility research",
                "HCI",
              ],
              [
                "03",
                "AI in the physical world",
                "Robotics and reinforcement learning",
                "Robotics",
              ],
            ].map(([number, title, description, query]) => (
              <Link
                href={`/professors?q=${encodeURIComponent(query ?? "")}`}
                key={number}
              >
                <span>{number}</span>
                <div>
                  <strong>{title}</strong>
                  <small>{description}</small>
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </div>
      </section>
      <section
        className="university-marquee-section"
        aria-labelledby="university-marquee-title"
      >
        <div className="university-marquee-heading">
          <div>
            <p className="kicker">UNIVERSITY DISCOVERY</p>
            <h2 id="university-marquee-title">
              Explore labs at leading universities
            </h2>
          </div>
        </div>
        <div
          className="university-marquee"
          tabIndex={0}
          aria-label="University logo carousel. Focus to pause the animation."
        >
          <div className="university-marquee-track">
            {[0, 1].map((copyIndex) => (
              <ul
                aria-hidden={copyIndex === 1 ? true : undefined}
                className="university-marquee-group"
                key={copyIndex}
              >
                {UNIVERSITIES.map((university) => (
                  <li key={`${copyIndex}-${university.name}`}>
                    <Image
                      alt={`${university.name} logo`}
                      height={university.height}
                      sizes="(max-width: 700px) 192px, 220px"
                      src={university.logo}
                      width={university.width}
                    />
                  </li>
                ))}
              </ul>
            ))}
          </div>
        </div>
      </section>
      <section className="home-bottom-cta">
        <div>
          <p>Build your research profile</p>
          <h2>
            Get professor recommendations
            <br />
            grounded in your experience.
          </h2>
        </div>
        <div className="home-bottom-actions">
          <Link className="primary-cta" href="/profile">
            Create my profile
          </Link>
        </div>
      </section>
    </main>
  );
}
