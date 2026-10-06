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
      <details>
        <summary><Icon name="sparkle" size={14} />地域の保存スポットからルートを作る <span>{recommendations.length}</span></summary>
        <div className="recommendation-list">
          {recommendations.map((recommendation) => (
            <article className="recommendation-card" key={recommendation.region.id}>
              <p><strong>{recommendation.region.name}</strong> · {recommendation.spotIds.length}スポット</p>
              <button onClick={() => onCreateRoute(recommendation)} type="button">ルートを作成 <Icon name="arrow" size={15} /></button>
            </article>
          ))}
        </div>
      </details>
    </section>
  );
}
