import { IconButton, Tooltip, Typography, Box } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

interface Props {
  title: React.ReactNode;
}

export default function IndicatorHelpTooltip({ title }: Props) {
  return (
    <Tooltip
      title={title}
      placement="top"
      arrow
      componentsProps={{
        tooltip: { sx: { maxWidth: 300, fontSize: "0.75rem", lineHeight: 1.6 } },
      }}
    >
      <IconButton size="small" sx={{ p: 0, ml: 0.5, color: "text.disabled" }}>
        <HelpOutlineIcon sx={{ fontSize: 14 }} />
      </IconButton>
    </Tooltip>
  );
}

export const HELP_TEXTS = {
  ma: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>移動平均（MA）</Typography>
      <Typography variant="caption" display="block">過去N日間の終値の平均。現在値との乖離率で割安・割高を確認します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・乖離率がマイナス → 移動平均より株価が下 → 下落傾向</Typography>
      <Typography variant="caption" display="block">・乖離率がプラス → 移動平均より株価が上 → 上昇傾向</Typography>
      <Typography variant="caption" display="block" mt={0.5}>25日（短期）・75日（中期）・200日（長期）の順に安定性が高まります。</Typography>
    </Box>
  ),
  bb: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>ボリンジャーバンド（BB）</Typography>
      <Typography variant="caption" display="block">移動平均 ± 2σ（標準偏差）のバンド。統計的に株価の約95%がバンド内に収まります。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・上限突破 → 買われすぎの可能性（反落に注意）</Typography>
      <Typography variant="caption" display="block">・下限割れ → 売られすぎの可能性（反発に期待）</Typography>
      <Typography variant="caption" display="block">・%B: 0が下限、1が上限。0.5が中央</Typography>
    </Box>
  ),
  rsi: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>RSI（相対力指数）</Typography>
      <Typography variant="caption" display="block">0〜100の値。直近の値上がり幅と値下がり幅の比率から算出します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・70以上 → 買われすぎ（赤）：売りシグナル</Typography>
      <Typography variant="caption" display="block">・30以下 → 売られすぎ（緑）：買いシグナル</Typography>
      <Typography variant="caption" display="block">・30〜70 → 中立</Typography>
    </Box>
  ),
  macd: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>MACD（移動平均収束拡散法）</Typography>
      <Typography variant="caption" display="block">短期EMA(12)と長期EMA(26)の差。トレンドの方向と強さを示します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・MACDがシグナルを上抜け → ゴールデンクロス：買いシグナル</Typography>
      <Typography variant="caption" display="block">・MACDがシグナルを下抜け → デッドクロス：売りシグナル</Typography>
      <Typography variant="caption" display="block">・ヒストグラム（棒）: MACD−シグナルの差。プラスで上昇モメンタム</Typography>
    </Box>
  ),
  stoch: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>ストキャスティクス</Typography>
      <Typography variant="caption" display="block">0〜100の値。一定期間の高安値に対する現在値の位置を示します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・80以上 → 買われすぎ（赤）：売りシグナル</Typography>
      <Typography variant="caption" display="block">・20以下 → 売られすぎ（緑）：買いシグナル</Typography>
      <Typography variant="caption" display="block">・%KがシグナルD%を上抜けたときに注目</Typography>
    </Box>
  ),
  atr: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>ATR（平均真の値幅）</Typography>
      <Typography variant="caption" display="block">直近14日間の値動きの平均幅。ボラティリティ（変動の激しさ）を示します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・ATRが大きい → ボラが高い（損失も利益も大きくなりやすい）</Typography>
      <Typography variant="caption" display="block">・ATRが小さい → ボラが低い（安定した動き）</Typography>
      <Typography variant="caption" display="block">・%表示: 株価に対するATRの割合</Typography>
    </Box>
  ),
  momentum: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>モメンタム</Typography>
      <Typography variant="caption" display="block">25日前の株価と現在値の変化率。トレンドの勢いを示します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・プラス → 上昇トレンド中</Typography>
      <Typography variant="caption" display="block">・マイナス → 下落トレンド中</Typography>
      <Typography variant="caption" display="block">・±5%未満が目安で「横ばい」</Typography>
    </Box>
  ),
  etfDividendYield: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>分配金利回り（ETF）</Typography>
      <Typography variant="caption" display="block">年間分配金 ÷ 現在価格 × 100。インカムゲインの効率を示します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・3%以上 → 高利回り（緑表示）</Typography>
      <Typography variant="caption" display="block">・2〜3% → 標準的</Typography>
      <Typography variant="caption" display="block">・2%未満 → 低利回り（値上がり益狙いが主体）</Typography>
    </Box>
  ),
  etfReturn52w: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>52週リターン</Typography>
      <Typography variant="caption" display="block">1年前の価格と現在価格の変化率。中期的なパフォーマンスを示します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・プラス → 1年で価格が上昇</Typography>
      <Typography variant="caption" display="block">・マイナス → 1年で価格が下落</Typography>
      <Typography variant="caption" display="block">・ベンチマーク（日経平均など）との比較が重要</Typography>
    </Box>
  ),
  etfEvaluationZone: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>総合評価ゾーン</Typography>
      <Typography variant="caption" display="block">利回り・リターン・テクニカル等の複数指標を点数化して総合判定します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・超割安 / 買い推奨 → 購入を検討しやすい水準</Typography>
      <Typography variant="caption" display="block">・レンジ中 → 様子見</Typography>
      <Typography variant="caption" display="block">・下落警戒 / 購入危険 → 買い増しは慎重に</Typography>
    </Box>
  ),
  reitPNav: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>P/NAV（純資産価値比率）</Typography>
      <Typography variant="caption" display="block">時価総額 ÷ 純資産価値（NAV）。REITの割安・割高を測る最重要指標です。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・1.0未満（緑）→ 純資産より安く買える＝割安</Typography>
      <Typography variant="caption" display="block">・1.0 → 純資産と等価</Typography>
      <Typography variant="caption" display="block">・1.0超 → プレミアムを払っている状態</Typography>
    </Box>
  ),
  reitDividendYield: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>分配金利回り（REIT）</Typography>
      <Typography variant="caption" display="block">年間分配金 ÷ 現在価格 × 100。REITは収益の90%超を分配するため利回りが高めです。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・4%以上（緑）→ 高利回り水準</Typography>
      <Typography variant="caption" display="block">・3〜4% → 標準的</Typography>
      <Typography variant="caption" display="block">・3%未満 → 低利回り（価格が高い可能性）</Typography>
    </Box>
  ),
  reitNavPerUnit: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>NAV/口（1口あたり純資産）</Typography>
      <Typography variant="caption" display="block">REITが保有する不動産等の純資産を口数で割った理論価値です。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・現在価格 &lt; NAV/口 → 割安（P/NAV &lt; 1.0）</Typography>
      <Typography variant="caption" display="block">・現在価格 &gt; NAV/口 → 割高（P/NAV &gt; 1.0）</Typography>
    </Box>
  ),
  reitEvaluationZone: (
    <Box>
      <Typography variant="caption" display="block" fontWeight="bold" mb={0.5}>総合評価ゾーン</Typography>
      <Typography variant="caption" display="block">P/NAV・分配金利回り・テクニカル等の複数指標を点数化して総合判定します。</Typography>
      <Typography variant="caption" display="block" mt={0.5}>・超割安 / 買い推奨 → 購入を検討しやすい水準</Typography>
      <Typography variant="caption" display="block">・レンジ中 → 様子見</Typography>
      <Typography variant="caption" display="block">・下落警戒 / 購入危険 → 買い増しは慎重に</Typography>
    </Box>
  ),
};
