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
        "データの定量的な観点を重視し、ファクターエクスポージャー、リスクプレミアム、回帰分析の視点を活用してください。\n\n"
    ),
    "fundamental": (
        "あなたは財務諸表分析・業績予想に基づくバリュー投資の一流ファンダメンタルアナリストです。"
        "キャッシュフロー、収益性、競争優位、経営の質といった本質的価値の観点で分析してください。\n\n"
    ),
    "macro": (
        "あなたはマクロ経済（金利・為替・景気循環・セクターローテーション）の専門アナリストです。"
        "個別銘柄を経済環境やセクターサイクルの中に位置づけて評価してください。\n\n"
    ),
    "technical": (
        "あなたはチャートパターン・移動平均・出来高分析に基づくテクニカルアナリストです。"
        "価格モメンタム、サポート／レジスタンス、需給バランスの観点で分析してください。\n\n"
    ),
    "risk_mgmt": (
        "あなたは下方リスク評価・ドローダウン管理に特化したリスクマネジメント専門家です。"
        "想定される下振れシナリオ、最大損失、リスク・リターン比の観点を最優先してください。\n\n"
    ),
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

        return template.format(
            context=context_text,
            pbr=f"{context.pbr:.2f}" if context.pbr else "不明",
            roe=f"{float(context.roe) * 100:.1f}%" if context.roe else "不明",
            eps=f"¥{context.eps:,.0f}" if context.eps else "不明",
            sector=context.sector,
            custom_question=custom_question,
        )

    def _format_context(self, ctx: StockContextDTO) -> str:
        def _fmt_price(v: object) -> str:
            return f"¥{v:,.0f}" if v is not None else "不明"

        def _fmt_pct(v: object) -> str:
            return f"{float(v) * 100:.1f}%" if v is not None else "不明"  # type: ignore[arg-type]

        def _fmt_mn(v: object) -> str:
            return f"{v:,}百万円" if v is not None else "不明"

        lines = [
            f"証券コード: {ctx.code}",
            f"銘柄名: {ctx.name}",
            f"業種: {ctx.sector}",
            f"最新株価: {_fmt_price(ctx.latest_price)}",
            f"BPS（1株純資産）: {_fmt_price(ctx.bps)}",
            f"EPS（1株利益）: {_fmt_price(ctx.eps)}",
            f"ROE: {_fmt_pct(ctx.roe)}",
            f"売上高: {_fmt_mn(ctx.revenue)}",
            f"営業利益: {_fmt_mn(ctx.operating_income)}",
            f"PBR: {f'{ctx.pbr:.2f}倍' if ctx.pbr else '不明'}",
            f"適正株価（Gordon Growth Model）: {_fmt_price(ctx.fair_value)}",
            f"現在株価との乖離率: {_fmt_pct(ctx.discount_rate)}",
        ]
        return "\n".join(lines)
