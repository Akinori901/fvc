"""仮想売買ドメイン値オブジェクト。"""

from enum import StrEnum


class TradeType(StrEnum):
    BUY = "buy"
    SELL = "sell"
