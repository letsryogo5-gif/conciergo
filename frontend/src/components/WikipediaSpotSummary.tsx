import { useState } from "react";
import type { Spot, WikipediaSummary as WikipediaSummaryType } from "../types";
import { AttributionCredits } from "./AttributionCredits";

type WikipediaSpotSummaryProps = {
  spot: Spot;
  label?: string;
};

export function WikipediaSpotSummary({ spot, label }: WikipediaSpotSummaryProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [summary, setSummary] = useState<WikipediaSummaryType | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggleSummary() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (loaded || loading) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/spots/${encodeURIComponent(spot.id)}/knowledge`);
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Wikipediaの概要を読み込めませんでした。");
      }
      setSummary((await response.json()) as WikipediaSummaryType | null);
      setLoaded(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Wikipediaの概要を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="wikipedia-summary">
      <button
        aria-expanded={open}
        className="wikipedia-summary-toggle"
        onClick={() => void toggleSummary()}
        type="button"
      >
        <span>{label ?? (spot.is_world_heritage ? "世界遺産の背景を知る" : "豆知識をもっと知る")}</span>
        <span>{open ? "閉じる −" : "Wikipediaを読む ＋"}</span>
      </button>
      {open && (
        <div className="wikipedia-summary-content" aria-live="polite">
          {loading && <p role="status">Wikipediaから概要を読み込んでいます…</p>}
          {error && <p className="wikipedia-summary-error" role="alert">{error}</p>}
          {!loading && !error && loaded && !summary && (
            <p role="status">この場所に関連するWikipedia記事が見つかりませんでした。</p>
          )}
          {summary && (
            <>
              <h4>{summary.title}</h4>
              <p>{summary.extract}</p>
              <a href={summary.article_url} target="_blank" rel="noreferrer">
                Wikipediaで記事を読む
              </a>
              <AttributionCredits
                credits={[{
                  label: `Wikipedia contributors · ${summary.title}`,
                  url: summary.article_url,
                  licenseName: "CC BY-SA 4.0",
                  licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/",
                }]}
                label="本文の出典"
              />
            </>
          )}
        </div>
      )}
    </section>
  );
}
