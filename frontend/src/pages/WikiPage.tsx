import { useState } from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  InputAdornment,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SearchIcon from "@mui/icons-material/Search";

interface WikiEntry {
  term: string;
  description: string;
}

interface WikiCategory {
  category: string;
  entries: WikiEntry[];
}

const wikiData: WikiCategory[] = [
  {
    category: "ETF関連",
    entries: [
      {
        term: "為替ヘッジあり / なし",
        description:
          "海外資産に投資するETFには「為替ヘッジあり」と「なし」がある。" +
          "「為替ヘッジあり」は為替変動リスクを抑えるため、円高時でも基準価額が下がりにくい。" +
          "一方でヘッジコスト（日米金利差分）がかかるため、リターンが若干低下する。" +
          "「為替ヘッジなし」は為替の影響をそのまま受けるため、円安時にはプラスに、円高時にはマイナスに働く。" +
          "長期投資では為替リスクは平均化されるため「ヘッジなし」、短期〜中期で円高リスクを避けたい場合は「ヘッジあり」が一般的。",
      },
      {
        term: "分配金利回り",
        description:
          "年間分配金 / 現在の基準価額（株価）で算出。" +
          "ETFの場合は決算期ごとに分配金が支払われ、直近12ヶ月の合計から利回りを計算する。" +
          "高配当ETFでは3〜5%程度、インデックスETFでは0〜2%程度が一般的。",
      },
      {
        term: "純資産総額",
        description:
          "そのETFに投資されている資金の総額。" +
          "純資産が大きいほど流動性が高く、売買しやすい。" +
          "一般に100億円以上あれば安心。10億円未満は流動性リスクや繰上償還リスクがある。",
      },
      {
        term: "52週リターン",
        description:
          "過去52週間（約1年間）の価格変動率。" +
          "（現在価格 - 52週前価格）/ 52週前価格 で計算。" +
          "配当は含まないプライスリターン。",
      },
      {
        term: "インデックスファンドとETFの違い",
        description:
          "どちらも指数に連動する投資商品だが、取引方法が異なる。" +
          "ETF（上場投資信託）は株式のようにリアルタイムで売買でき、信託報酬が低い傾向にある。" +
          "インデックスファンド（投資信託）は1日1回の基準価額で取引され、積立投資や少額投資に向いている。" +
          "つみたてNISAではインデックスファンド、まとまった資金の一括投資ではETFが使われることが多い。",
      },
      {
        term: "経費率（信託報酬）",
        description:
          "ETFの運用コストとして毎日差し引かれる手数料。年率で表示される。" +
          "例えば経費率0.1%なら、100万円投資で年間約1,000円。" +
          "同じ指数に連動するETFなら経費率が低いものを選ぶのが基本。",
      },
    ],
  },
  {
    category: "REIT関連",
    entries: [
      {
        term: "P/NAV（Price to Net Asset Value）",
        description:
          "REIT版のPBR。現在の投資口価格 / 1口あたり純資産価値（NAV）で算出。" +
          "P/NAV < 1.0 なら保有不動産の価値より安く買えている状態（割安）。" +
          "P/NAV > 1.0 なら不動産価値にプレミアムが乗っている状態。" +
          "一般にJ-REITでは0.8〜1.2が標準的なレンジ。",
      },
      {
        term: "分配カバレッジ",
        description:
          "1口あたり利益（EPS）/ 年間分配金 で算出。" +
          "1.0以上なら利益で分配金を賄えている健全な状態。" +
          "1.0未満は利益以上の分配を行っており、内部留保の取り崩しや資産売却に依存している可能性がある。",
      },
      {
        term: "J-REIT分配金の仕組み",
        description:
          "J-REITは利益の90%超を分配すると法人税が非課税になる（導管性要件）。" +
          "そのため、ほとんどのJ-REITは利益のほぼ全額を分配金として投資家に還元する。" +
          "決算は年2回（半期ごと）が多く、分配金は決算日から約2〜3ヶ月後に支払われる。",
      },
      {
        term: "NAV（Net Asset Value）",
        description:
          "REITが保有する不動産等の資産から負債を差し引いた純資産価値。" +
          "不動産の鑑定評価額ベースで計算され、REITの「本来の価値」を示す指標。" +
          "本システムではBPS（1口あたり純資産）をNAVの代理指標として使用。",
      },
    ],
  },
  {
    category: "株式関連",
    entries: [
      {
        term: "PBR（Price Book-value Ratio）",
        description:
          "株価純資産倍率 = 株価 / BPS（1株あたり純資産）。" +
          "PBR 1.0倍は「解散価値」と同等。1.0未満は理論上、会社を解散した方が株主にとって得になる水準。" +
          "成長企業は高PBR（2〜10倍）、成熟企業や不人気銘柄は低PBR（0.5〜1.0倍）になりやすい。",
      },
      {
        term: "ROE（Return on Equity）",
        description:
          "自己資本利益率 = 当期純利益 / 自己資本。" +
          "株主が出した資本に対してどれだけ効率的に利益を生んでいるかを示す。" +
          "一般に8%以上が優秀、15%以上はトップクラス。" +
          "本システムではROE = EPS / BPS で計算（J-Quantsの自己資本比率とは異なる）。",
      },
      {
        term: "EPS（Earnings Per Share）",
        description:
          "1株あたり利益 = 当期純利益 / 発行済株式数。" +
          "企業の収益力を1株単位で比較可能にした指標。" +
          "EPS成長率が高い企業は将来の株価上昇が期待される。",
      },
      {
        term: "信用残高（信売比率）",
        description:
          "信売比率 = 信用売り残 / 信用買い残。" +
          "1.0未満は「買い偏り」で、将来の売り圧力（返済売り）が大きい。" +
          "特に0.05未満は極端な買い偏りで、追証による強制決済リスクが高い。" +
          "1.0超は「売り偏り」で、将来の買い戻し需要（踏み上げ）が期待される。",
      },
      {
        term: "Gordon Growth Model（ゴードン成長モデル）",
        description:
          "配当割引モデルの一種で、適正PBR = ROE / (株主資本コスト - 成長率) で算出。" +
          "本システムでは株主資本コスト = 8%（固定）を使用し、ROEと成長率から適正株価を逆算する。" +
          "成長率はユーザーが仮定するか、市場折込成長率（現在PBRから逆算）を参考にする。",
      },
      {
        term: "市場折込成長率",
        description:
          "現在のPBRから逆算した、市場が織り込んでいると推定される成長率。" +
          "計算式: g = (PBR × r - ROE) / (PBR - 1)  （r = 株主資本コスト 8%）。" +
          "この値が高いほど市場は「強気」で、低い or マイナスなら「弱気」と解釈できる。",
      },
    ],
  },
  {
    category: "FX関連",
    entries: [
      {
        term: "購買力平価（PPP: Purchasing Power Parity）",
        description:
          "同じ商品が世界中で同じ価格になるべき、という理論に基づく為替レートの均衡水準。" +
          "OECDが算出するPPPレートは、長期的な為替の「適正水準」の目安として使われる。" +
          "実際のレートがPPPより大幅に乖離している場合、長期的には回帰する傾向がある。",
      },
      {
        term: "金利差と為替レートの関係",
        description:
          "一般に高金利通貨は買われやすく、低金利通貨は売られやすい（金利裁定）。" +
          "日米10年国債利回り差が拡大すると、ドル買い・円売りが進みドル高円安になりやすい。" +
          "本システムではOLS回帰（USDJPY = β₀ + β₁ × 金利差）で適正レートを推定している。",
      },
      {
        term: "RSI（Relative Strength Index）",
        description:
          "相対力指数。過去14日間の値上がり幅と値下がり幅から算出する0〜100のオシレーター指標。" +
          "70以上は「買われすぎ」、30以下は「売られすぎ」のシグナル。" +
          "トレンドの転換点を見つけるのに使われるが、強いトレンド時は指標が張り付くことがある。",
      },
      {
        term: "ボリンジャーバンド",
        description:
          "移動平均線の上下に標準偏差の2倍の幅を持たせたバンド。" +
          "価格がバンド上限（+2σ）を超えると「割高」、下限（-2σ）を下回ると「割安」のサイン。" +
          "バンド幅が狭い（スクイーズ）時は、その後大きく動くことが多い。",
      },
    ],
  },
  {
    category: "評価用語",
    entries: [
      {
        term: "総合評価の5段階",
        description:
          "本システムでは複数のファクターをスコア化し、合計点で5段階評価する。\n\n" +
          "  超割安（スコア4以上）: 複数の指標が強い割安を示唆\n" +
          "  買い推奨（スコア2〜3）: 概ね割安で、購入を検討できる水準\n" +
          "  レンジ中（スコア-1〜1）: 特に割安でも割高でもない中立圏\n" +
          "  下落警戒（スコア-3〜-2）: 割高な指標が多く、注意が必要\n" +
          "  購入危険（スコア-4以下）: 複数の指標が強い割高を示唆",
      },
      {
        term: "株式の評価ファクター",
        description:
          "株式の総合評価は5つのファクターの合計で判定する。" +
          "1) 評価ゾーン: Gordon Modelに基づく割安/割高判定（-4〜+3）。" +
          "2) 成長率評価: 市場折込成長率の水準（-2〜+2）。" +
          "3) ROEトレンド: 3期連続の改善/悪化（-1〜+1）。" +
          "4) EPS成長: 3年CAGRまたは前年比（-1〜+1）。" +
          "5) 信売比率: 信用残高の偏り（-4〜0）。",
      },
      {
        term: "REIT/ETFの評価ファクター",
        description:
          "REITは4ファクター: P/NAV（-3〜+3）、分配金利回り（-2〜+2）、分配カバレッジ（-2〜+1）、52週価格位置（-1〜+1）。" +
          "ETFは4ファクター: 分配金利回り（-1〜+2）、52週価格位置（-2〜+2）、52週リターン（-1〜+1）、純資産残高（-1〜+1）。" +
          "REITではP/NAVが最重要、ETFでは52週価格位置が最重要ファクター。",
      },
    ],
  },
];

export default function WikiPage() {
  const [search, setSearch] = useState("");

  const filteredData = search
    ? wikiData
        .map((cat) => ({
          ...cat,
          entries: cat.entries.filter(
            (e) =>
              e.term.toLowerCase().includes(search.toLowerCase()) ||
              e.description.toLowerCase().includes(search.toLowerCase())
          ),
        }))
        .filter((cat) => cat.entries.length > 0)
    : wikiData;

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 1 }}>
        投資用語集
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        本システムで使用する投資用語・指標の説明
      </Typography>

      <TextField
        size="small"
        placeholder="用語を検索..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 3, width: 320 }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          },
        }}
      />

      {filteredData.map((cat) => (
        <Box key={cat.category} sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            {cat.category}
          </Typography>
          {cat.entries.map((entry) => (
            <Accordion key={entry.term} disableGutters>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography fontWeight="bold">{entry.term}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ whiteSpace: "pre-line", lineHeight: 1.8 }}
                >
                  {entry.description}
                </Typography>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      ))}

      {filteredData.length === 0 && (
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          「{search}」に一致する用語が見つかりませんでした。
        </Typography>
      )}
    </Box>
  );
}
