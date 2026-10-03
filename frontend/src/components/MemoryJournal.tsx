import { useMemo, useState } from "react";
import type { Spot, TravelMemory } from "../types";
import { Icon } from "./Icon";

type MemoryJournalProps = {
  memories: TravelMemory[];
  spots: Spot[];
  visitedIds: string[];
  onToggleVisited: (spot: Spot) => void;
};

const MAP_WIDTH = 800;
const MAP_HEIGHT = 440;
const MAP_PADDING = 46;

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "Asia/Tokyo",
  }).format(new Date(value));
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(new Date(value));
}

export function MemoryJournal({ memories, spots, visitedIds, onToggleVisited }: MemoryJournalProps) {
  const [selectedMemoryId, setSelectedMemoryId] = useState(memories[0]?.id ?? "");
  const [selectedPhotoId, setSelectedPhotoId] = useState<string | null>(null);
  const selectedMemory = memories.find((memory) => memory.id === selectedMemoryId) ?? memories[0];
  const selectedPhoto = selectedMemory?.photos.find((photo) => photo.id === selectedPhotoId)
    ?? selectedMemory?.photos[0]
    ?? null;

  const projected = useMemo(() => {
    if (!selectedMemory) return null;
    const points = [...selectedMemory.route, ...selectedMemory.photos].map((point) => ({
      latitude: point.latitude,
      longitude: point.longitude,
    }));
    const longitudes = points.map((point) => point.longitude);
    const latitudes = points.map((point) => point.latitude);
    const minLongitude = Math.min(...longitudes);
    const maxLongitude = Math.max(...longitudes);
    const minLatitude = Math.min(...latitudes);
    const maxLatitude = Math.max(...latitudes);
    const longitudeSpan = maxLongitude - minLongitude || 0.01;
    const latitudeSpan = maxLatitude - minLatitude || 0.01;
    const project = (latitude: number, longitude: number) => ({
      x: MAP_PADDING + ((longitude - minLongitude) / longitudeSpan) * (MAP_WIDTH - MAP_PADDING * 2),
      y: MAP_HEIGHT - MAP_PADDING - ((latitude - minLatitude) / latitudeSpan) * (MAP_HEIGHT - MAP_PADDING * 2),
    });

    return {
      project,
      routePoints: selectedMemory.route.map((point) => project(point.latitude, point.longitude)),
      routeLine: selectedMemory.route
        .map((point) => {
          const location = project(point.latitude, point.longitude);
          return `${location.x},${location.y}`;
        })
        .join(" "),
    };
  }, [selectedMemory]);

  if (!selectedMemory || !projected) {
    return (
      <section className="memory-page" aria-label="思い出">
        <div className="memory-intro">
          <p className="eyebrow"><Icon name="sparkle" size={14} /> YOUR TRAVEL MEMORIES</p>
          <h1>旅の余韻を、<br /><em>たどる場所。</em></h1>
        </div>
        <div className="memory-empty"><Icon name="map" size={28} /><strong>思い出のサンプルを読み込めませんでした。</strong></div>
      </section>
    );
  }

  return (
    <section className="memory-page" aria-label="思い出">
      <div className="memory-intro">
        <div>
          <p className="eyebrow"><Icon name="sparkle" size={14} /> YOUR TRAVEL MEMORIES</p>
          <h1>旅の余韻を、<br /><em>たどる場所。</em></h1>
          <p className="intro-description">歩いた道と、その時刻に撮った写真を重ねて振り返る。</p>
        </div>
        <span className="memory-intro-stamp">LIFE<small>IN MOMENTS</small></span>
      </div>

      <div className="memory-sample-note" role="note">
        <strong>サンプルの旅行履歴・写真です</strong>
        <span>地図線・撮影日時・位置情報はモックデータです。写真のアップロード、端末のカメラロール参照、EXIF読み取りは行いません。</span>
      </div>

      <div className="memory-trip-rail" aria-label="旅行履歴を選択">
        {memories.map((memory) => (
          <button
            aria-pressed={selectedMemory.id === memory.id}
            className={`memory-trip-chip${selectedMemory.id === memory.id ? " selected" : ""}`}
            key={memory.id}
            onClick={() => {
              setSelectedMemoryId(memory.id);
              setSelectedPhotoId(null);
            }}
            type="button"
          >
            <span>{formatDate(memory.visited_at)}</span>
            <strong>{memory.title}</strong>
            <small>{memory.region} · {memory.photos.length}枚</small>
          </button>
        ))}
      </div>

      <article className="memory-story-card">
        <div className="memory-story-heading">
          <span className="eyebrow">A DAY HELD IN THE HEART</span>
          <h2>{selectedMemory.title}</h2>
          <p>{formatDate(selectedMemory.visited_at)} · {selectedMemory.region}</p>
          <blockquote>{selectedMemory.note}</blockquote>
        </div>
        <div className="memory-map-board" aria-label={`${selectedMemory.title}のサンプル経路と写真の位置`}>
          <div className="memory-map-caption"><span>MEMORY ROUTE</span><span>{selectedMemory.route.length} PLACES · {selectedMemory.photos.length} PHOTOS</span></div>
          <svg className="memory-route-svg" viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} role="img" aria-label="サンプル旅行経路の線">
            <defs>
              <pattern id="memory-grid" width="36" height="36" patternUnits="userSpaceOnUse">
                <path d="M 36 0 L 0 0 0 36" fill="none" stroke="#d9ded4" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="url(#memory-grid)" />
            <path d={`M ${projected.routeLine}`} className="memory-route-line" />
            {selectedMemory.route.map((point, index) => {
              const location = projected.routePoints[index];
              return (
                <g key={`${point.spot_id}-${index}`}>
                  <circle className="memory-route-stop" cx={location.x} cy={location.y} r="7" />
                  <text className="memory-route-label" x={location.x + 13} y={location.y - 10}>{point.label}</text>
                </g>
              );
            })}
          </svg>
          {selectedMemory.photos.map((photo) => {
            const location = projected.project(photo.latitude, photo.longitude);
            const left = `${(location.x / MAP_WIDTH) * 100}%`;
            const top = `${(location.y / MAP_HEIGHT) * 100}%`;
            return (
              <button
                aria-label={`${formatTime(photo.captured_at)} ${photo.caption}の写真を表示`}
                className={`memory-photo-pin${selectedPhoto?.id === photo.id ? " selected" : ""}`}
                key={photo.id}
                onClick={() => setSelectedPhotoId(photo.id)}
                style={{ left, top }}
                type="button"
              >
                <img src={photo.image_url} alt="" />
                <span>{formatTime(photo.captured_at)}</span>
              </button>
            );
          })}
          <span className="memory-map-disclaimer">位置関係を示すサンプル図 · 実際の地図ではありません</span>
        </div>

        {selectedPhoto && (
          <div className="memory-photo-feature" aria-live="polite">
            <img src={selectedPhoto.image_url} alt={selectedPhoto.caption} />
            <div>
              <span>{formatDate(selectedPhoto.captured_at)} · {formatTime(selectedPhoto.captured_at)}</span>
              <h3>{selectedPhoto.caption}</h3>
              <p><Icon name="pin" size={13} /> {selectedMemory.route.find((point) => point.spot_id === selectedPhoto.spot_id)?.label ?? selectedMemory.region}</p>
            </div>
            <span className="memory-photo-count">{selectedMemory.photos.findIndex((photo) => photo.id === selectedPhoto.id) + 1}<small> / {selectedMemory.photos.length}</small></span>
          </div>
        )}

        <div className="memory-photo-strip" aria-label="思い出の写真">
          {selectedMemory.photos.map((photo) => (
            <button
              aria-label={`${formatTime(photo.captured_at)} ${photo.caption}`}
              aria-pressed={selectedPhoto?.id === photo.id}
              className={`memory-photo-thumb${selectedPhoto?.id === photo.id ? " selected" : ""}`}
              key={photo.id}
              onClick={() => setSelectedPhotoId(photo.id)}
              type="button"
            >
              <img src={photo.image_url} alt="" />
              <span>{formatTime(photo.captured_at)}</span>
            </button>
          ))}
        </div>
      </article>

      <div className="memory-visited-list">
        <div className="memory-visited-heading"><span className="eyebrow">PLACES I HAVE BEEN</span><strong>「行った」場所</strong><span>{visitedIds.length} SPOTS</span></div>
        {selectedMemory.route.map((point) => {
          const spot = spots.find((item) => item.id === point.spot_id);
          if (!spot) return null;
          const isVisited = visitedIds.includes(spot.id);
          return (
            <div className="memory-visited-row" key={spot.id}>
              <img src={spot.image_url} alt="" />
              <span><strong>{point.label}</strong><small>{spot.prefecture} · {spot.is_world_heritage ? `✦ 世界遺産 ${spot.heritage_name}` : spot.local_trivia}</small></span>
              <button className={isVisited ? "visited-toggle is-visited" : "visited-toggle"} onClick={() => onToggleVisited(spot)} type="button" aria-pressed={isVisited}>
                {isVisited ? "行った ✓" : "行った"}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
