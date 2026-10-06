import type { ModelCourse, Spot } from "../types";
import { Icon } from "./Icon";

type ModelCourseDiscoverProps = {
  courses: ModelCourse[];
  spots: Spot[];
  savedIds: string[];
  onSaveSpot: (spot: Spot) => void;
};

type ModelCourseCardProps = Omit<ModelCourseDiscoverProps, "courses"> & {
  course: ModelCourse;
};

function ModelCourseCard({ course, spots, savedIds, onSaveSpot }: ModelCourseCardProps) {
  const courseSpots = course.spot_ids.map((spotId) => spots.find((spot) => spot.id === spotId) ?? null);

  return (
    <article className="model-course-card">
      <div className="model-course-visual">
        <img src={course.image_url} alt={`${course.region}モデルコースのイメージ`} loading="lazy" />
        <span className="model-course-ribbon"><Icon name="route" size={13} /> MODEL COURSE</span>
        <span className="model-course-region">{course.region}</span>
      </div>
      <div className="model-course-copy">
        <div className="model-course-meta"><span>BY {course.creator}</span><span>♡ {course.likes.toLocaleString("ja-JP")}</span></div>
        <h2>{course.title}</h2>
        <p>{course.description}</p>
        <div className="model-course-itinerary-heading">
          <span className="eyebrow">COURSE ITINERARY</span>
          <span>モデルコースの順路 · {course.spot_ids.length}スポット</span>
        </div>
        <ol className="model-course-timeline" aria-label={`${course.title}の訪問順路`}>
          {courseSpots.map((spot, index) => (
            <li key={course.spot_ids[index]}>
              <span className="model-course-stop-number" aria-label={`第${index + 1}スポット`}>
                {String(index + 1).padStart(2, "0")}
              </span>
              {spot ? (
                <>
                  <img src={spot.image_url} alt={`${spot.prefecture}のサンプル風景`} loading="lazy" />
                  <div className="model-course-stop-copy">
                    <span className="model-course-stop-meta">{spot.prefecture} · {spot.category}</span>
                    <strong>{spot.title}</strong>
                    <p>{spot.description}</p>
                    <span className="model-course-stop-local">
                      <span><b>味わう</b>{spot.local_food}</span>
                      <span><b>出会う</b>{spot.local_species}</span>
                    </span>
                    {spot.is_world_heritage && (
                      <span className="model-course-stop-heritage">✦ 世界遺産 · {spot.heritage_name}</span>
                    )}
                  </div>
                  <button
                    aria-label={`${spot.title}を行きたいリストに${savedIds.includes(spot.id) ? "追加済み" : "追加"}`}
                    className={savedIds.includes(spot.id) ? "model-course-save-stop is-saved" : "model-course-save-stop"}
                    disabled={savedIds.includes(spot.id)}
                    onClick={() => onSaveSpot(spot)}
                    type="button"
                  >
                    <Icon name={savedIds.includes(spot.id) ? "heart" : "bookmark"} size={13} />
                    {savedIds.includes(spot.id) ? "追加済み" : "行きたい"}
                  </button>
                </>
              ) : (
                <span className="model-course-missing">スポット情報を読み込めませんでした: {course.spot_ids[index]}</span>
              )}
            </li>
          ))}
        </ol>
        <p className="model-course-save-note">気になるスポットだけを個別に「行きたい」へ保存できます。</p>
      </div>
    </article>
  );
}

export function ModelCourseDiscover({ courses, spots, savedIds, onSaveSpot }: ModelCourseDiscoverProps) {
  return (
    <section className="model-course-page" aria-label="モデルコースを発見">
      <div className="model-course-page-intro">
        <div>
          <p className="eyebrow"><Icon name="compass" size={14} /> JOURNEYS SHARED BY TRAVELERS</p>
          <h1>誰かの旅から、<br /><em>次の旅を見つけよう。</em></h1>
          <p className="intro-description">モデルコースの順路を眺めて、心に留まったスポットだけを行きたいリストへ。</p>
        </div>
        <span className="model-course-stamp">TRAVEL<small>TOGETHER</small></span>
      </div>
      <div className="model-course-sample-note" role="note">
        <strong>モデルコースはサンプル共有です</strong>
        <span>投稿内容はこの試作サーバーのメモリー上で共有されます。外部SNS投稿や永続データベースへの保存は行いません。</span>
      </div>
      {courses.length > 0 ? (
        <div className="model-course-list">
          {courses.map((course) => (
            <ModelCourseCard
              course={course}
              key={course.id}
              onSaveSpot={onSaveSpot}
              savedIds={savedIds}
              spots={spots}
            />
          ))}
        </div>
      ) : (
        <div className="model-course-empty"><Icon name="route" size={28} /><strong>モデルコースはまだありません。</strong><span>公開された旅のコースがここに並びます。</span></div>
      )}
    </section>
  );
}
