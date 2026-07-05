"""仮想売買ドメイン例外。"""


class InsufficientPositionError(Exception):
    """保有数が売却数量を下回る"""


class InvalidTradeQuantityError(Exception):
    """数量が100の倍数でない"""


class StockPriceUnavailableError(Exception):
    """最新株価がNULL"""
