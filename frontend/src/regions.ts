import type { Spot } from "./types";

export const REGION_PIN_THRESHOLD = 3;

export type JapanRegion = {
  id: string;
  name: string;
  shortName: string;
  prefectures: string[];
  className: string;
  note: string;
};

export const JAPAN_REGIONS: JapanRegion[] = [
  {
    id: "hokkaido",
    name: "北海道",
    shortName: "北海道",
    prefectures: ["北海道"],
    className: "region-hokkaido",
    note: "北の大地",
  },
  {
    id: "tohoku",
    name: "東北",
    shortName: "東北",
    prefectures: ["青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"],
    className: "region-tohoku",
    note: "森と海の東北",
  },
  {
    id: "kanto",
    name: "関東",
    shortName: "関東",
    prefectures: ["茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県"],
    className: "region-kanto",
    note: "東京からひと足",
  },
  {
    id: "chubu",
    name: "中部",
    shortName: "中部",
    prefectures: ["新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県"],
    className: "region-chubu",
    note: "山と高原",
  },
  {
    id: "kansai",
    name: "関西",
    shortName: "関西",
    prefectures: ["三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"],
    className: "region-kansai",
    note: "古都と水辺",
  },
  {
    id: "chugoku-shikoku",
    name: "中国・四国",
    shortName: "中国四国",
    prefectures: ["鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県"],
    className: "region-chugoku-shikoku",
    note: "瀬戸内と島々",
  },
  {
    id: "kyushu-okinawa",
    name: "九州・沖縄",
    shortName: "九州沖縄",
    prefectures: ["福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"],
    className: "region-kyushu-okinawa",
    note: "南の島へ",
  },
];

export function getRegionForSpot(spot: Spot): JapanRegion {
  return JAPAN_REGIONS.find((region) => region.prefectures.includes(spot.prefecture)) ?? JAPAN_REGIONS[JAPAN_REGIONS.length - 1];
}

export function getRegionalSpotGroups(spots: Spot[]) {
  return JAPAN_REGIONS.map((region) => ({
    region,
    spots: spots.filter((spot) => region.prefectures.includes(spot.prefecture)),
  }));
}
