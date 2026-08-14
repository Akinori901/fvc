"""プロンプト構築サービス。銘柄コンテキストと質問タイプからプロンプトを生成する。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.ai.application.dto import StockContextDTO

_SYSTEM_PROMPT = """あなたは株式投資の専門アナリストです。
提供された銘柄データを基に、投資家が意思決定に役立てられる、具体的かつ客観的な分析を日本語で提供してください。

制約:
- 断定的な買い推奨・売り推奨は行わない
- データに基づいた分析を行う
- 不明な点は「データが不足しているため判断が難しい」と明示する
- 回答は3000文字以内に収めること。各提案は1〜2文で簡潔に説明し、詳細な計算過程は省くこと
- 提案は最大5つまでに絞り、優先度順に番号付きで列挙すること
- 最後に「まとめ」セクションを設け、必ず文章を完結させること
- 見出し（###）や箇条書きを使い読みやすく構成する"""

# 専門家ロール: system_prompt の冒頭に挿入されるプレフィックス文。
# キーは VALID_EXPERT_ROLES と同期して管理する。
_ROLE_PROMPTS: dict[str, str] = {
    "general": "",
    "quant": (
        "あなたは定量分析（統計・ファクター・ボラティリティ）に強い一流のクオンツアナリストです。"
        "提供データのうち、ヒストリカル・ボラティリティ、移動平均乖離、RSI/MACD、モメンタム、"
        "バリュエーション（PBR/乖離率/市場織込成長率）、成長率、配当利回りを定量的に評価してください。\n"
        "※ 個別銘柄のベータ・シャープレシオ・ファクターエクスポージャー・相関は本システムでは"
        "算出しておらず提供されません。これらは推測せず、提供された指標の範囲で分析してください。\n\n"
    ),
    "fundamental": (
        "あなたは財務諸表分析・業績予想に基づくバリュー投資の一流ファンダメンタルアナリストです。"
        "提供データのうち、ROE・自己資本比率・営業利益率・売上高/EPS/営業利益の成長率・"
        "営業キャッシュフロー/FCF・配当・オーナー経営・バリュエーションを重視して本質的価値を評価してください。\n"
        "※ 純利益の絶対額・投資CF/財務CF・有利子負債の内訳は提供されません。推測しないでください。\n\n"
    ),
    "macro": (
        "あなたはマクロ経済（金利・為替・景気循環）の専門アナリストです。"
        "提供される市場環境（USD/JPY・日米10年金利・金利差）と業種を踏まえ、"
        "個別銘柄を金利感応度・為替感応度・業種特性の観点で位置づけてください。\n"
        "※ 政策金利・CPI・GDP等の一般マクロ指標、セクター相対パフォーマンス、"
        "個別銘柄の金利/為替感応度の実測値は提供されません。業種と提供環境データからの定性的推論に留めてください。\n\n"
    ),
    "technical": (
        "あなたはチャートパターン・移動平均・出来高分析に基づくテクニカルアナリストです。"
        "提供される移動平均乖離（25/75/200日）・RSI・MACD・ボリンジャーバンド・ATR・"
        "モメンタム・52週位置・信用需給・流動性を用いて、トレンド・過熱感・需給を分析してください。\n"
        "※ 株価は日足終値のみ保持しており、始値・高値・安値（4本値）は提供されません。"
        "そのためギャップや日中レンジ、真のATRは扱えません。終値ベースの近似として解釈してください。\n\n"
    ),
    "risk_mgmt": (
        "あなたは下方リスク評価・ドローダウン管理に特化したリスクマネジメント専門家です。"
        "提供されるヒストリカル・ボラティリティ・ATR・信用残（信売比率/買残トレンド）・流動性・"
        "自己資本比率・配当の安定性・バリュエーション過熱度から、下振れシナリオとリスク要因を評価してください。\n"
        "※ VaR・最大ドローダウン・ベータ・シャープレシオは本システムでは算出しておらず提供されません。"
        "提供されたボラティリティ等から定性的にリスクを論じ、これらの統計量は推測しないでください。\n\n"
    ),
}

# スクリーニング指標のコード値 → 日本語ラベル（画面表示と揃える）
_ROE_TREND_LABELS: dict[str, str] = {
    "improving": "改善",
    "declining": "悪化",
    "stable": "横ばい",
}
_MOMENTUM_LABELS: dict[str, str] = {
    "strong_buy": "強い買い",
    "buy": "買い",
    "neutral": "中立",
    "caution": "注意",
    "sell": "売り",
}
_BALANCE_TREND_LABELS: dict[str, str] = {
    "increasing": "増加",
    "decreasing": "減少",
    "flat": "横ばい",
}
_LIQUIDITY_LABELS: dict[str, str] = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "very_low": "極低",
}
_RSI_SIGNAL_LABELS: dict[str, str] = {
    "overbought": "買われ過ぎ",
    "oversold": "売られ過ぎ",
    "neutral": "中立",
}
_MACD_CROSS_LABELS: dict[str, str] = {
    "golden": "ゴールデンクロス",
    "dead": "デッドクロス",
    "none": "なし",
}
_BB_SIGNAL_LABELS: dict[str, str] = {
    "above_upper": "上限バンド超え",
    "below_lower": "下限バンド割れ",
    "inside": "バンド内",
}

_QUESTION_TEMPLATES: dict[str, str] = {
    "pbr_low": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄のPBRが低い（現在 {pbr}倍）主な理由として考えられる要因を分析してください。
業種特性、収益性（ROE: {roe}）、成長性の観点から考察してください。""",
    "investment_risk": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄への投資における主なリスク要因を分析してください。
財務面のリスク、事業リスク、市場リスクの観点から整理してください。""",
    "growth_outlook": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄の今後の成長見通しを分析してください。
売上高・営業利益のトレンド、ROEの推移、業種動向を踏まえて考察してください。""",
    "custom": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
{custom_question}

上記の質問に対して、提供されたデータと専門知識を活用し、具体的かつ十分に詳しく回答してください。""",
    "price_forecast": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄の3ヶ月後の株価レンジを予想してください。
現在のファンダメンタルズ（PBR: {pbr}倍、ROE: {roe}）、適正株価との乖離、
業種のマクロ環境を踏まえ、強気・中立・弱気の3シナリオで考察してください。
※ 投資助言ではなく、分析に基づく参考値としてお示しください。""",
    "price_drop_reason": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄の株価が直近で下落している（または低迷している）可能性のある原因を分析してください。
業績面の要因、市場環境・セクター動向、需給要因の3つの観点から考察してください。""",
    "dividend_analysis": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄の配当に関する分析を行ってください。
現在の配当利回り、配当性向（EPS: {eps} ベース）、今後の増配余力、
インカム投資としての魅力度を総合的に評価してください。""",
    "sector_comparison": """以下の銘柄データを参照してください。

【銘柄情報】
{context}

【質問】
この銘柄の「{sector}」セクター内での相対的な位置づけを分析してください。
バリュエーション（PBR: {pbr}倍）、収益性（ROE: {roe}）、成長性の観点から、
セクター内で優位性がある点・劣位にある点を整理してください。""",
}


class PromptBuilderService:
    """質問タイプに応じたプロンプトを組み立てる。"""

    def build_system_prompt(self, expert_role: str = "general") -> str:
        role_prefix = _ROLE_PROMPTS.get(expert_role, "")
        return role_prefix + _SYSTEM_PROMPT

    def build_user_prompt(
        self,
        context: StockContextDTO,
        question_type: str,
        custom_question: str = "",
    ) -> str:
        template = _QUESTION_TEMPLATES.get(question_type)
        if template is None:
            raise ValueError(f"未知の質問タイプ: {question_type}")

        context_text = self._format_context(context)

        sym = "$" if context.market_type == "US" else "¥"
        return template.format(
            context=context_text,
            pbr=f"{context.pbr:.2f}" if context.pbr else "不明",
            roe=f"{float(context.roe) * 100:.1f}%" if context.roe else "不明",
            eps=f"{sym}{context.eps:,.2f}" if context.eps else "不明",
            sector=context.sector,
            custom_question=custom_question,
        )

    def _format_context(self, ctx: StockContextDTO) -> str:
        is_us = ctx.market_type == "US"
        sym = "$" if is_us else "¥"
        unit = "百万ドル" if is_us else "百万円"

        def _fmt_price(v: object) -> str:
            """株価・BPS など。日本株は整数、米株はドル建て小数2桁。"""
            if v is None:
                return "不明"
            return f"{sym}{v:,.2f}" if is_us else f"{sym}{v:,.0f}"

        def _fmt_eps(v: object) -> str:
            """EPS は小数2桁（$0.31 や ¥85.25 のような小額を切り捨てない）。"""
            return f"{sym}{v:,.2f}" if v is not None else "不明"

        def _fmt_pct(v: object) -> str:
            """比率（0.05 = 5%）を % 表記に。"""
            return f"{float(v) * 100:.1f}%" if v is not None else "不明"  # type: ignore[arg-type]

        def _fmt_mn(v: object) -> str:
            return f"{v:,}{unit}" if v is not None else "不明"

        def _fmt_ratio_pct(v: object) -> str:
            """既に % スケール（12.29 = 12.29%）の値をそのまま % 表記に。"""
            return f"{float(v):.2f}%" if v is not None else "不明"  # type: ignore[arg-type]

        # --- 基本（常に出力） ---
        lines = [
            "■ 基本情報・バリュエーション",
            f"証券コード: {ctx.code}",
            f"銘柄名: {ctx.name}",
            f"業種: {ctx.sector}",
            f"最新株価: {_fmt_price(ctx.latest_price)}",
            f"BPS（1株純資産）: {_fmt_price(ctx.bps)}",
            f"EPS（1株利益）: {_fmt_eps(ctx.eps)}",
            f"ROE: {_fmt_pct(ctx.roe)}",
            f"売上高: {_fmt_mn(ctx.revenue)}",
            f"営業利益: {_fmt_mn(ctx.operating_income)}",
            f"PBR: {f'{ctx.pbr:.2f}倍' if ctx.pbr else '不明'}",
            f"適正株価（Gordon Growth Model, 成長率2%想定）: {_fmt_price(ctx.fair_value)}",
            f"適正株価との乖離率: {_fmt_pct(ctx.discount_rate)}",
        ]

        # --- 成長性（欠損行はスキップ） ---
        growth: list[str] = []
        if ctx.implied_growth_rate is not None:
            growth.append(f"市場が織り込む成長率（株価が示唆する期待成長率）: {_fmt_pct(ctx.implied_growth_rate)}")
        if ctx.company_forecast_growth_rate is not None:
            growth.append(f"会社予想ベース成長率: {_fmt_pct(ctx.company_forecast_growth_rate)}")
        if ctx.growth_rate_label:
            growth.append(f"成長率評価: {ctx.growth_rate_label}")
        if ctx.eps_growth_yoy is not None:
            growth.append(f"EPS成長率（前年比）: {_fmt_pct(ctx.eps_growth_yoy)}")
        if ctx.eps_cagr_3y is not None:
            growth.append(f"EPS CAGR（3年）: {_fmt_pct(ctx.eps_cagr_3y)}")
        if ctx.revenue_growth_yoy is not None:
            growth.append(f"売上高成長率（前年比）: {_fmt_pct(ctx.revenue_growth_yoy)}")
        if ctx.roe_trend:
            growth.append(f"ROEトレンド: {_ROE_TREND_LABELS.get(ctx.roe_trend, ctx.roe_trend)}")
        if growth:
            lines += ["", "■ 成長性", *growth]

        # --- テクニカル・需給 ---
        tech: list[str] = []
        if ctx.momentum_signal:
            tech.append(f"モメンタム（需給シグナル）: {_MOMENTUM_LABELS.get(ctx.momentum_signal, ctx.momentum_signal)}")
        if ctx.price_position_52w is not None:
            # 0.0〜1.0 の割合。0%=52週安値, 100%=52週高値
            tech.append(f"52週レンジ内の位置: {_fmt_pct(ctx.price_position_52w)}（0%=安値, 100%=高値）")
        if ctx.distance_from_52w_high is not None:
            tech.append(f"52週高値からの距離: {_fmt_pct(ctx.distance_from_52w_high)}")
        if ctx.sl_ratio is not None:
            tech.append(f"信用倍率（信売比率）: {float(ctx.sl_ratio):.2f}倍")
        if ctx.long_balance_trend:
            trend_label = _BALANCE_TREND_LABELS.get(ctx.long_balance_trend, ctx.long_balance_trend)
            tech.append(f"信用買残トレンド: {trend_label}")
        if ctx.liquidity_level:
            tech.append(f"流動性: {_LIQUIDITY_LABELS.get(ctx.liquidity_level, ctx.liquidity_level)}")
        # 移動平均乖離（build_indicators。既に % スケール）
        if ctx.ma_25_deviation_pct is not None:
            tech.append(f"25日移動平均乖離: {_fmt_ratio_pct(ctx.ma_25_deviation_pct)}")
        if ctx.ma_75_deviation_pct is not None:
            tech.append(f"75日移動平均乖離: {_fmt_ratio_pct(ctx.ma_75_deviation_pct)}")
        if ctx.ma_200_deviation_pct is not None:
            tech.append(f"200日移動平均乖離: {_fmt_ratio_pct(ctx.ma_200_deviation_pct)}")
        if ctx.rsi_14 is not None:
            rsi_sig = f"（{_RSI_SIGNAL_LABELS.get(ctx.rsi_signal, '')}）" if ctx.rsi_signal else ""
            tech.append(f"RSI(14): {float(ctx.rsi_14):.1f}{rsi_sig}")
        if ctx.macd_hist is not None:
            macd_c = f"（{_MACD_CROSS_LABELS.get(ctx.macd_cross, '')}）" if ctx.macd_cross else ""
            tech.append(f"MACDヒストグラム: {float(ctx.macd_hist):.2f}{macd_c}")
        if ctx.bb_signal:
            bb_pos = f"（%B={float(ctx.bb_position):.2f}）" if ctx.bb_position is not None else ""
            tech.append(f"ボリンジャーバンド: {_BB_SIGNAL_LABELS.get(ctx.bb_signal, ctx.bb_signal)}{bb_pos}")
        if ctx.atr_pct is not None:
            tech.append(f"ATR(14)株価比: {_fmt_ratio_pct(ctx.atr_pct)}（4本値未保持のため終値ベース近似）")
        if ctx.volatility_20d is not None:
            tech.append(f"ヒストリカル・ボラティリティ(20日): {_fmt_ratio_pct(ctx.volatility_20d)}")
        if tech:
            lines += ["", "■ テクニカル・需給", *tech]

        # --- 配当 ---
        div: list[str] = []
        if ctx.dividend_yield is not None:
            div.append(f"配当利回り: {_fmt_ratio_pct(ctx.dividend_yield)}")
        if ctx.payout_ratio is not None:
            div.append(f"配当性向: {_fmt_ratio_pct(ctx.payout_ratio)}")
        if ctx.consecutive_dividend_years is not None:
            div.append(f"連続配当年数: {ctx.consecutive_dividend_years}年")
        if ctx.progressive_dividend_years is not None:
            div.append(f"累進配当年数: {ctx.progressive_dividend_years}年")
        if div:
            lines += ["", "■ 配当", *div]

        # --- FCF ---
        fcf: list[str] = []
        if ctx.fcf_yield is not None:
            fcf.append(f"FCF利回り: {_fmt_ratio_pct(ctx.fcf_yield)}")
        if ctx.fcf_margin is not None:
            fcf.append(f"FCFマージン: {_fmt_ratio_pct(ctx.fcf_margin)}")
        if fcf:
            lines += ["", "■ キャッシュフロー", *fcf]

        # --- 財務健全性 ---
        health: list[str] = []
        if ctx.per is not None:
            health.append(f"PER: {float(ctx.per):.2f}倍")
        if ctx.market_cap is not None:
            health.append(f"時価総額: {_fmt_mn(ctx.market_cap)}")
        if ctx.equity_ratio is not None:
            health.append(f"自己資本比率: {_fmt_ratio_pct(ctx.equity_ratio)}")
        if ctx.operating_margin is not None:
            health.append(f"営業利益率: {_fmt_ratio_pct(ctx.operating_margin)}")
        if ctx.operating_cash_flow is not None:
            health.append(f"営業キャッシュフロー: {_fmt_mn(ctx.operating_cash_flow)}")
        if ctx.free_cash_flow is not None:
            health.append(f"フリーキャッシュフロー: {_fmt_mn(ctx.free_cash_flow)}")
        if health:
            lines += ["", "■ 財務健全性", *health]

        # --- オーナー経営 ---
        if ctx.is_owner_managed:
            owner = "オーナー経営: 該当（代表者が主要株主）"
            if ctx.owner_ratio is not None:
                owner += f" / 代表者関連の持株比率: {_fmt_ratio_pct(ctx.owner_ratio)}"
            lines += ["", "■ ガバナンス", owner]

        # --- 市場環境（マクロ） ---
        macro: list[str] = []
        if ctx.usdjpy is not None:
            macro.append(f"USD/JPY: {float(ctx.usdjpy):.2f}")
        if ctx.us_10y is not None:
            macro.append(f"米国10年債利回り: {float(ctx.us_10y):.2f}%")
        if ctx.jp_10y is not None:
            macro.append(f"日本10年債利回り: {float(ctx.jp_10y):.2f}%")
        if ctx.us_10y is not None and ctx.jp_10y is not None:
            macro.append(f"日米10年金利差: {float(ctx.us_10y - ctx.jp_10y):.2f}%")
        if macro:
            market_label = "米国市場" if ctx.market_type == "US" else "日本市場"
            lines += ["", f"■ 市場環境（{market_label}上場, 分析時点）", *macro]

        return "\n".join(lines)
