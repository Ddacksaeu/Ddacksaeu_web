"use client";

type ErrorPageProperties = Readonly<{
  error: Error & { digest?: string };
  reset: () => void;
}>;

export default function ErrorPage({ reset }: ErrorPageProperties) {
  return (
    <main className="page-shell">
      <section aria-labelledby="error-title" className="entry-panel recovery-panel">
        <p className="eyebrow">WORKSPACE ERROR</p>
        <h1 id="error-title">Something went wrong</h1>
        <p className="intro">Your saved work is still available. Try loading this screen again.</p>
        <button className="primary-button" onClick={reset} type="button">Try again</button>
      </section>
    </main>
  );
}
