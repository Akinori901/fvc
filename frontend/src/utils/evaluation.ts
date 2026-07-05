export type EvaluationZone =
  | "very_cheap"
  | "cheap"
  | "fair"
  | "expensive"
  | "very_expensive";

export interface ZoneInfo {
  zone: EvaluationZone;
  label: string;
  color: string;
  bgColor: string;
}

const VERY_CHEAP: ZoneInfo = { zone: "very_cheap", label: "超割安", color: "#1b5e20", bgColor: "#e8f5e9" };
const CHEAP: ZoneInfo = { zone: "cheap", label: "割安", color: "#2e7d32", bgColor: "#c8e6c9" };
const FAIR: ZoneInfo = { zone: "fair", label: "適正", color: "#f57f17", bgColor: "#fff9c4" };
const EXPENSIVE: ZoneInfo = { zone: "expensive", label: "割高", color: "#e65100", bgColor: "#ffe0b2" };
const VERY_EXPENSIVE: ZoneInfo = { zone: "very_expensive", label: "危険", color: "#b71c1c", bgColor: "#ffcdd2" };

const ZONES: ZoneInfo[] = [VERY_CHEAP, CHEAP, FAIR, EXPENSIVE, VERY_EXPENSIVE];

/**
 * 乖離率から評価ゾーンを判定
 * discount_rate > 0: 割安（現在価格 < 適正価格）
 * discount_rate < 0: 割高（現在価格 > 適正価格）
 */
export function getEvaluationZone(discountRate: number): ZoneInfo {
  if (discountRate >= 0.3) return VERY_CHEAP;
  if (discountRate >= 0.1) return CHEAP;
  if (discountRate >= -0.1) return FAIR;
  if (discountRate >= -0.3) return EXPENSIVE;
  return VERY_EXPENSIVE;
}

export function getAllZones(): ZoneInfo[] {
  return ZONES;
}

export function getZoneInfoByZone(zone: EvaluationZone): ZoneInfo {
  return ZONES.find((z) => z.zone === zone) ?? VERY_EXPENSIVE;
}
