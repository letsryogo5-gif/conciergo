import { useEffect, useMemo, useState } from "react";
import type { AppStatus, LocalEvent, ModelCourse, ModelCourseRequest, RoutePlan, RouteRequest, Spot, TravelMemory } from "./types";
import { Icon } from "./components/Icon";
import { RoutePlanner } from "./components/RoutePlanner";
import { RegionalMap } from "./components/RegionalMap";
import { RegionalRecommendations } from "./components/RegionalRecommendations";
import { TriviaToast } from "./components/TriviaToast";
import { EventCalendar } from "./components/EventCalendar";
import { HeritageFeatures } from "./components/HeritageFeatures";
import { MemoryJournal } from "./components/MemoryJournal";
import { ModelCourseDiscover } from "./components/ModelCourseDiscover";
import type { RegionalRecommendation } from "./components/RegionalRecommendations";
import { getRegionalSpotGroups, REGION_PIN_THRESHOLD } from "./regions";

type View = "feed" | "map" | "route" | "events" | "memories" | "discover";

const categories = ["すべて", "秘境", "季節の絶景", "海辺のまち", "まち歩き", "野生のいきもの"];
const favoritesStorageKey = "yorimichi-wishlist";
const visitedStorageKey = "yorimichi-visited";

function readSavedSpotIds(): string[] {
  const storedValue = window.localStorage.getItem(favoritesStorageKey);
  if (storedValue === null) return [];

  const parsedValue: unknown = JSON.parse(storedValue);
  if (!Array.isArray(parsedValue) || !parsedValue.every((value) => typeof value === "string")) {
    throw new Error("保存したスポットのデータ形式が正しくありません。ブラウザーの保存データを確認してください。");
  }
  return parsedValue;
}

function readVisitedSpotIds(): string[] {
  const storedValue = window.localStorage.getItem(visitedStorageKey);
  if (storedValue === null) return [];

  const parsedValue: unknown = JSON.parse(storedValue);
  if (!Array.isArray(parsedValue) || !parsedValue.every((value) => typeof value === "string")) {
    throw new Error("「行った」スポットのデータ形式が正しくありません。ブラウザーの保存データを確認してください。");
  }
  return parsedValue;
}

function App() {
  const [spots, setSpots] = useState<Spot[]>([]);
  const [events, setEvents] = useState<LocalEvent[]>([]);
  const [memories, setMemories] = useState<TravelMemory[]>([]);
  const [modelCourses, setModelCourses] = useState<ModelCourse[]>([]);
  const [savedIds, setSavedIds] = useState<string[]>([]);
  const [visitedIds, setVisitedIds] = useState<string[]>([]);
  const [status, setStatus] = useState<AppStatus | null>(null);
  const [routePlan, setRoutePlan] = useState<RoutePlan | null>(null);
  const [routeSpotIds, setRouteSpotIds] = useState<string[] | null>(null);
  const [routeAreaName, setRouteAreaName] = useState<string | null>(null);
  const [routeEvent, setRouteEvent] = useState<LocalEvent | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [routeShareLoading, setRouteShareLoading] = useState(false);
  const [routeShareMessage, setRouteShareMessage] = useState<string | null>(null);
  const [routeShareError, setRouteShareError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<View>("feed");
  const [activeCategory, setActiveCategory] = useState("すべて");
  const [selectedSpotId, setSelectedSpotId] = useState<string | null>(null);
  const [selectedRegionId, setSelectedRegionId] = useState<string | null>(null);
  const [routeSelectionMode, setRouteSelectionMode] = useState(false);
  const [selectedRouteSpotIds, setSelectedRouteSpotIds] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [storageError, setStorageError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSampleData() {
      try {
        const [spotsResponse, statusResponse, eventsResponse, memoriesResponse, modelCoursesResponse] = await Promise.all([
          fetch("/api/spots"),
          fetch("/api/status"),
          fetch("/api/events"),
          fetch("/api/memories"),
          fetch("/api/model-courses"),
        ]);
        if (!spotsResponse.ok || !statusResponse.ok || !eventsResponse.ok || !memoriesResponse.ok || !modelCoursesResponse.ok) {
          throw new Error("サンプルデータを読み込めませんでした。バックエンドが起動しているか確認してください。");
        }

        const [spotData, statusData, eventData, memoryData, modelCourseData] = await Promise.all([
          spotsResponse.json() as Promise<Spot[]>,
          statusResponse.json() as Promise<AppStatus>,
          eventsResponse.json() as Promise<LocalEvent[]>,
          memoriesResponse.json() as Promise<TravelMemory[]>,
          modelCoursesResponse.json() as Promise<ModelCourse[]>,
        ]);
        if (!Array.isArray(spotData) || spotData.length === 0) {
          throw new Error("表示できるスポットがありません。サンプルデータを確認してください。");
        }
        setSpots(spotData);
        setEvents(eventData);
        setMemories(memoryData);
        setModelCourses(modelCourseData);
        setStatus(statusData);
        setSavedIds(readSavedSpotIds());
        setVisitedIds(readVisitedSpotIds());
      } catch (cause) {
        setLoadError(cause instanceof Error ? cause.message : "初期データの読み込みに失敗しました。");
      } finally {
        setLoading(false);
      }
    }

    void loadSampleData();
  }, []);

  const savedSpots = useMemo(
    () => spots.filter((spot) => savedIds.includes(spot.id)),
    [savedIds, spots],
  );
  const regionalGroups = useMemo(() => getRegionalSpotGroups(savedSpots), [savedSpots]);
  const recommendations: RegionalRecommendation[] = useMemo(
    () => regionalGroups
      .filter(({ spots: regionSpots }) => regionSpots.length >= REGION_PIN_THRESHOLD)
      .map(({ region, spots: regionSpots }) => ({ region, spotIds: regionSpots.map((spot) => spot.id) })),
    [regionalGroups],
  );
  const selectedRegion = regionalGroups.find(({ region }) => region.id === selectedRegionId)?.region ?? null;
  const mapSpots = selectedRegionId
    ? regionalGroups.find(({ region }) => region.id === selectedRegionId)?.spots ?? []
    : savedSpots;
  const visibleSpots = useMemo(
    () => activeCategory === "すべて" ? spots : spots.filter((spot) => spot.category === activeCategory),
    [activeCategory, spots],
  );
  const selectedMapSpot = mapSpots.find((spot) => spot.id === selectedSpotId) ?? mapSpots[0] ?? null;

  function toggleSavedSpot(spot: Spot) {
    const isSaved = savedIds.includes(spot.id);
    const nextIds = isSaved ? savedIds.filter((id) => id !== spot.id) : [...savedIds, spot.id];

    try {
      window.localStorage.setItem(favoritesStorageKey, JSON.stringify(nextIds));
      setSavedIds(nextIds);
      setSelectedRouteSpotIds((current) => current?.filter((id) => nextIds.includes(id)) ?? null);
      setRoutePlan(null);
      setRouteSpotIds(null);
      setRouteAreaName(null);
      setRouteEvent(null);
      setStorageError(null);
    } catch {
      setStorageError("保存できませんでした。ブラウザーのストレージ設定を確認してください。");
    }
  }

  function toggleVisitedSpot(spot: Spot) {
    const isVisited = visitedIds.includes(spot.id);
    const nextIds = isVisited ? visitedIds.filter((id) => id !== spot.id) : [...visitedIds, spot.id];

    try {
      window.localStorage.setItem(visitedStorageKey, JSON.stringify(nextIds));
      setVisitedIds(nextIds);
      setStorageError(null);
    } catch {
      setStorageError("「行った」状態を保存できませんでした。ブラウザーのストレージ設定を確認してください。");
    }
  }

  async function generateRoute(
    spotIds: string[] = routeSpotIds ?? savedIds,
    areaName: string | null = routeAreaName,
    event: LocalEvent | null = routeEvent,
  ) {
    if (spotIds.length === 0) return;

    setRouteLoading(true);
    setRouteError(null);
    setRouteShareMessage(null);
    setRouteShareError(null);
    setRoutePlan(null);
    setRouteSpotIds(spotIds);
    setRouteAreaName(areaName);
    setRouteEvent(event);
    try {
      const routeRequest: RouteRequest = {
        spot_ids: [...spotIds],
        event_id: event?.id ?? null,
      };
      const response = await fetch("/api/routes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(routeRequest),
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "旅行プランを作成できませんでした。");
      }
      setRoutePlan((await response.json()) as RoutePlan);
    } catch (cause) {
      setRouteError(cause instanceof Error ? cause.message : "旅行プランの作成に失敗しました。");
    } finally {
      setRouteLoading(false);
    }
  }

  async function shareCurrentRoute(title: string) {
    if (!routePlan || !title.trim()) return;

    const spotIds = [...new Set(routePlan.days.flatMap((day) => day.stops.map((stop) => stop.spot.id)))];
    if (spotIds.length === 0) {
      setRouteShareError("共有できるスポットが含まれていません。");
      return;
    }
    const routeSpots = spotIds
      .map((spotId) => spots.find((spot) => spot.id === spotId))
      .filter((spot): spot is Spot => spot !== undefined);
    if (routeSpots.length !== spotIds.length) {
      setRouteShareError("ルート内のスポット情報が不足しているため、共有できません。");
      return;
    }
    const region = routeAreaName
      ?? [...new Set(routeSpots.map((spot) => spot.prefecture))].join("・");
    const description = routeEvent
      ? `${routeEvent.name}の開催目安に合わせた、${routeEvent.region}のサンプル旅行コースです。`
      : `${region}のスポットをつないだ、よりみち発のサンプル旅行コースです。`;
    const request: ModelCourseRequest = {
      title: title.trim(),
      description,
      region,
      creator: "よりみちユーザー",
      spot_ids: spotIds,
    };

    setRouteShareLoading(true);
    setRouteShareMessage(null);
    setRouteShareError(null);
    try {
      const response = await fetch("/api/model-courses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "モデルコースを公開できませんでした。");
      }
      const publishedCourse = (await response.json()) as ModelCourse;
      setModelCourses((current) => [publishedCourse, ...current.filter((course) => course.id !== publishedCourse.id)]);
      setRouteShareMessage("モデルコースを公開しました。「モデルコース」から確認できます。");
    } catch (cause) {
      setRouteShareError(cause instanceof Error ? cause.message : "モデルコースの公開に失敗しました。");
    } finally {
      setRouteShareLoading(false);
    }
  }

  function saveModelCourseSpot(spot: Spot) {
    if (!spots.some((availableSpot) => availableSpot.id === spot.id)) {
      setStorageError(`スポット情報を読み込めません: ${spot.id}`);
      return;
    }

    const nextIds = [...new Set([...savedIds, spot.id])];
    try {
      window.localStorage.setItem(favoritesStorageKey, JSON.stringify(nextIds));
      setSavedIds(nextIds);
      setRouteSpotIds(null);
      setRouteAreaName(null);
      setRouteEvent(null);
      setRoutePlan(null);
      setRouteError(null);
      setStorageError(null);
    } catch {
      setStorageError("スポットを保存できませんでした。ブラウザーのストレージ設定を確認してください。");
    }
  }

  function updateRouteSelection(spotIds: string[]) {
    const uniqueIds = [...new Set(spotIds)].filter((spotId) => savedIds.includes(spotId));
    const areaName = regionalGroups.find(({ spots: regionSpots }) =>
      uniqueIds.length > 0 && uniqueIds.every((spotId) => regionSpots.some((spot) => spot.id === spotId)),
    )?.region.name ?? null;
    setRouteSpotIds(uniqueIds);
    setRouteAreaName(areaName);
    setRouteEvent(null);
    setRoutePlan(null);
    setRouteError(null);
    setRouteShareMessage(null);
    setRouteShareError(null);
  }

  function toggleRouteSelectionMode() {
    if (routeSelectionMode) {
      setRouteSelectionMode(false);
      return;
    }
    setSelectedRouteSpotIds((current) => current ?? []);
    setRouteSelectionMode(true);
  }

  function toggleRouteSpot(spotId: string) {
    setSelectedRouteSpotIds((current) => {
      const selectedIds = current ?? [];
      return selectedIds.includes(spotId)
        ? selectedIds.filter((id) => id !== spotId)
        : [...selectedIds, spotId];
    });
  }

  function selectVisibleRouteSpots() {
    const visibleIds = mapSpots.map((spot) => spot.id);
    setSelectedRouteSpotIds((current) => [...new Set([...(current ?? []), ...visibleIds])]);
  }

  function clearRouteSpotSelection() {
    setSelectedRouteSpotIds([]);
  }

  function createSelectedRoute() {
    const spotIds = selectedRouteSpotIds ?? [];
    if (spotIds.length === 0) return;

    const areaName = regionalGroups.find(({ spots: regionSpots }) =>
      spotIds.every((spotId) => regionSpots.some((spot) => spot.id === spotId)),
    )?.region.name ?? null;
    setRouteSelectionMode(false);
    setActiveView("route");
    void generateRoute(spotIds, areaName);
  }

  function openAllSavedRoute() {
    setRouteSpotIds(null);
    setRouteAreaName(null);
    setRoutePlan(null);
    setRouteError(null);
    setRouteEvent(null);
    setActiveView("route");
  }

  function createRegionalRoute(recommendation: RegionalRecommendation) {
    setSelectedRegionId(recommendation.region.id);
    setActiveView("route");
    void generateRoute(recommendation.spotIds, recommendation.region.name);
  }

  function createEventRoute(event: LocalEvent) {
    const eventSpot = spots.find((spot) => spot.id === event.spot_id);
    if (!eventSpot) {
      setRouteError("イベントに関連するスポットが見つかりません。");
      setRouteEvent(event);
      setRouteAreaName(event.region);
      setRouteSpotIds([]);
      setRoutePlan(null);
      setActiveView("route");
      return;
    }

    if (!savedIds.includes(eventSpot.id)) {
      try {
        window.localStorage.setItem(favoritesStorageKey, JSON.stringify([...savedIds, eventSpot.id]));
        setSavedIds((current) => current.includes(eventSpot.id) ? current : [...current, eventSpot.id]);
        setStorageError(null);
      } catch {
        setStorageError("保存できませんでした。ブラウザーのストレージ設定を確認してください。");
      }
    }
    setActiveView("route");
    void generateRoute([eventSpot.id], event.region, event);
  }

  if (loading) {
    return <main className="loading-screen"><span className="loading-mark">y</span><p>まだ知らない景色を探しています…</p></main>;
  }

  if (loadError || !status) {
    return <main className="error-screen"><span className="eyebrow">YORIMICHI / SAMPLE</span><h1>旅のかけらを読み込めませんでした。</h1><p role="alert">{loadError ?? "サンプルモードの状態を確認できませんでした。"}</p><button className="button-primary" onClick={() => window.location.reload()}>もう一度読み込む</button></main>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="よりみち ホーム">
          <span className="brand-mark">y</span>
          <span className="brand-word">よりみち<small>YORIMICHI</small></span>
        </a>
        <p className="sidebar-label">DISCOVER</p>
        <nav className="side-nav" aria-label="メインナビゲーション">
          <button className={activeView === "feed" ? "nav-item active" : "nav-item"} onClick={() => setActiveView("feed")} type="button"><Icon name="compass" /><span>見つける</span></button>
          <button className={activeView === "map" ? "nav-item active" : "nav-item"} onClick={() => setActiveView("map")} type="button"><Icon name="map" /><span>マイマップ</span><span className="nav-count">{savedSpots.length}</span></button>
          <button className={activeView === "route" ? "nav-item active" : "nav-item"} onClick={openAllSavedRoute} type="button"><Icon name="route" /><span>旅行プラン</span></button>
          <button className={activeView === "discover" ? "nav-item active" : "nav-item"} onClick={() => setActiveView("discover")} type="button"><Icon name="compass" /><span>モデルコース</span><span className="nav-count">{modelCourses.length}</span></button>
          <button className={activeView === "events" ? "nav-item active" : "nav-item"} onClick={() => setActiveView("events")} type="button"><Icon name="sparkle" /><span>季節の行事</span></button>
          <button className={activeView === "memories" ? "nav-item active" : "nav-item"} onClick={() => setActiveView("memories")} type="button"><Icon name="bookmark" /><span>思い出</span><span className="nav-count">{visitedIds.length}</span></button>
        </nav>
        <div className="sidebar-note"><span className="note-star">✳</span><strong>行きたい場所も、<br />旅の余韻も。</strong><p>訪れた場所は「行った」で<br />思い出に残せます。</p></div>
        <div className="sidebar-bottom"><span className="mini-avatar">y</span><span>気ままな旅好き<small>旅の記録とウィッシュリスト</small></span></div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="mobile-brand"><span className="brand-mark">y</span><span>よりみち</span></div>
          <div className="topbar-copy"><span className="topbar-eyebrow">A LITTLE INSPIRATION, EVERY DAY</span><span>旅の予定がなくても、心は旅に出られる。</span></div>
          <span className="sample-pill"><span />SAMPLE MODE</span>
        </header>

        <div className="sample-banner" role="note"><span className="banner-sparkle">✳</span><p><strong>※現在サンプルモードで動作中です</strong><span>　表示内容はデモ用データです。地図・SNSサービスには接続していません。</span></p></div>

        {storageError && <p className="storage-error" role="alert">{storageError}</p>}
        {activeView === "feed" && <TriviaToast spots={spots} savedIds={savedIds} visitedIds={visitedIds} onToggleSave={toggleSavedSpot} onToggleVisited={toggleVisitedSpot} />}

        {activeView === "feed" ? (
          <div className="content-layout">
            <section className="feed-column" aria-label="地域の魅力を見つけるフィード">
              <div className="page-intro">
                <div><p className="eyebrow"><Icon name="sparkle" size={14} /> SCROLL INTO SOMEWHERE</p><h1>知らない景色に、<br /><em>恋をしよう。</em></h1><p className="intro-description">ふと心に残った景色が、次の旅のきっかけになる。</p></div>
                <div className="issue-stamp"><span>旅心をくすぐる</span><strong>小さな<br />きっかけ</strong><span>NO. 001 — JAPAN</span></div>
              </div>
              <HeritageFeatures
                spots={spots}
                savedIds={savedIds}
                visitedIds={visitedIds}
                onToggleSave={toggleSavedSpot}
                onToggleVisited={toggleVisitedSpot}
                onOpenMap={(spot) => { setSelectedSpotId(spot.id); setSelectedRegionId(null); setActiveView("map"); }}
              />
              <div className="category-row" aria-label="スポットのカテゴリー">
                {categories.map((category) => <button key={category} className={`category-chip${activeCategory === category ? " selected" : ""}`} onClick={() => setActiveCategory(category)} type="button">{category}</button>)}
              </div>
              <button className="feed-model-course-invite" onClick={() => setActiveView("discover")} type="button">
                <span className="feed-model-course-icon"><Icon name="route" size={17} /></span>
                <span><small>JOURNEYS SHARED BY TRAVELERS</small><strong>誰かのモデルコースをのぞいてみる</strong></span>
                <Icon name="arrow" size={16} />
              </button>
              <RegionalRecommendations recommendations={recommendations} compact onCreateRoute={createRegionalRoute} />

              <div className="feed-list">
                {visibleSpots.map((spot, index) => {
                  const isSaved = savedIds.includes(spot.id);
                  return (
                    <article className="spot-card" key={spot.id}>
                      <div className="media-panel">
                        {spot.video_url ? <video className="spot-media" autoPlay muted loop playsInline preload="metadata" poster={spot.image_url} aria-label={`${spot.region}のサンプル動画`}><source src={spot.video_url} type="video/mp4" /></video> : <img className="spot-media" src={spot.image_url} alt={`${spot.region}をイメージしたサンプル写真`} loading={index === 0 ? "eager" : "lazy"} />}
                        <div className="media-shade" />
                        <div className="media-topline"><span className="creator-avatar">{spot.creator.slice(0, 1)}</span><span>{spot.creator}<small> · JAPAN LOCAL JOURNAL</small></span><span className="media-more">•••</span></div>
                        <div className="media-location"><span className="location-pin"><Icon name="pin" size={14} /></span><span>{spot.region}<small>{spot.prefecture} · JAPAN</small></span></div>
                        {spot.is_world_heritage && <div className="media-heritage-badge"><span>✦</span> 世界遺産 <small>{spot.heritage_name}</small></div>}
                        <div className="media-title"><span className="category-label">{spot.category}</span><h2>{spot.title}</h2><p>{spot.description}</p></div>
                        <div className="media-index"><span>0{index + 1}</span><span />{String(visibleSpots.length).padStart(2, "0")}</div>
                        <div className="media-actions"><button className={`like-button${isSaved ? " liked" : ""}`} type="button" onClick={() => toggleSavedSpot(spot)} aria-pressed={isSaved} aria-label={isSaved ? `${spot.region}をマイマップから外す` : `${spot.region}をいいねしてマイマップに保存`}><Icon name="heart" size={25} /><span>{isSaved ? "行きたい！" : "行きたい"}</span></button><span className="like-count">{(spot.likes + (isSaved ? 1 : 0)).toLocaleString("ja-JP")}</span><span className="media-action-divider" /><span className="gesture-hint">↓ SCROLL TO WANDER</span></div>
                      </div>
                      <div className="discovery-panel">
                        <div className="discovery-heading"><span className="discovery-icon"><Icon name="sparkle" size={16} /></span><div><span>LOCAL ONLY</span><strong>この土地だけの、小さな出会い。</strong></div><span className="discovery-prefecture">{spot.prefecture}</span></div>
                        <div className="local-discoveries">
                          <div><span className="local-icon food-icon">味</span><span><small>ここで食べたい</small><strong>{spot.local_food}</strong></span></div>
                          <span className="discovery-divider" />
                          <div><span className="local-icon nature-icon">森</span><span><small>ここで会いたい</small><strong>{spot.local_species}</strong></span></div>
                        </div>
                        <div className="tag-row">{spot.tags.map((tag) => <span key={tag}># {tag}</span>)}</div>
                        <button className={visitedIds.includes(spot.id) ? "visited-toggle is-visited feed-visited-toggle" : "visited-toggle feed-visited-toggle"} onClick={() => toggleVisitedSpot(spot)} type="button" aria-pressed={visitedIds.includes(spot.id)}>{visitedIds.includes(spot.id) ? "行った場所に記録済み ✓" : "ここに行ったことがある"}</button>
                      </div>
                    </article>
                  );
                })}
                {visibleSpots.length === 0 && <div className="empty-filter"><Icon name="compass" size={32} /><strong>このカテゴリーのスポットは準備中です。</strong><button type="button" onClick={() => setActiveCategory("すべて")}>すべての景色を見る</button></div>}
              </div>
              <p className="feed-end-note">まだ知らない場所は、まだまだたくさん。<span>次の景色に出会うまで、のんびりスクロール。</span></p>
            </section>

            <aside className="right-column" aria-label="マイマップのプレビュー">
              <div className="wishlist-card">
                <div className="wishlist-heading"><div><span className="eyebrow">YOUR LITTLE WISH MAP</span><h2>いつか行きたい、<br />が増えていく。</h2></div><span className="wishlist-count">{String(savedSpots.length).padStart(2, "0")}<small>PLACES</small></span></div>
                <div className="mini-region-overview" aria-label="地域ごとの保存スポット数">
                  {regionalGroups.map(({ region, spots: regionSpots }) => (
                    <button
                      className={`mini-region-chip${regionSpots.length > 0 ? " has-pins" : ""}`}
                      key={region.id}
                      onClick={() => { setSelectedRegionId(region.id); setActiveView("map"); }}
                      type="button"
                    >
                      <span>{region.shortName}</span><strong>{regionSpots.length}</strong>
                    </button>
                  ))}
                </div>
                {savedSpots.length > 0 ? <div className="saved-preview">{savedSpots.slice(0, 2).map((spot) => <button key={spot.id} type="button" onClick={() => { setActiveView("map"); setSelectedSpotId(spot.id); }}><img src={spot.image_url} alt="" /><span><strong>{spot.region.split(",")[0]}</strong><small>{spot.prefecture}</small></span><Icon name="arrow" size={16} /></button>)}</div> : <p className="wishlist-empty">気になる場所に「行きたい」すると、<br />ここに景色が集まります。</p>}
                <button className="view-map-button" type="button" onClick={() => setActiveView("map")}>マイマップをひらく <Icon name="arrow" size={16} /></button>
              </div>
              <div className="editor-note"><span className="editor-doodle">“</span><p>行き先を決めていなくても、<br />旅はもう始まっているのかも。</p><span>— よりみち編集部</span></div>
              <div className="service-note"><span>この試作について</span><p>地図のピンはブラウザー内に保存されます。実際の地図・SNSサービスは未実装です。</p></div>
            </aside>
          </div>
        ) : activeView === "map" ? (
          <section className="map-page" aria-label="マイマップ">
            <div className="map-page-intro"><div><p className="eyebrow"><Icon name="map" size={14} /> YOUR SAVED PLACES</p><h1>「いつか行きたい」を、<br /><em>地図の上に。</em></h1><p className="intro-description">フィードで出会った景色は、ここにそっと残ります。</p></div><span className="map-total">{String(savedSpots.length).padStart(2, "0")}<small>PLACES TO WANDER</small></span></div>
            <RegionalRecommendations recommendations={recommendations} onCreateRoute={createRegionalRoute} />
            <div className="map-layout">
              <RegionalMap spots={savedSpots} selectedRegionId={selectedRegionId} onSelectRegion={setSelectedRegionId} />
              <div className="map-detail-column">
                <div className="map-selection-header">
                  <button
                    aria-pressed={routeSelectionMode}
                    className={`map-selection-toggle${routeSelectionMode ? " is-active" : ""}`}
                    onClick={toggleRouteSelectionMode}
                    type="button"
                  >
                    {routeSelectionMode ? "選択モードを終了" : "今回のスポットを選ぶ"}
                  </button>
                  {routeSelectionMode && <span>{selectedRouteSpotIds?.length ?? 0}件を選択中</span>}
                </div>
                <div className="map-list-heading"><div><span className="eyebrow">A MAP OF YOUR CURIOSITY</span><h2>{selectedRegion ? `${selectedRegion.name}の景色` : "集めた景色"} <span>{mapSpots.length}</span></h2></div><span className="sort-note">{selectedRegion ? "エリアで絞り込み中" : "すべてのエリア"}</span></div>
                {routeSelectionMode && (
                  <div className="map-selection-tools">
                    <p>チェックしたスポットだけを今回のルートに組み込みます。</p>
                    <div>
                      <button onClick={selectVisibleRouteSpots} type="button">表示中をすべて選択</button>
                      <button onClick={clearRouteSpotSelection} type="button">選択を解除</button>
                      <button
                        className="button-primary"
                        disabled={!selectedRouteSpotIds?.length || routeLoading}
                        onClick={createSelectedRoute}
                        type="button"
                      >
                        {selectedRouteSpotIds?.length ?? 0}件でルートを作成 <Icon name="arrow" size={14} />
                      </button>
                    </div>
                  </div>
                )}
                {savedSpots.length === 0 ? <div className="map-empty"><span className="map-empty-illustration"><Icon name="heart" size={26} /></span><strong>地図は、まだまっさら。</strong><p>フィードで心に残る場所を見つけたら、<br />「行きたい」を押して集めてみて。</p><button className="button-primary" onClick={() => setActiveView("feed")} type="button">景色を見つける <Icon name="arrow" size={16} /></button></div> : mapSpots.length === 0 ? <div className="map-empty region-filter-empty"><span className="map-empty-illustration"><Icon name="map" size={24} /></span><strong>{selectedRegion?.name}のピンは、まだありません。</strong><p>別のエリアを選ぶか、全国の保存スポットを表示してください。</p></div> : (
                  <>
                    <div className="saved-list">{mapSpots.map((spot) => {
                      const routeSelected = selectedRouteSpotIds?.includes(spot.id) ?? false;
                      return (
                        <div className={`saved-place-row${routeSelectionMode && routeSelected ? " is-route-selected" : ""}`} key={spot.id}>
                          <button className={`saved-place${selectedMapSpot?.id === spot.id ? " selected" : ""}`} onClick={() => setSelectedSpotId(spot.id)} type="button" aria-pressed={selectedMapSpot?.id === spot.id}>
                            <img src={spot.image_url} alt="" />
                            <span className="saved-place-copy"><small>{spot.prefecture} · {spot.category}{visitedIds.includes(spot.id) ? " · 行った" : ""}</small><strong>{spot.region.split(",")[0]}</strong><span>{spot.local_food}</span></span>
                            <span className="saved-heart"><Icon name="heart" size={17} /></span>
                          </button>
                          {routeSelectionMode && (
                            <label className="route-spot-checkbox">
                              <input
                                checked={routeSelected}
                                onChange={() => toggleRouteSpot(spot.id)}
                                type="checkbox"
                              />
                              <span>今回</span>
                            </label>
                          )}
                        </div>
                      );
                    })}</div>
                    {selectedMapSpot && <article className="map-selected-card"><img src={selectedMapSpot.image_url} alt={`${selectedMapSpot.region}のサンプル写真`} /><div className="map-selected-copy"><span className="eyebrow">SAVED IN YOUR MAP</span>{selectedMapSpot.is_world_heritage && <span className="map-heritage-mark">✦ 世界遺産 · {selectedMapSpot.heritage_name}</span>}<h3>{selectedMapSpot.title}</h3><p>{selectedMapSpot.description}</p><div className="selected-local-info"><span>味わう · {selectedMapSpot.local_food}</span><span>出会う · {selectedMapSpot.local_species}</span></div><div className="map-trivia"><span><Icon name="sparkle" size={13} /> 知ってた？</span><p>{selectedMapSpot.local_trivia}</p></div><button type="button" onClick={() => { setActiveCategory("すべて"); setActiveView("feed"); }}>フィードでもう一度見る <Icon name="arrow" size={14} /></button><button className={visitedIds.includes(selectedMapSpot.id) ? "visited-toggle is-visited" : "visited-toggle"} onClick={() => toggleVisitedSpot(selectedMapSpot)} type="button" aria-pressed={visitedIds.includes(selectedMapSpot.id)}>{visitedIds.includes(selectedMapSpot.id) ? "行った場所に記録済み ✓" : "ここに行ったことがある"}</button></div></article>}
                  </>
                )}
              </div>
            </div>
            <p className="map-disclaimer">エリアマップは日本の地域区分を使ったサンプル表示です。実際の地図・経路情報には接続していません。</p>
          </section>
        ) : activeView === "route" ? (
          <RoutePlanner
            savedSpots={savedSpots}
            selectedSpotIds={routeSpotIds ?? savedIds}
            areaName={routeAreaName}
            event={routeEvent}
            routePlan={routePlan}
            loading={routeLoading}
            error={routeError}
            sharing={routeShareLoading}
            shareMessage={routeShareMessage}
            shareError={routeShareError}
            onSelectionChange={updateRouteSelection}
            onGenerate={(spotIds) => void generateRoute(spotIds, routeAreaName, routeEvent)}
            onShare={(title) => void shareCurrentRoute(title)}
            onBrowseFeed={() => setActiveView("feed")}
          />
        ) : activeView === "discover" ? (
          <ModelCourseDiscover courses={modelCourses} spots={spots} savedIds={savedIds} onSaveSpot={saveModelCourseSpot} />
        ) : activeView === "events" ? (
          <EventCalendar
            events={events}
            spots={spots}
            savedIds={savedIds}
            visitedIds={visitedIds}
            onToggleSave={toggleSavedSpot}
            onToggleVisited={toggleVisitedSpot}
            onCreateRoute={createEventRoute}
          />
        ) : (
          <MemoryJournal memories={memories} spots={spots} visitedIds={visitedIds} onToggleVisited={toggleVisitedSpot} />
        )}
        <footer className="footer"><span>よりみち <b>·</b> 旅心に、寄り道を。</span><span>日本のサンプルスポット · 外部サービス未接続</span></footer>
      </main>
      <nav className="mobile-nav" aria-label="メインナビゲーション">
        <button className={activeView === "feed" ? "mobile-nav-item active" : "mobile-nav-item"} onClick={() => setActiveView("feed")} type="button"><Icon name="compass" size={21} /><span>見つける</span></button>
        <button className={activeView === "map" ? "mobile-nav-item active" : "mobile-nav-item"} onClick={() => setActiveView("map")} type="button"><span className="mobile-map-icon"><Icon name="map" size={21} />{savedSpots.length > 0 && <i />}</span><span>マイマップ</span></button>
        <button className={activeView === "route" ? "mobile-nav-item active" : "mobile-nav-item"} onClick={openAllSavedRoute} type="button"><Icon name="route" size={21} /><span>旅行プラン</span></button>
        <button className={activeView === "discover" ? "mobile-nav-item active" : "mobile-nav-item"} onClick={() => setActiveView("discover")} type="button"><Icon name="compass" size={21} /><span>モデルコース</span></button>
        <button className={activeView === "events" ? "mobile-nav-item active" : "mobile-nav-item"} onClick={() => setActiveView("events")} type="button"><Icon name="sparkle" size={21} /><span>季節の行事</span></button>
        <button className={activeView === "memories" ? "mobile-nav-item active" : "mobile-nav-item"} onClick={() => setActiveView("memories")} type="button"><Icon name="bookmark" size={21} /><span>思い出</span></button>
      </nav>
    </div>
  );
}

export default App;
