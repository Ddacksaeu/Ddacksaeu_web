import { createFileRoute, Link } from "@tanstack/react-router";
import { Heart, X, ArrowRight, GitCompareArrows } from "lucide-react";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { LabCard, MatchBar } from "@/components/lab/LabCard";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { LABS } from "@/lib/mock-data";
import { useAppState } from "@/lib/app-state";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/favorites")({
  component: FavoritesPage,
  head: () => ({
    meta: [
      { title: "Saved Labs | Ddaksaeu" },
      { name: "description", content: "Compare and organize your saved labs." },
    ],
  }),
});

function FavoritesPage() {
  const { favorites, compareIds, toggleCompare, clearCompare } = useAppState();
  const [compareOpen, setCompareOpen] = useState(false);
  const savedLabs = LABS.filter((lab) => favorites.includes(lab.id));
  const compareLabs = LABS.filter((lab) => compareIds.includes(lab.id));

  return (
    <AppShell
      title="Saved Labs"
      description={`Saved labs: ${savedLabs.length}. Compare up to 3 labs.`}
      actions={
        <Button
          disabled={compareLabs.length < 2}
          onClick={() => setCompareOpen(true)}
          className="gap-2 rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)] disabled:opacity-50"
        >
          <GitCompareArrows className="h-4 w-4" />
          Compare ({compareLabs.length})
        </Button>
      }
    >
      {savedLabs.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-border bg-white p-12 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[color:var(--surface)] text-[color:var(--deep)]">
            <Heart className="h-6 w-6" />
          </div>
          <h3 className="mt-4 text-base font-semibold text-[color:var(--navy)]">
            No saved labs yet
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Select the heart on any lab card to save it for later.
          </p>
          <Button
            asChild
            className="mt-4 gap-2 rounded-full bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
          >
            <Link to="/">
              Explore labs <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </section>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {savedLabs.map((lab) => {
              const inCompare = compareIds.includes(lab.id);
              const compareFull = compareIds.length >= 3 && !inCompare;
              return (
                <LabCard
                  key={lab.id}
                  lab={lab}
                  headerActions={
                    <label
                      className={cn(
                        "flex cursor-pointer items-center gap-1.5 rounded-full border border-border bg-white px-2.5 py-1 text-xs text-foreground/80 shadow-sm",
                        inCompare &&
                          "border-[color:var(--point)] bg-[color:var(--point)]/10 text-[color:var(--deep)]",
                        compareFull && "cursor-not-allowed opacity-50",
                      )}
                    >
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={inCompare}
                        disabled={compareFull}
                        onChange={() => toggleCompare(lab.id)}
                      />
                      <span
                        className={cn(
                          "grid h-3.5 w-3.5 place-items-center rounded-sm border",
                          inCompare
                            ? "border-[color:var(--point)] bg-[color:var(--point)] text-white"
                            : "border-border",
                        )}
                      >
                        {inCompare && <span className="text-[9px]">&#10003;</span>}
                      </span>
                      Compare
                    </label>
                  }
                />
              );
            })}
          </div>
          {compareLabs.length > 0 && (
            <div className="fixed bottom-16 left-0 right-0 z-20 flex justify-center px-4 lg:bottom-6 lg:pl-64">
              <div className="flex w-full max-w-3xl items-center gap-3 rounded-2xl border border-border bg-white p-3 shadow-[0_10px_32px_-16px_oklch(0.24_0.05_260/0.35)]">
                <div className="text-xs text-muted-foreground">Comparison list</div>
                <div className="flex flex-1 flex-wrap items-center gap-2">
                  {compareLabs.map((lab) => (
                    <span
                      key={lab.id}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-[color:var(--surface)] px-2.5 py-1 text-xs"
                    >
                      {lab.name}
                      <button
                        onClick={() => toggleCompare(lab.id)}
                        aria-label="Remove from comparison"
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <Button variant="ghost" size="sm" onClick={clearCompare} className="rounded-full">
                  Clear
                </Button>
                <Button
                  disabled={compareLabs.length < 2}
                  onClick={() => setCompareOpen(true)}
                  className="rounded-full bg-[color:var(--point)] hover:bg-[color:var(--deep)]"
                >
                  Compare
                </Button>
              </div>
            </div>
          )}
        </>
      )}
      <Dialog open={compareOpen} onOpenChange={setCompareOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Compare labs</DialogTitle>
            <DialogDescription>{compareLabs.length} labs side by side.</DialogDescription>
          </DialogHeader>
          <div className="overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0 text-sm">
              <thead>
                <tr>
                  <th className="w-32 border-b border-border bg-[color:var(--surface)] px-3 py-2 text-left text-xs font-medium uppercase tracking-widest text-muted-foreground">
                    Category
                  </th>
                  {compareLabs.map((lab) => (
                    <th
                      key={lab.id}
                      className="border-b border-border bg-[color:var(--surface)] px-3 py-2 text-left text-sm font-semibold text-[color:var(--navy)]"
                    >
                      {lab.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <Row label="Professor" values={compareLabs.map((lab) => lab.professor)} />
                <Row label="Department" values={compareLabs.map((lab) => lab.department)} />
                <Row label="Research fields" values={compareLabs.map((lab) => lab.field)} />
                <tr>
                  <td className="border-b border-border px-3 py-3 align-top text-xs text-muted-foreground">
                    Profile match
                  </td>
                  {compareLabs.map((lab) => (
                    <td key={lab.id} className="border-b border-border px-3 py-3 align-top">
                      <MatchBar score={lab.matchScore} />
                    </td>
                  ))}
                </tr>
                <Row
                  label="Recent topics"
                  values={compareLabs.map((lab) => lab.recentTopics.slice(0, 2).join(" / "))}
                />
                <tr>
                  <td className="px-3 py-3 align-top text-xs text-muted-foreground">Website</td>
                  {compareLabs.map((lab) => (
                    <td key={lab.id} className="px-3 py-3 align-top">
                      <a
                        href={lab.homepage}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[color:var(--deep)] hover:underline"
                      >
                        Visit
                      </a>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

function Row({ label, values }: { label: string; values: string[] }) {
  return (
    <tr>
      <td className="border-b border-border px-3 py-3 align-top text-xs text-muted-foreground">
        {label}
      </td>
      {values.map((value, index) => (
        <td key={index} className="border-b border-border px-3 py-3 align-top text-foreground/85">
          {value}
        </td>
      ))}
    </tr>
  );
}
