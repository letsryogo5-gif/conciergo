import { useEffect, useState } from "react";
import type { LocalEvent, RoutePlan, Spot } from "../types";
import { Icon } from "./Icon";

type RoutePlannerProps = {
  savedSpots: Spot[];
  selectedSpotIds: string[];
  areaName: string | null;
  event: LocalEvent | null;
  routePlan: RoutePlan | null;
  loading: boolean;
  error: string | null;
  sharing: boolean;
  shareMessage: string | null;
  shareError: string | null;
  onSelectionChange: (spotIds: string[]) => void;
  onGenerate: (spotIds: string[]) => void;
  onShare: (title: string) => void;
  onBrowseFeed: () => void;
};

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}分`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}時間${remainder}分` : `${hours}時間`;
}

export function RoutePlanner({
  savedSpots,
  selectedSpotIds,
  areaName,
  event,
  routePlan,
  loading,
  error,
  sharing,
  shareMessage,
  shareError,
  onSelectionChange,
  onGenerate,
  onShare,
  onBrowseFeed,
}: RoutePlannerProps) {
  const [shareTitle, setShareTitle] = useState("");
  const [selectedPrefecture, setSelectedPrefecture] = useState<string | null>(null);
  const selectedIds = selectedSpotIds.filter((spotId) => savedSpots.some((spot) => spot.id === spotId));
  const prefectures = [...new Set(savedSpots.map((spot) => spot.prefecture))];
  const visibleSpots = selectedPrefecture
    ? savedSpots.filter((spot) => spot.prefecture === selectedPrefecture)
    : savedSpots;
  const allVisibleSelected = visibleSpots.length > 0
    && visibleSpots.every((spot) => selectedIds.includes(spot.id));

  function toggleSpot(spotId: string) {
    onSelectionChange(
      selectedIds.includes(spotId)
        ? selectedIds.filter((id) => id !== spotId)
        : [...selectedIds, spotId],
    );
  }

  useEffect(() => {
    if (!routePlan) return;
    const firstSpot = routePlan.days[0]?.stops[0]?.spot;
    const title = event
      ? `${event.name}を楽しむ${event.region}の旅`
      : areaName
        ? `${areaName}をめぐるよりみちコース`
        : firstSpot
          ? `${firstSpot.prefecture}から始まるよりみちコース`
          : "わたしのよりみちコース";
    setShareTitle(title);
  }, [areaName, event, routePlan]);

  return (
    <section className="route-page" aria-label="旅行プラン">
      <div className="route-page-intro">
        <div><p className="eyebrow"><Icon name="route" size={14} /> YOUR MADE-TO-ORDER JOURNEY</p><h1>{event ? `${event.name}に合わせて、` : areaName ? `${areaName}のピンをつないで、` : "「行きたい」をつないで、"}<br /><em>旅のかたちに。</em></h1><p className="intro-description">{event ? `${event.best_time}ごろの開催に合わせ、近くの世界遺産や豆知識スポットも組み合わせます。` : areaName ? `${areaName}エリアのスポットだけで、巡る順番と1日の予定を組み立てます。` : "マイマップのスポットから、巡る順番と1日の予定を組み立てます。"}</p></div>
        <span className="route-intro-stamp"><Icon name="sparkle" size={26} /><small>MADE FOR YOU</small></span>
      </div>
      <div className="route-sample-note" role="note"><strong>サンプルのルート提案</strong><span>座標から近隣の場所を同じ日にまとめる簡易計算です。実際の道路・鉄道・フェリーの経路や時刻ではありません。</span></div>
      {savedSpots.length === 0 ? (
        <div className="route-empty">
          <span className="route-empty-icon"><Icon name="map" size={26} /></span>
          <h2>旅のきっかけを集めよう。</h2>
          <p>フィードで「行きたい」を押した場所から、<br />あなただけの旅のたたき台を作れます。</p>
          <button className="button-primary" onClick={onBrowseFeed} type="button">景色を見つける <Icon name="arrow" size={16} /></button>
        </div>
      ) : (
        <>
          <section className="route-spot-picker" aria-label="今回の旅行で訪れるスポット">
            <div className="route-spot-picker-heading">
              <div>
                <span className="eyebrow">CHOOSE YOUR STOPS</span>
                <h2>今回の旅で行きたい場所</h2>
                <p>選んだスポットだけでタイムラインを作成します。</p>
              </div>
              <span className="route-selection-count">{selectedIds.length}<small> / {savedSpots.length} SPOTS</small></span>
            </div>
            <div className="route-region-filter" role="group" aria-label="都道府県でスポットを絞り込む">
              <button
                aria-pressed={selectedPrefecture === null}
                className={selectedPrefecture === null ? "is-active" : ""}
                onClick={() => setSelectedPrefecture(null)}
                type="button"
              >
                すべて <span>{savedSpots.length}</span>
              </button>
              {prefectures.map((prefecture) => {
                const count = savedSpots.filter((spot) => spot.prefecture === prefecture).length;
                return (
                  <button
                    aria-pressed={selectedPrefecture === prefecture}
                    className={selectedPrefecture === prefecture ? "is-active" : ""}
                    key={prefecture}
                    onClick={() => setSelectedPrefecture(prefecture)}
                    type="button"
                  >
                    {prefecture} <span>{count}</span>
                  </button>
                );
              })}
            </div>
            <div className="route-spot-picker-actions">
              <button
                disabled={allVisibleSelected}
                onClick={() => onSelectionChange([...new Set([...selectedIds, ...visibleSpots.map((spot) => spot.id)])])}
                type="button"
              >
                表示中を選択
              </button>
              <button
                disabled={!visibleSpots.some((spot) => selectedIds.includes(spot.id))}
                onClick={() => {
                  const visibleIds = new Set(visibleSpots.map((spot) => spot.id));
                  onSelectionChange(selectedIds.filter((spotId) => !visibleIds.has(spotId)));
                }}
                type="button"
              >
                表示中を解除
              </button>
            </div>
            <ul className="route-spot-picker-list">
              {visibleSpots.map((spot) => {
                const checked = selectedIds.includes(spot.id);
                return (
                  <li key={spot.id}>
                    <label className={checked ? "route-spot-option is-selected" : "route-spot-option"}>
                      <input
                        checked={checked}
                        onChange={() => toggleSpot(spot.id)}
                        type="checkbox"
                      />
                      <img src={spot.image_url} alt="" />
                      <span><strong>{spot.region.split(",")[0]}</strong><small>{spot.prefecture} · {spot.local_food}</small></span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </section>
          <div className="route-create-row">
            <div><span className="eyebrow">YOUR WISH LIST</span><strong>{selectedIds.length}か所を今回のルートに選択</strong><span>マイマップに保存した場所から選べます。</span></div>
            <button className="button-primary route-generate-button" disabled={loading || selectedIds.length === 0} onClick={() => onGenerate(selectedIds)} type="button"><Icon name="sparkle" size={16} />{loading ? "プランを組み立て中…" : routePlan ? "選んだ場所で作り直す" : "選んだ場所で旅行プランを作る"}<Icon name="arrow" size={15} /></button>
          </div>
          {error && <p className="route-error" role="alert">{error}</p>}
          {routePlan ? (
            <>
              {routePlan.occasion && <div className="route-occasion-banner"><img src={routePlan.occasion.image_url} alt="" /><span><small>SEASONAL JOURNEY · {routePlan.occasion.best_time}</small><strong>{routePlan.occasion.name}の時期に合わせた旅</strong><span>近くの世界遺産・ローカルトリビアスポットもルート候補に加えました。</span></span><span className="occasion-star">✦</span></div>}
              <div className="route-summary">
                <span><strong>{routePlan.days.length}</strong>日間の旅</span>
                <span><strong>{routePlan.total_spots}</strong>スポット</span>
                <span><strong>{formatMinutes(routePlan.total_estimated_travel_minutes)}</strong>同日内の移動目安</span>
                <span className="route-summary-tag">SAMPLE ROUTE</span>
              </div>
              <div className="route-days">
                {routePlan.days.map((day) => (
                  <article className="route-day-card" key={day.day_number}>
                    <header className="route-day-header"><span className="route-day-number">DAY {String(day.day_number).padStart(2, "0")}</span><div><h2>{day.title}</h2><span>{day.start_time} 出発 · {day.end_time} ごろ終了</span></div><span className="route-stop-count">{day.stops.length} SPOT{day.stops.length === 1 ? "" : "S"}</span></header>
                    <ol className="route-timeline">
                      {day.stops.map((stop, stopIndex) => (
                        <li className="route-timeline-item" key={stop.spot.id}>
                          {stopIndex > 0 && <div className="route-transfer"><span className="transfer-line" /><span><Icon name="route" size={13} /> 移動目安 {stop.travel_minutes_from_previous}分 · 約{stop.distance_km_from_previous}km（直線距離）</span></div>}
                          <div className="route-stop-row"><span className="route-stop-time">{stop.arrival_time}<small>{stop.departure_time}</small></span><span className="route-stop-marker"><Icon name="pin" size={15} /></span><img src={stop.spot.image_url} alt="" /><div className="route-stop-copy"><span>{stop.spot.prefecture} · {stop.spot.category}</span><h3>{stop.spot.region.split(",")[0]}</h3><p>{stop.spot.title}</p><small>滞在目安 {stop.visit_minutes}分 · {stop.spot.local_food}も味わって</small></div></div>
                        </li>
                      ))}
                    </ol>
                  </article>
                ))}
              </div>
              <p className="route-disclaimer">{routePlan.note}</p>
              <div className="route-share-panel">
                <div><span className="eyebrow">PASS THE INSPIRATION ON</span><strong>この旅のかけらを、誰かの次の旅へ。</strong><p>公開すると「モデルコース」タブに表示されます。</p></div>
                <label>コース名<input maxLength={90} onChange={(changeEvent) => setShareTitle(changeEvent.target.value)} value={shareTitle} /></label>
                <button className="button-primary" disabled={sharing || !shareTitle.trim()} onClick={() => onShare(shareTitle.trim())} type="button">
                  <Icon name="arrow" size={15} />{sharing ? "公開しています…" : "モデルコースとして公開"}
                </button>
                {shareMessage && <p className="route-share-message" role="status">{shareMessage}</p>}
                {shareError && <p className="route-share-error" role="alert">{shareError}</p>}
              </div>
            </>
          ) : (
            <div className="route-preview">
              <div className="route-preview-icon"><Icon name="route" size={23} /></div>
              <div><strong>集めたピンを、旅のタイムラインへ。</strong><p>近いスポットを同じ日にまとめ、各日の訪問順を提案します。</p></div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
