import { describe, it, expect } from "vitest";
import { computeOverallRating } from "./overallRating";
import type { EvaluationZone } from "./evaluation";
import golden from "./__fixtures__/overall_rating_golden.json";

// この golden vector は backend/apps/stocks/tests/fixtures/overall_rating_golden.json と
// 同一内容（BEの test_golden_fixtures_in_sync が両ファイルの一致を検証）。TS/Python の
// 総合評価スコア一致を担保する。ケースを変えたら両ファイルを更新し双方のテストを再実行すること。

const num = (v: string | number | null | undefined): number | null =>
  v == null ? null : typeof v === "number" ? v : Number(v);

describe("computeOverallRating (golden vector, TS/Python 一致)", () => {
  for (const c of golden.cases) {
    it(c.name, () => {
      const i = c.inputs as Record<string, string | number | null>;
      const score = computeOverallRating({
        evaluationZone: (i.evaluation_zone as EvaluationZone | null) ?? null,
        growthRateLabel: (i.growth_rate_label as string | null) ?? null,
        roeTrend: (i.roe_trend as "improving" | "declining" | "stable" | null) ?? null,
        epsCagr3y: num(i.eps_cagr_3y),
        epsGrowthYoy: num(i.eps_growth_yoy),
        slRatio: num(i.sl_ratio),
        momentumSignal:
          (i.momentum_signal as "strong_buy" | "buy" | "neutral" | "caution" | "sell" | null) ?? null,
        dividendYield: num(i.dividend_yield),
        payoutRatio: num(i.payout_ratio),
        consecutiveDividendYears: num(i.consecutive_dividend_years),
        progressiveDividendYears: num(i.progressive_dividend_years),
        fcfYield: num(i.fcf_yield),
        fcfMargin: num(i.fcf_margin),
        fcf: num(i.fcf),
        prevFcf: num(i.prev_fcf),
      }).score;
      expect(score).toBe(c.expected_score);
    });
  }
});
