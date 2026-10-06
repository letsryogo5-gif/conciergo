import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { JAPAN_REGIONS, REGION_PIN_THRESHOLD, getRegionForSpot, getRegionalSpotGroups } from "../regions";
import type { JapanRegion } from "../regions";
import type { GeocodingResult, Spot } from "../types";
import { OSMSpotMap } from "./OSMSpotMap";

type RegionalMapProps = {
  spots: Spot[];
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
  onSelectSpot: (spot: Spot) => void;
};

export function RegionalMap({ spots, selectedRegionId, onSelectRegion, onSelectSpot }: RegionalMapProps) {
  const groups = useMemo(() => getRegionalSpotGroups(spots), [spots]);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<GeocodingResult[]>([]);
  const [focusedResult, setFocusedResult] = useState<GeocodingResult | null>(null);
  const mapSpots = selectedRegionId
    ? groups.find((group) => group.region.id === selectedRegionId)?.spots ?? []
    : spots;

  async function searchPlace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 2) {
      setSearchError("地名を2文字以上入力してください。");
      return;
    }

    setSearching(true);
    setSearchError(null);
    setSearchResults([]);
    setFocusedResult(null);
    try {
      const response = await fetch(`/api/geocode?q=${encodeURIComponent(normalizedQuery)}`);
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "地名を検索できませんでした。");
      }
      const results = (await response.json()) as GeocodingResult[];
      setSearchResults(results);
      setFocusedResult(results[0] ?? null);
      if (results.length === 0) {
        setSearchError("地名が見つかりませんでした。別の表記で検索してください。");
      }
    } catch (cause) {
      setSearchError(cause instanceof Error ? cause.message : "地名検索に失敗しました。");
    } finally {
      setSearching(false);
    }
  }

  function selectSpot(spot: Spot) {
    onSelectRegion(getRegionForSpot(spot).id);
    onSelectSpot(spot);
  }

  function clearSearch() {
    setSearchResults([]);
    setFocusedResult(null);
    setSearchError(null);
    setQuery("");
  }

  return (
    <div className="regional-map" aria-label="日本の保存スポットマップ">
      <div className="map-section-heading">
        <div className="map-caption">保存した場所</div>
      </div>
      <form className="map-geocoder" onSubmit={(event) => void searchPlace(event)}>
        <label htmlFor="map-place-query">地名・住所を検索</label>
        <div>
          <input
            autoComplete="off"
            id="map-place-query"
            maxLength={120}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例：京都駅、香川県高松市"
            value={query}
          />
          <button disabled={searching || query.trim().length < 2} type="submit">
            {searching ? <><span className="map-search-spinner" aria-hidden="true" />検索中</> : "検索"}
          </button>
        </div>
      </form>
      {searchError && <p className="map-geocoder-message" role="status">{searchError}</p>}
      {searchResults.length > 0 && (
        <section className="map-geocoder-results" aria-label="地名検索結果">
          <div className="map-geocoder-results-heading">
            <span>検索候補 <strong>{searchResults.length}</strong></span>
            <button onClick={clearSearch} type="button">検索をクリア</button>
          </div>
          <ul>
            {searchResults.map((result) => (
              <li key={result.place_id}>
                <button
                  aria-pressed={focusedResult?.place_id === result.place_id}
                  onClick={() => setFocusedResult(result)}
                  type="button"
                >
                  <span>{result.display_name}</span>
                  <small>{result.category && result.place_type ? `${result.category} · ${result.place_type}` : "OpenStreetMap検索結果"}</small>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <OSMSpotMap
        focusedResult={focusedResult}
        searchResults={searchResults}
        spots={mapSpots}
        onSelectSpot={selectSpot}
      />
      <details className="region-filter-details">
        <summary>{selectedRegionId ? `${groups.find((group) => group.region.id === selectedRegionId)?.region.name ?? "地域"}で表示中` : "地域で絞り込む"} <span>{selectedRegionId ? "変更" : "すべて"}</span></summary>
        <div className="region-map-grid">
          {JAPAN_REGIONS.map((region: JapanRegion) => {
            const group = groups.find((item) => item.region.id === region.id);
            const count = group?.spots.length ?? 0;
            const active = selectedRegionId === region.id;
            return (
              <button
                aria-label={`${region.name}: 保存スポット${count}件を表示`}
                aria-pressed={active}
                className={`region-tile ${region.className}${count > 0 ? " has-pins" : ""}${active ? " is-active" : ""}`}
                key={region.id}
                onClick={() => onSelectRegion(active ? null : region.id)}
                type="button"
              >
                <span className="region-tile-top"><span>{region.name}</span><span className={`region-count${count >= REGION_PIN_THRESHOLD ? " is-ready" : ""}`}>{count}</span></span>
              </button>
            );
          })}
          <button
            aria-pressed={selectedRegionId === null}
            className={`region-tile region-show-all${selectedRegionId === null ? " is-active" : ""}`}
            onClick={() => onSelectRegion(null)}
            type="button"
          >
            <span className="region-tile-top"><span>全国</span><span className="region-count">{spots.length}</span></span>
          </button>
        </div>
      </details>
      <p className="region-map-footnote">
        {searchResults.length > 0
          ? "検索結果 © OpenStreetMap contributors · 検索地点は一時表示です。"
          : "地域カードから保存スポットを絞り込めます。"}
      </p>
    </div>
  );
}
