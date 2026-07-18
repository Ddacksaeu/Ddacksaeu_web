"use client";

import { useSyncExternalStore } from "react";
import { z } from "zod";

import styles from "./scheduler-checklist.module.css";

const TASKS = ["Review application guidelines", "Prepare professor-specific CV versions", "Send outreach email", "Prepare interview questions"] as const;
const taskSchema = z.enum(TASKS);
const completedTasksSchema = z.array(taskSchema);
const CHECKLIST_KEY = "ddaksaewoo:scheduler-checklist";
const CHECKLIST_EVENT = "ddaksaewoo:scheduler-checklist-change";
const DEFAULT_COMPLETED = JSON.stringify([TASKS[0]]);

type Task = z.infer<typeof taskSchema>;

function getSnapshot(): string {
  return window.localStorage.getItem(CHECKLIST_KEY) ?? DEFAULT_COMPLETED;
}

function getServerSnapshot(): string {
  return DEFAULT_COMPLETED;
}

function parseCompleted(snapshot: string): readonly Task[] {
  try {
    const parsed = completedTasksSchema.safeParse(JSON.parse(snapshot));
    return parsed.success ? parsed.data : [TASKS[0]];
  } catch (error) {
    if (error instanceof SyntaxError) return [TASKS[0]];
    throw error;
  }
}

function subscribe(onChange: () => void): () => void {
  function handleStorage(event: StorageEvent): void {
    if (event.key === CHECKLIST_KEY) onChange();
  }

  window.addEventListener("storage", handleStorage);
  window.addEventListener(CHECKLIST_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", handleStorage);
    window.removeEventListener(CHECKLIST_EVENT, onChange);
  };
}

export function SchedulerChecklist() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const completed = parseCompleted(snapshot);

  function toggle(task: Task): void {
    const nextCompleted = completed.includes(task)
      ? completed.filter((item) => item !== task)
      : [...completed, task];
    window.localStorage.setItem(CHECKLIST_KEY, JSON.stringify(nextCompleted));
    window.dispatchEvent(new Event(CHECKLIST_EVENT));
  }

  return (
    <section className={styles["box"]} aria-labelledby="checklist-title">
      <h3 id="checklist-title">This week’s checklist</h3>
      <p>{completed.length} / {TASKS.length} complete</p>
      <ul className={styles["list"]}>{TASKS.map((task) => <li key={task}><label className={styles["item"] + (completed.includes(task) ? " " + styles["done"] : "")}><input checked={completed.includes(task)} type="checkbox" onChange={() => toggle(task)} />{task}</label></li>)}</ul>
    </section>
  );
}
