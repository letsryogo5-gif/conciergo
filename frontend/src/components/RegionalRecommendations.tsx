import type { JapanRegion } from "../regions";
import { Icon } from "./Icon";

export type RegionalRecommendation = {
  region: JapanRegion;
  spotIds: string[];
};

type RegionalRecommendationsProps = {
  recommendations: RegionalRecommendation[];
  compact?: boolean;
  onCreateRoute: (recommendation: RegionalRecommendation) => void;
};

export function RegionalRecommendations({
  recommendations,
  compact = false,
  onCreateRoute,
}: RegionalRecommendationsProps) {
  if (recommendations.length === 0) return null;

  return (
    <section className={`regional-recommendations${compact ? " is-compact" : ""}`} aria-label="エリア別おすすめルート">
      <div className="recommendation-heading">
        <span className="recommendation-sparkle"><Icon name="sparkle" size={17} /></span>
        <div><span>YOUR NEXT LITTLE ADVENTURE</span><strong>ピンが集まったエリアから、旅を作ろう。</strong></div>
      </div>
      <div className="recommendation-list">
        {recommendations.map((recommendation) => (
          <article className="recommendation-card" key={recommendation.region.id}>
            <span className="recommendation-count">{recommendation.spotIds.length}<small> SPOTS</small></span>
            <p><strong>{recommendation.region.name}</strong>の行きたい場所が<strong>{recommendation.spotIds.length}件</strong>たまりました！<span>このエリアで最高の周遊ルートを作ってみませんか？</span></p>
            <button onClick={() => onCreateRoute(recommendation)} type="button">このエリアでルートを作る <Icon name="arrow" size={15} /></button>
          </article>
        ))}
      </div>
    </section>
  );
}
