import type { EvaluationZone } from "./evaluation";

export interface SignalItem {
  category: string;
  label: string;
  impact: number;
}

export interface OverallRatingResult {
  label: string;
  score: number;
  color: string;
  bgColor: string;
  signals: SignalItem[];
}

interface ComputeInputs {
  evaluationZone: EvaluationZone | null;
  growthRateLabel: string | null;
  roeTrend: "improving" | "declining" | "stable" | null;
  epsCagr3y: number | null;
  epsGrowthYoy: number | null;
  slRatio: number | null;
  momentumSignal?: "strong_buy" | "buy" | "neutral" | "caution" | "sell" | null;
  dividendYield?: number | null;
  payoutRatio?: number | null;
  consecutiveDividendYears?: number | null;
  progressiveDividendYears?: number | null;
  fcfYield?: number | null;
  fcfMargin?: number | null;
  fcf?: number | null;
  prevFcf?: number | null;
}

export function computeOverallRating(inputs: ComputeInputs): OverallRatingResult {
  const signals: SignalItem[] = [];
  let score = 0;

  // --- バリュエーション ---
  const valuation = (() => {
    switch (inputs.evaluationZone) {
      case "very_cheap":  return { impact: +3, label: "超割安（30%以上割安）" };
      case "cheap":       return { impact: +1, label: "割安（10〜30%割安）" };
      case "fair":        return { impact:  0, label: "適正（±10%）" };
      case "expensive":   return { impact: -2, label: "割高（10〜30%割高）" };
      case "very_expensive": return { impact: -4, label: "危険（30%以上割高）" };
      default:            return { impact:  0, label: "データなし" };
    }
  })();
  score += valuation.impact;
  signals.push({ category: "評価ゾーン", label: valuation.label, impact: valuation.impact });

  // --- 成長率評価 ---
  const growth = (() => {
    switch (inputs.growthRateLabel) {
      case "かなり強気":       return { impact: +2, label: "かなり強気（市場折込成長率≥7%）" };
      case "非常に優秀":
      case "優秀":             return { impact: +1, label: `${inputs.growthRateLabel}（市場折込成長率≥3%）` };
      case "普通":
      case "低成長":           return { impact:  0, label: `${inputs.growthRateLabel}（市場折込成長率≥0%）` };
      case "マイナス成長":     return { impact: -1, label: "マイナス成長（市場折込成長率<0%）" };
      case "ROE持続性に疑念":  return { impact: -2, label: "ROE持続性に疑念（PBR<1, 市場が収益力を不信視）" };
      default:                 return { impact:  0, label: "データなし" };
    }
  })();
  score += growth.impact;
  signals.push({ category: "成長率評価", label: growth.label, impact: growth.impact });

  // --- ROEトレンド ---
  const roeTrendImpact = (() => {
    switch (inputs.roeTrend) {
      case "improving": return { impact: +1, label: "3期連続改善" };
      case "declining": return { impact: -1, label: "3期連続悪化" };
      case "stable":    return { impact:  0, label: "横ばい" };
      default:          return { impact:  0, label: "データなし" };
    }
  })();
  score += roeTrendImpact.impact;
  signals.push({ category: "ROEトレンド", label: roeTrendImpact.label, impact: roeTrendImpact.impact });

  // --- EPS成長（3年CAGRを優先、なければYoY）---
  const epsGrowth = inputs.epsCagr3y ?? inputs.epsGrowthYoy;
  const epsImpact = (() => {
    if (epsGrowth == null) return { impact: 0, label: "データなし" };
    const source = inputs.epsCagr3y != null ? "CAGR3年" : "前年比";
    const pct = (epsGrowth * 100).toFixed(1);
    if (epsGrowth >= 0.2) return { impact: +1, label: `${pct}%（${source}、高成長）` };
    if (epsGrowth <= -0.2) return { impact: -1, label: `${pct}%（${source}、大幅減益）` };
    return { impact: 0, label: `${pct}%（${source}、中程度）` };
  })();
  score += epsImpact.impact;
  signals.push({ category: "EPS成長", label: epsImpact.label, impact: epsImpact.impact });

  // --- 信用残高（信売比率）---
  const marginImpact = (() => {
    if (inputs.slRatio == null) return { impact: 0, label: "データなし" };
    const r = inputs.slRatio;
    const fmt = r.toFixed(2);
    if (r < 0.05) return { impact: -4, label: `信売比率 ${fmt} — 極端な買い偏り（強制売りリスク大）` };
    if (r < 0.30) return { impact: -1, label: `信売比率 ${fmt} — 買い偏り` };
    if (r <= 2.00) return { impact:  0, label: `信売比率 ${fmt} — 均衡` };
    return { impact: 0, label: `信売比率 ${fmt} — 売り偏り` };
  })();
  score += marginImpact.impact;
  signals.push({ category: "信用残高", label: marginImpact.label, impact: marginImpact.impact });

  // --- モメンタム（52週高値効果）---
  const momentumImpact = (() => {
    switch (inputs.momentumSignal) {
      case "strong_buy": return { impact: +2, label: "52w高値近接 + 出来高急増" };
      case "buy":        return { impact: +1, label: "上昇トレンド確認" };
      case "neutral":    return { impact:  0, label: "中間圏" };
      case "caution":    return { impact: -1, label: "下落トレンド" };
      case "sell":       return { impact: -1, label: "底値圏" };
      default:           return { impact:  0, label: "データなし" };
    }
  })();
  score += momentumImpact.impact;
  signals.push({ category: "モメンタム", label: momentumImpact.label, impact: momentumImpact.impact });

  // --- 配当評価 ---
  const dividendImpact = (() => {
    const dy = inputs.dividendYield;
    const pr = inputs.payoutRatio;
    const consec = inputs.consecutiveDividendYears;
    const prog = inputs.progressiveDividendYears;

    if (dy == null || dy === 0) {
      if (dy === 0) return { impact: -1, label: "無配" };
      return { impact: 0, label: "データなし" };
    }
    const highYield = dy >= 3.5;
    const riskyPayout = pr != null && pr > 70;
    const healthyPayout = pr == null || pr <= 60;

    if (highYield && riskyPayout) {
      if (prog == null || prog === 0) {
        return { impact: -2, label: `利回り${dy.toFixed(1)}% / 性向${pr!.toFixed(0)}% + 累進なし` };
      }
      return { impact: -1, label: `利回り${dy.toFixed(1)}% / 性向${pr!.toFixed(0)}%（持続性リスク）` };
    }
    if (highYield && healthyPayout) {
      if (prog != null && prog >= 3) {
        return { impact: +2, label: `利回り${dy.toFixed(1)}% / 性向${pr?.toFixed(0) ?? "N/A"}% / 累進${prog}年` };
      }
      return { impact: +1, label: `高配当${dy.toFixed(1)}% + 健全性向` };
    }
    if (consec != null && consec >= 5) {
      return { impact: +1, label: `連続配当${consec}年` };
    }
    return { impact: 0, label: `配当あり（利回り${dy.toFixed(1)}%）` };
  })();
  score += dividendImpact.impact;
  signals.push({ category: "配当評価", label: dividendImpact.label, impact: dividendImpact.impact });

  // --- FCF評価 ---
  const fcfImpact = (() => {
    const fcf = inputs.fcf;
    const fy = inputs.fcfYield;
    const fm = inputs.fcfMargin;

    if (fcf == null) return { impact: 0, label: "データなし" };

    if (fcf < 0) {
      if (inputs.prevFcf != null && inputs.prevFcf < 0) {
        return { impact: -2, label: "FCF 2期連続マイナス" };
      }
      return { impact: -1, label: "FCFマイナス" };
    }

    if (fy != null && fy >= 8 && fm != null && fm >= 10) {
      return { impact: +2, label: `FCF利回り${fy.toFixed(1)}% + マージン${fm.toFixed(0)}%` };
    }
    if (fy != null && fy >= 5) {
      return { impact: +1, label: `FCF利回り${fy.toFixed(1)}%` };
    }
    return { impact: 0, label: `FCFプラス${fy != null ? `（利回り${fy.toFixed(1)}%）` : ""}` };
  })();
  score += fcfImpact.impact;
  signals.push({ category: "FCF評価", label: fcfImpact.label, impact: fcfImpact.impact });

  // --- ラベル決定 ---
  const rating = (() => {
    if (score >= 6) return { label: "超割安",   color: "#1b5e20", bgColor: "#e8f5e9" };
    if (score >= 2) return { label: "買い推奨", color: "#2e7d32", bgColor: "#c8e6c9" };
    if (score >= -1) return { label: "レンジ中", color: "#f57f17", bgColor: "#fff9c4" };
    if (score >= -5) return { label: "下落警戒", color: "#e65100", bgColor: "#ffe0b2" };
    return             { label: "購入危険",   color: "#b71c1c", bgColor: "#ffcdd2" };
  })();

  return { ...rating, score, signals };
}
