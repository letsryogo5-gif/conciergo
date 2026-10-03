import { useEffect, useState } from "react";
import type { Spot } from "../types";
import { Icon } from "./Icon";

type TriviaToastProps = {
  spots: Spot[];
  savedIds: string[];
  onToggleSave: (spot: Spot) => void;
};

export function TriviaToast({ spots, savedIds, onToggleSave }: TriviaToastProps) {
  const [spotIndex, setSpotIndex] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (spots.length === 0) return;

    let hideTimer: number | undefined;
    const initialTimer = window.setTimeout(() => setVisible(true), 1800);
    const rotationTimer = window.setInterval(() => {
      setSpotIndex((index) => (index + 1) % spots.length);
      setVisible(true);
      window.clearTimeout(hideTimer);
      hideTimer = window.setTimeout(() => setVisible(false), 7200);
    }, 18000);
    hideTimer = window.setTimeout(() => setVisible(false), 9000);

    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(rotationTimer);
      window.clearTimeout(hideTimer);
    };
  }, [spots]);

  if (spots.length === 0) return null;

  const spot = spots[spotIndex % spots.length];
  const isSaved = savedIds.includes(spot.id);

  return (
    <aside className={`trivia-toast${visible ? " is-visible" : ""}`} aria-live="polite" aria-label="地域のちょこっと豆知識">
      <div className="trivia-toast-top"><span className="trivia-orbit"><Icon name="sparkle" size={15} /></span><span><small>DID YOU KNOW?</small><strong>知ってた？</strong></span><button className="trivia-dismiss" onClick={() => setVisible(false)} type="button" aria-label="豆知識を閉じる">×</button></div>
      <p>{spot.local_trivia}</p>
      <div className="trivia-toast-bottom"><span><Icon name="pin" size={12} /> {spot.region.split(",")[0]} · {spot.prefecture}</span><button className={isSaved ? "trivia-save saved" : "trivia-save"} onClick={() => onToggleSave(spot)} type="button" aria-pressed={isSaved}><Icon name="heart" size={14} />{isSaved ? "保存中" : "行きたい"}</button></div>
    </aside>
  );
}
