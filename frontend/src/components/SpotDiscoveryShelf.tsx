import { useEffect, useState } from "react";
import type { Spot, SpotDiscoveryResults } from "../types";
import { Icon } from "./Icon";

type SpotDiscoveryShelfProps = {
  savedIds: string[];
  onSaveSpot: (spot: Spot) => void;
  onSaveSpots: (spots: Spot[]) => void;
};

async function fetchDiscovery(params: URLSearchParams, signal?: AbortSignal): Promise<SpotDiscoveryResults> {
  const response = await fetch(`/api/discover/spots?${params.toString()}`, { signal });
  if (!response.ok) {
    const body = (await response.json()) as { detail?: string };
    throw new Error(body.detail ?? "スポット候補を取得できませんでした。");
  }
  return (await response.json()) as SpotDiscoveryResults;
}

function SpotCandidateCard({
  spot,
  saved,
  onSave,
}: {
  spot: Spot;
  saved: boolean;
  onSave: () => void;
}) {
  return (
    <article className="spot-discovery-card">
      <img src={spot.image_url} alt={`${spot.prefecture}のサンプル風景`} loading="lazy" />
      <div className="spot-discovery-card-copy">
        <span className="spot-discovery-region"><Icon name="pin" size={12} />{spot.prefecture} · {spot.category}</span>
        <h3>{spot.title}</h3>
        <p>{spot.description}</p>
        <button className={saved ? "spot-discovery-save is-saved" : "spot-discovery-save"} disabled={saved} onClick={onSave} type="button">
          <Icon name={saved ? "heart" : "bookmark"} size={14} />{saved ? "行きたいに保存済み" : "行きたいに保存"}
        </button>
      </div>
    </article>
  );
}

export function SpotDiscoveryShelf({ savedIds, onSaveSpot, onSaveSpots }: SpotDiscoveryShelfProps) {
  const [categories, setCategories] = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [inspiration, setInspiration] = useState<Spot[]>([]);
  const [results, setResults] = useState<Spot[]>([]);
  const [total, setTotal] = useState(0);
  const [category, setCategory] = useState("");
  const [region, setRegion] = useState("");
  const [loadingInspiration, setLoadingInspiration] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspirationError, setInspirationError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadInspiration() {
      setLoadingInspiration(true);
      setInspirationError(null);
      try {
        const response = await fetchDiscovery(new URLSearchParams({ limit: "3", random_order: "true" }), controller.signal);
        setInspiration(response.items);
        setCategories(response.categories);
        setRegions(response.regions);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setInspirationError(cause instanceof Error ? cause.message : "おすすめを取得できませんでした。");
        }
      } finally {
        if (!controller.signal.aborted) setLoadingInspiration(false);
      }
    }
    void loadInspiration();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!category && !region) {
      setResults([]);
      setTotal(0);
      setError(null);
      return;
    }

    const controller = new AbortController();
    async function loadFilteredSpots() {
      setLoadingResults(true);
      setError(null);
      const params = new URLSearchParams({ limit: "100" });
      if (category) params.set("category", category);
      if (region) params.set("region", region);
      try {
        const response = await fetchDiscovery(params, controller.signal);
        setResults(response.items);
        setTotal(response.total);
        setCategories(response.categories);
        setRegions(response.regions);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "候補の検索に失敗しました。");
      } finally {
        if (!controller.signal.aborted) setLoadingResults(false);
      }
    }
    void loadFilteredSpots();
    return () => controller.abort();
  }, [category, region]);

  async function refreshInspiration() {
    setLoadingInspiration(true);
    setInspirationError(null);
    try {
      const response = await fetchDiscovery(new URLSearchParams({ limit: "3", random_order: "true" }));
      setInspiration(response.items);
      setCategories(response.categories);
      setRegions(response.regions);
    } catch (cause) {
      setInspirationError(cause instanceof Error ? cause.message : "おすすめを取得できませんでした。");
    } finally {
      setLoadingInspiration(false);
    }
  }

  const unsavedResults = results.filter((spot) => !savedIds.includes(spot.id));

  return (
    <section className="spot-discovery-shelf" aria-label="スポットを探す">
      <div className="spot-discovery-heading">
        <div>
          <span className="eyebrow"><Icon name="sparkle" size={13} /> FIND YOUR NEXT DETOUR</span>
          <h2>今日のインスピレーション</h2>
          <p>気分にぴったりの景色や、まだ知らない地域の魅力を見つけよう。</p>
        </div>
        <button className="spot-discovery-refresh" disabled={loadingInspiration} onClick={() => void refreshInspiration()} type="button">
          <Icon name="sparkle" size={14} />{loadingInspiration ? "探しています…" : "別のおすすめを見る"}
        </button>
      </div>

      {inspirationError && <p className="spot-discovery-error" role="alert">{inspirationError}</p>}
      {loadingInspiration && inspiration.length === 0 && <p className="spot-discovery-status" role="status">おすすめを探しています…</p>}
      <div className="spot-discovery-grid">
        {inspiration.map((spot) => (
          <SpotCandidateCard key={spot.id} onSave={() => onSaveSpot(spot)} saved={savedIds.includes(spot.id)} spot={spot} />
        ))}
      </div>

      <div className="spot-discovery-filter">
        <div className="spot-discovery-filter-heading">
          <div><span className="eyebrow">BROWSE BY PLACE OR THEME</span><h3>地域・テーマから探す</h3></div>
          <span>候補をまとめて行きたいリストへ保存できます。</span>
        </div>
        <div className="spot-discovery-filter-controls">
          <label>
            <span>テーマ・カテゴリ</span>
            <select onChange={(event) => setCategory(event.target.value)} value={category}>
              <option value="">すべてのテーマ</option>
              {categories.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span>地域</span>
            <select onChange={(event) => setRegion(event.target.value)} value={region}>
              <option value="">すべての地域</option>
              {regions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          {(category || region) && <button className="spot-discovery-clear" onClick={() => { setCategory(""); setRegion(""); }} type="button">条件をクリア</button>}
        </div>
        {region && results.length > 0 && (
          <div className="spot-discovery-bulk-row">
            <span>{region}の候補 {total}件 · 未保存 {unsavedResults.length}件</span>
            <button className="button-primary" disabled={unsavedResults.length === 0 || loadingResults} onClick={() => onSaveSpots(unsavedResults)} type="button">
              <Icon name="bookmark" size={14} />{unsavedResults.length > 0 ? "この地域の候補をまとめて保存" : "すべて保存済み"}
            </button>
          </div>
        )}
        {loadingResults && <p className="spot-discovery-status" role="status">候補を検索しています…</p>}
        {error && <p className="spot-discovery-error" role="alert">{error}</p>}
        {!loadingResults && (category || region) && results.length === 0 && !error && (
          <p className="spot-discovery-status">この条件に合う候補はありません。</p>
        )}
        {!loadingResults && results.length > 0 && (
          <>
            <p className="spot-discovery-result-count">{total}件の候補</p>
            <div className="spot-discovery-grid">
              {results.map((spot) => (
                <SpotCandidateCard key={spot.id} onSave={() => onSaveSpot(spot)} saved={savedIds.includes(spot.id)} spot={spot} />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
