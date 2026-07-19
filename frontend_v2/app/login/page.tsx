"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AppHeader } from "../../src/components/app-header";
import { startDemoSession } from "../../src/features/auth/demo-session";
import styles from "../../src/styles/auth.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [signingUp, setSigningUp] = useState(false);
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true); setStatus("");
    try {
      const response = await fetch(signingUp ? "/api/auth/signup" : "/api/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password"), ...(signingUp ? { name: form.get("name") } : {}) }),
      });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Could not sign in.");
      startDemoSession(window.localStorage);
      router.push("/onboarding");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not sign in."); }
    finally { setSubmitting(false); }
  }
  return (
    <div className="site-shell">
      <AppHeader />
      <main className={styles["shell"]}>
        <form className={styles["card"]} onSubmit={(event) => void submit(event)}>
          <p className={styles["eyebrow"]}>WELCOME TO Ddaksaeu</p>
          <h1>Graduate school planning,<br />all in one place</h1>
          <p className={styles["lead"]}>Manage professor discovery, CV analysis, outreach drafts, and application deadlines in one flow.</p>
          {signingUp ? <label className={styles["field"]}>Name<input autoComplete="name" name="name" required type="text" /></label> : null}
          <label className={styles["field"]}>Email<input autoComplete="email" name="email" placeholder="you@example.com" required type="email" /></label>
          <label className={styles["field"]}>Password<input autoComplete={signingUp ? "new-password" : "current-password"} minLength={signingUp ? 12 : 1} name="password" required type="password" /></label>
          <button className={styles["primary"]} disabled={submitting} type="submit">{submitting ? "Please wait" : signingUp ? "Create account" : "Sign in"}</button>
          <button className={styles["legal"]} onClick={() => { setSigningUp((value) => !value); setStatus(""); }} type="button">{signingUp ? "Already have an account? Sign in" : "New here? Create an account"}</button>
          <p className={styles["formStatus"]} aria-live="polite">{status}</p>
        </form>
      </main>
    </div>
  );
}
