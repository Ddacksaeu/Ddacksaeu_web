"use client";

import ky from "ky";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AppHeader } from "../../src/components/app-header";
import { completeDemoOnboarding } from "../../src/features/auth/demo-session";
import styles from "../../src/styles/auth.module.css";

export default function OnboardingPage() {
  const router = useRouter();
  const [cvFileName, setCvFileName] = useState("");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  async function completeSetup(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const researchInterests = String(form.get("researchInterests") ?? "")
      .split(/[,\n]/)
      .map((value) => value.trim())
      .filter(Boolean);
    setSaving(true);
    setStatus("Saving your setup.");
    try {
      await ky.put("/api/profile", {
        json: {
          consentToStorage: true,
          displayName: "Researcher",
          researchInterests,
          preferredUniversity: String(form.get("preferredUniversity") ?? ""),
          applicationTerm: String(form.get("applicationTerm") ?? ""),
          degreeProgram: String(form.get("degreeProgram") ?? ""),
        },
      });
      const cv = form.get("cv");
      if (cv instanceof File && cv.size > 0) {
        const body = new FormData();
        body.set("cv", cv);
        await ky.post("/api/profile", { body });
      }
      completeDemoOnboarding(window.localStorage);
      router.push("/dashboard");
    } catch {
      setStatus("Could not save your setup. Please try again.");
      setSaving(false);
    }
  }

  return (
    <div className="site-shell">
      <AppHeader setup />
      <main className={styles["shell"]}>
        <form className={styles["card"] + " " + styles["cardWide"]} onSubmit={(event) => void completeSetup(event)}>
          <p className={styles["eyebrow"]}>INITIAL SETUP</p>
          <h1>Tell us what you are looking for</h1>
          <p className={styles["lead"]}>We only use these details for professor recommendations and deadlines. You can update them anytime in Profile.</p>
          <div className={styles["grid"]}>
            <label className={styles["field"]}>Preferred university<select defaultValue="" name="preferredUniversity" required><option disabled value="">Select a university</option><option>Seoul National University</option><option>KAIST</option><option>POSTECH</option><option>Yonsei University</option></select></label>
            <label className={styles["field"]}>Application term<select defaultValue="Spring 2027" name="applicationTerm"><option>Spring 2027</option><option>Fall 2027</option></select></label>
            <label className={styles["field"] + " " + styles["full"]}>Target major and research interests<textarea name="researchInterests" placeholder="e.g. Computer Vision, Multimodal Learning, Medical AI" required /></label>
            <fieldset className={styles["field"] + " " + styles["full"]}><legend>Degree program</legend><div className={styles["course"]}><label><input name="degreeProgram" type="radio" value="Master's" required />Master’s</label><label><input name="degreeProgram" type="radio" value="PhD" />PhD</label><label><input name="degreeProgram" type="radio" value="Integrated MS/PhD" />Integrated MS/PhD</label></div></fieldset>
            <label className={styles["field"] + " " + styles["full"]}>Upload CV / portfolio<span className={styles["filePicker"]}><input aria-describedby="onboarding-cv-help" className={styles["fileInput"]} accept="application/pdf,text/plain" name="cv" type="file" onChange={(event) => setCvFileName(event.target.files?.item(0)?.name ?? "")} /><span className={styles["fileButton"]}>Choose file</span><span className={styles["fileName"]}>{cvFileName || "No file selected"}</span></span><span className={styles["help"]} id="onboarding-cv-help">Optional · PDF or TXT · Up to 5 MB</span></label>
          </div>
          <button className={styles["primary"]} disabled={saving} type="submit">{saving ? "Saving setup" : "Complete setup"}</button>
          <p className={styles["formStatus"]} aria-live="polite">{status}</p>
        </form>
      </main>
    </div>
  );
}
