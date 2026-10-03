import { useMemo, useState } from "react";
import type { LocalEvent, Spot } from "../types";
import { Icon } from "./Icon";

type EventCalendarProps = {
  events: LocalEvent[];
  spots: Spot[];
  savedIds: string[];
  visitedIds: string[];
  onToggleSave: (spot: Spot) => void;
  onToggleVisited: (spot: Spot) => void;
  onCreateRoute: (event: LocalEvent) => void;
};

const MONTHS = ["睦月", "如月", "弥生", "卯月", "皐月", "水無月", "文月", "葉月", "長月", "神無月", "霜月", "師走"];

function getInitialMonth(events: LocalEvent[]): number {
  const currentMonth = new Date().getMonth() + 1;
  if (events.some((event) => currentMonth >= event.start_month && currentMonth <= event.end_month)) {
    return currentMonth;
  }
  return events
    .map((event) => event.start_month)
    .filter((month) => month >= currentMonth)
    .sort((first, second) => first - second)[0]
    ?? events.map((event) => event.start_month).sort((first, second) => first - second)[0]
    ?? currentMonth;
}

export function EventCalendar({ events, spots, savedIds, visitedIds, onToggleSave, onToggleVisited, onCreateRoute }: EventCalendarProps) {
  const [selectedMonth, setSelectedMonth] = useState(() => getInitialMonth(events));
  const eventsForMonth = useMemo(
    () => events.filter((event) => selectedMonth >= event.start_month && selectedMonth <= event.end_month),
    [events, selectedMonth],
  );

  function getSpot(spotId: string): Spot | undefined {
    return spots.find((spot) => spot.id === spotId);
  }

  return (
    <section className="event-page" aria-label="年中行事カレンダー">
      <div className="event-page-intro"><div><p className="eyebrow"><Icon name="sparkle" size={14} /> SEASONS WORTH WANDERING FOR</p><h1>季節を追いかけて、<br /><em>旅に出よう。</em></h1><p className="intro-description">日本の年中行事や、景色がいちばん輝く季節をひと月ずつ。</p></div><span className="event-year-stamp">JAPAN<small>SEASONAL NOTES</small></span></div>
      <div className="event-calendar-note"><span>CALENDAR OF LITTLE DISCOVERIES</span><p>開催月・見頃はサンプルデータです。年ごとの日程は各イベントの公式情報をご確認ください。</p></div>
      <div className="month-rail" aria-label="月を選ぶ">
        {MONTHS.map((month, index) => {
          const monthNumber = index + 1;
          const hasEvent = events.some((event) => monthNumber >= event.start_month && monthNumber <= event.end_month);
          return <button aria-pressed={selectedMonth === monthNumber} className={`month-button${selectedMonth === monthNumber ? " selected" : ""}${hasEvent ? " has-event" : ""}`} key={month} onClick={() => setSelectedMonth(monthNumber)} type="button"><strong>{String(monthNumber).padStart(2, "0")}</strong><span>{month}</span>{hasEvent && <i />}</button>;
        })}
      </div>
      <div className="event-month-heading"><span className="event-month-number">{String(selectedMonth).padStart(2, "0")}</span><div><span>MONTHLY JOURNAL</span><h2>{MONTHS[selectedMonth - 1]}の、旅のきっかけ。</h2></div><span className="event-month-count">{eventsForMonth.length} EVENTS</span></div>
      {eventsForMonth.length > 0 ? (
        <div className="event-card-list">
          {eventsForMonth.map((event) => {
            const spot = getSpot(event.spot_id);
            if (!spot) return null;
            const isSaved = savedIds.includes(spot.id);
            const isVisited = visitedIds.includes(spot.id);
            return (
              <article className="event-card" key={event.id}>
                <div className="event-card-visual"><img src={event.image_url} alt={`${event.name}の雰囲気を伝えるサンプル画像`} loading="lazy" /><span className="event-month-badge">{event.best_time}</span>{spot.is_world_heritage && <span className="event-heritage-chip">✦ 世界遺産とめぐる</span>}</div>
                <div className="event-card-copy"><span className="event-category">{event.category} · {event.region}</span><h3>{event.name}</h3><p>{event.description}</p><div className="event-linked-spot"><img src={spot.image_url} alt="" /><span><small>この季節に出会いたい場所</small><strong>{spot.region.split(",")[0]} · {spot.prefecture}</strong></span>{spot.is_world_heritage && <span className="tiny-heritage-mark">✦</span>}</div><div className="event-card-actions"><button className={isSaved ? "event-save-button saved" : "event-save-button"} onClick={() => onToggleSave(spot)} type="button" aria-pressed={isSaved}><Icon name="heart" size={15} />{isSaved ? "行きたいリストに保存中" : "行きたいリストに保存"}</button><button className="event-route-button" onClick={() => onCreateRoute(event)} type="button">この季節の旅を作る <Icon name="arrow" size={14} /></button></div><button className={isVisited ? "visited-toggle is-visited event-visited-toggle" : "visited-toggle event-visited-toggle"} onClick={() => onToggleVisited(spot)} type="button" aria-pressed={isVisited}>{isVisited ? "行った場所に記録済み ✓" : "ここに行ったことがある"}</button></div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="event-empty"><span>✳</span><strong>この月の行事は、これから届きます。</strong><p>別の月を選んで、季節の旅を探してみて。</p></div>
      )}
      <p className="event-footer-note">年中行事の画像・説明・開催時期はサンプルです。開催の有無・日程・見頃は年によって異なります。</p>
    </section>
  );
}
