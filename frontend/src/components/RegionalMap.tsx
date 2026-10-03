import { JAPAN_REGIONS, REGION_PIN_THRESHOLD, getRegionalSpotGroups } from "../regions";
import type { JapanRegion } from "../regions";
import type { Spot } from "../types";

type RegionalMapProps = {
  spots: Spot[];
  selectedRegionId: string | null;
  onSelectRegion: (regionId: string | null) => void;
};

export function RegionalMap({ spots, selectedRegionId, onSelectRegion }: RegionalMapProps) {
  const groups = getRegionalSpotGroups(spots);

  return (
    <div className="regional-map" aria-label="日本の地域別ウィッシュマップ">
      <div className="map-caption"><span className="map-live-dot" /> YOUR WISH MAP BY REGION</div>
      <div className="region-direction-labels"><span>北 N</span><span>南 S</span></div>
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
              <span className="region-tile-note">{region.note}</span>
              <span className="region-pin-indicator" aria-hidden="true">
                {Array.from({ length: REGION_PIN_THRESHOLD }, (_, index) => <i className={index < count ? "filled" : ""} key={index} />)}
              </span>
              <span className="region-tile-state">{count === 0 ? "まだ0件" : count >= REGION_PIN_THRESHOLD ? "ルート提案できます" : `あと${REGION_PIN_THRESHOLD - count}件で提案`}</span>
            </button>
          );
        })}
      </div>
      <button
        className={`region-show-all${selectedRegionId === null ? " is-active" : ""}`}
        onClick={() => onSelectRegion(null)}
        type="button"
      >
        全国の保存スポットを見る <span>{spots.length}件</span>
      </button>
      <p className="region-map-footnote">日本の地域区分をもとにしたエリア表示です。実際の地図ではありません。</p>
    </div>
  );
}
