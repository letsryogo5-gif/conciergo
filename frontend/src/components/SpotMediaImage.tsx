import { useEffect, useRef, useState } from "react";
import type { Spot, SpotMediaResults } from "../types";
import { AttributionCredits } from "./AttributionCredits";

type SpotMediaImageProps = {
  spot: Spot;
  loading?: "eager" | "lazy";
};

export function SpotMediaImage({ spot, loading = "lazy" }: SpotMediaImageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [media, setMedia] = useState<SpotMediaResults | null>(null);
  const [requestFailed, setRequestFailed] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof IntersectionObserver === "undefined") return;

    let active = true;
    let requestStarted = false;
    let controller: AbortController | null = null;

    const loadMedia = async () => {
      if (requestStarted) return;
      requestStarted = true;
      controller = new AbortController();

      try {
        const response = await fetch(
          `/api/spots/${encodeURIComponent(spot.id)}/media?media_type=image&limit=1`,
          { signal: controller.signal },
        );
        if (!response.ok) {
          throw new Error(`メディアAPIがHTTP ${response.status}を返しました。`);
        }
        const result = await response.json() as SpotMediaResults;
        if (
          result.spot_id !== spot.id
          || result.media_type !== "image"
          || !Array.isArray(result.items)
          || !result.items.every((item) => item.media_type === "image")
        ) {
          throw new Error("メディアAPIの応答形式が正しくありません。");
        }
        if (active) setMedia(result);
      } catch (cause) {
        if (active && !(cause instanceof DOMException && cause.name === "AbortError")) {
          setRequestFailed(true);
        }
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void loadMedia();
          observer.disconnect();
        }
      },
      { rootMargin: "160px" },
    );
    observer.observe(container);

    return () => {
      active = false;
      observer.disconnect();
      controller?.abort();
    };
  }, [spot.id]);

  const asset = media?.items[0];
  const unavailableProvider = media?.providers.find((provider) => provider.status === "unavailable");
  const emptyProvider = media?.providers.find((provider) => provider.status === "empty");
  return (
    <div className="spot-media-frame" ref={containerRef}>
      <img
        className="spot-media"
        src={asset?.url ?? spot.image_url}
        alt={`${spot.region}の${asset ? "風景" : "サンプル風景"}`}
        loading={loading}
      />
      {asset ? (
        <AttributionCredits
          className="media-attribution"
          credits={[{
            label: `${asset.source === "pixabay" ? "Pixabay" : "Pexels"}${asset.creator ? ` · ${asset.creator}` : ""}`,
            url: asset.page_url,
            licenseName: asset.source === "pixabay" ? "利用条件" : "Pexels License",
            licenseUrl: asset.source === "pixabay"
              ? "https://pixabay.com/service/license-summary/"
              : "https://www.pexels.com/license/",
          }]}
          label="写真"
        />
      ) : (
        <span className="media-attribution" aria-live={requestFailed ? "polite" : undefined}>
          {requestFailed
            ? "サンプル画像 · 外部取得エラー"
            : unavailableProvider
              ? `${unavailableProvider.provider === "pixabay" ? "Pixabay" : "Pexels"}接続不可 · サンプル画像`
              : emptyProvider
                ? "検索結果なし · サンプル画像"
                : "サンプル画像"}
        </span>
      )}
    </div>
  );
}
