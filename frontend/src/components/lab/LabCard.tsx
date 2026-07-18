import { Link } from "@tanstack/react-router";
import { ExternalLink, Heart, Building2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/lib/app-state";
import type { LabListItem } from "@/lib/api/labs";
import type { Lab } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export function MatchBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-[color:var(--surface)]">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[color:var(--deep)] to-[color:var(--point)]"
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-medium tabular-nums text-[color:var(--navy)]">{score}%</span>
    </div>
  );
}

export function LabCard({
  lab,
  variant = "grid",
  highlight,
}: {
  lab: Lab | LabListItem;
  variant?: "grid" | "list";
  highlight?: string[];
}) {
  const { isFavorite, toggleFavorite } = useAppState();
  const apiLab = "professorName" in lab;
  const fav = apiLab ? lab.isFavorite : isFavorite(lab.id);
  const professor = apiLab ? lab.professorName : lab.professor;
  const homepage = apiLab ? lab.homepageUrl : lab.homepage;
  const score = apiLab ? lab.recommendationScore : lab.matchScore;
  const recentTopics = apiLab ? [] : lab.recentTopics;
  const isMatch = (keyword: string) =>
    highlight?.some(
      (item) =>
        item.toLowerCase() === keyword.toLowerCase() ||
        keyword.toLowerCase().includes(item.toLowerCase()),
    );

  return (
    <article
      className={cn(
        "group relative flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 transition-shadow hover:shadow-[0_8px_24px_-16px_oklch(0.24_0.05_260/0.35)]",
        variant === "list" && "lg:flex-row lg:items-start lg:gap-6",
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Building2 className="h-3.5 w-3.5" />
              <span>{lab.department}</span>
              <span className="text-border">쨌</span>
              <span className="text-[color:var(--deep)]">{lab.field}</span>
            </div>
            <h3 className="mt-2 truncate text-base font-semibold tracking-tight text-[color:var(--navy)]">
              <Link to="/lab/$id" params={{ id: lab.id }} className="hover:underline">
                {lab.name}
              </Link>
            </h3>
            <p className="mt-0.5 text-sm text-muted-foreground">{professor}</p>
          </div>
          <button
            type="button"
            aria-label={fav ? "Remove from saved" : "Save lab"}
            onClick={() => toggleFavorite(lab.id)}
            className={cn(
              "grid h-9 w-9 shrink-0 place-items-center rounded-full border transition-colors",
              fav
                ? "border-[color:var(--point)]/40 bg-[color:var(--point)]/10 text-[color:var(--point)]"
                : "border-border text-muted-foreground hover:text-[color:var(--point)]",
            )}
          >
            <Heart className={cn("h-4 w-4", fav && "fill-current")} strokeWidth={1.8} />
          </button>
        </div>

        <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-foreground/80">
          {lab.summary ?? "No verified lab summary is available yet."}
        </p>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {lab.keywords.slice(0, 5).map((keyword) => (
            <Badge
              key={keyword}
              variant="outline"
              className={cn(
                "rounded-full border-border bg-[color:var(--surface)] font-normal text-foreground/70",
                isMatch(keyword) &&
                  "border-[color:var(--point)]/40 bg-[color:var(--point)]/10 text-[color:var(--deep)]",
              )}
            >
              {keyword}
            </Badge>
          ))}
        </div>

        <div className="mt-4 text-xs text-muted-foreground">
          {recentTopics.length > 0 ? (
            <>
              <span className="font-medium text-foreground/70">Recent topics 쨌 </span>
              {recentTopics.slice(0, 2).join(" / ")}
            </>
          ) : (
            <>Last updated 쨌 {new Date(lab.updatedAt).toLocaleDateString()}</>
          )}
        </div>
      </div>

      <div
        className={cn(
          "flex items-center justify-between gap-3 border-t border-border pt-4",
          variant === "list" &&
            "lg:w-56 lg:flex-col lg:items-stretch lg:justify-start lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0",
        )}
      >
        {score !== null ? (
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Profile match
            </div>
            <div className="mt-1">
              <MatchBar score={score} />
            </div>
          </div>
        ) : (
          <div className="text-xs text-muted-foreground">No profile score yet</div>
        )}
        <div className="flex gap-2">
          {homepage ? (
            <Button asChild size="sm" variant="outline" className="rounded-full">
              <a href={homepage} target="_blank" rel="noreferrer" aria-label="Open homepage">
                <ExternalLink className="h-3.5 w-3.5" />
                Website
              </a>
            </Button>
          ) : null}
          <Button
            asChild
            size="sm"
            className="rounded-full bg-[color:var(--deep)] hover:bg-[color:var(--navy)]"
          >
            <Link to="/lab/$id" params={{ id: lab.id }}>
              Details
            </Link>
          </Button>
        </div>
      </div>
    </article>
  );
}
