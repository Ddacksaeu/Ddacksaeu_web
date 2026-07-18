import Link from "next/link";

export default function NotFound() {
  return (
    <main className="page-shell">
      <section aria-labelledby="not-found-title" className="entry-panel recovery-panel">
        <p className="eyebrow">404 · WORKSPACE NOT FOUND</p>
        <h1 id="not-found-title">Lost your way?</h1>
        <p className="intro">This workspace does not exist or has moved. Start again from the demo.</p>
        <Link className="action-link" href="/">
          Return to demo home
          <span aria-hidden="true">→</span>
        </Link>
      </section>
    </main>
  );
}
