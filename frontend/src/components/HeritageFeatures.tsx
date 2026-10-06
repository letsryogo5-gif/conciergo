import type { Spot } from "../types";
import { Icon } from "./Icon";
import { WikipediaSpotSummary } from "./WikipediaSpotSummary";

type HeritageFeaturesProps = {
  spots: Spot[];
  savedIds: string[];
  visitedIds: string[];
  onToggleSave: (spot: Spot) => void;
  onToggleVisited: (spot: Spot) => void;
  onOpenMap: (spot: Spot) => void;
};

export function HeritageFeatures({ spots, savedIds, visitedIds, onToggleSave, onToggleVisited, onOpenMap }: HeritageFeaturesProps) {
  const heritageSpots = spots.filter((spot) => spot.is_world_heritage);
  if (heritageSpots.length === 0) return null;

  return (
    <section className="heritage-section" aria-label="日本の世界遺産を訪ねる">
      <div className="heritage-section-heading"><div><span className="eyebrow"><Icon name="sparkle" size={14} /> WORLD HERITAGE, A LITTLE CLOSER</span><h2>世界遺産を、<em>旅の理由に。</em></h2><p>その土地の物語を、風景の中で見つけよう。</p></div><span className="heritage-section-seal">JAPAN<small>HERITAGE</small></span></div>
      <div className="heritage-card-row">
        {heritageSpots.map((spot) => {
          const isSaved = savedIds.includes(spot.id);
          const isVisited = visitedIds.includes(spot.id);
          return (
            <article className="heritage-card" key={spot.id}>
              <button className="heritage-card-image" onClick={() => onOpenMap(spot)} type="button" aria-label={`${spot.heritage_name}をマイマップで見る`}><img src={spot.image_url} alt={`${spot.region}のサンプル風景`} loading="lazy" /><span className="heritage-crown">✦ WORLD HERITAGE</span><span className="heritage-card-region"><Icon name="pin" size={12} />{spot.prefecture}</span></button>
              <div className="heritage-card-copy"><span className="heritage-overline">日本の世界遺産</span><h3>{spot.heritage_name}</h3><p>{spot.local_trivia}</p><WikipediaSpotSummary spot={spot} label="世界遺産の概要と価値を知る" /><div className="heritage-card-actions"><button className={isSaved ? "heritage-save saved" : "heritage-save"} onClick={() => onToggleSave(spot)} type="button" aria-pressed={isSaved}><Icon name="heart" size={14} />{isSaved ? "保存中" : "行きたい"}</button><button className={isVisited ? "visited-toggle is-visited" : "visited-toggle"} onClick={() => onToggleVisited(spot)} type="button" aria-pressed={isVisited}>{isVisited ? "行った ✓" : "行った"}</button></div></div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
