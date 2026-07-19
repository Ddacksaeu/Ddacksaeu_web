"use client";

import { HTTPError } from "ky";
import { useEffect, useState } from "react";

import { getRecommendations, type Recommendation } from "./recommendations-api";
import { RecommendationResults } from "./recommendation-results";

type Properties = Readonly<{ analysisId: string }>;

type RecommendationState =
  | Readonly<{ kind: "loading" }>
  | Readonly<{ kind: "ready"; analysisId: string; items: readonly Recommendation[] }>
  | Readonly<{ kind: "error"; analysisId: string; message: string }>;

function getErrorMessage(error: unknown): string {
  if (error instanceof HTTPError && (error.response.status === 401 || error.response.status === 403)) {
    return "Your session has expired. Log in again to view professor matches.";
  }
  if (error instanceof HTTPError && error.response.status === 409) {
    return "This CV analysis is not ready for professor matching yet.";
  }
  return "Could not load professor matches. Try again.";
}

export function CvRecommendations({ analysisId }: Properties) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<RecommendationState>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    void getRecommendations()
      .then((items) => {
        if (active) setState({ kind: "ready", analysisId, items });
      })
      .catch((error: unknown) => {
        if (active) setState({ kind: "error", analysisId, message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [analysisId, attempt]);
  if (state.kind !== "loading" && state.analysisId !== analysisId) return <section className="catalog-empty" aria-live="polite"><h2>Finding your best professor matches…</h2><p>Comparing CV keywords with current lab research.</p></section>;


  switch (state.kind) {
    case "loading":
      return <section className="catalog-empty" aria-live="polite"><h2>Finding your best professor matches…</h2><p>Comparing CV keywords with current lab research.</p></section>;
    case "ready":
      return <RecommendationResults items={state.items} />;
    case "error":
      return <section className="catalog-empty" role="alert">
        <h2>Professor matching is unavailable</h2>
        <p>{state.message}</p>
        <button className="secondary-button" type="button" onClick={() => { setState({ kind: "loading" }); setAttempt((current) => current + 1); }}>
          Try again
        </button>
      </section>;
  }
}
