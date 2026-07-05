export interface PaperPosition {
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_cost_price: string;
  total_cost: string;
  latest_price: string | null;
  unrealized_profit: string | null;
  unrealized_profit_pct: string | null;
  realized_profit_total: string;
}

export interface PaperPositionList {
  positions: PaperPosition[];
  summary: {
    total_investment: string;
    total_unrealized_profit: string;
    total_realized_profit: string;
    position_count: number;
  };
}

export interface PaperTrade {
  id: number;
  stock_code: string;
  stock_name: string;
  trade_type: "buy" | "sell";
  quantity: number;
  price: string;
  total_amount: string;
  realized_profit: string | null;
  memo: string;
  traded_at: string;
}

export interface ExecuteTradeRequest {
  stock_code: string;
  trade_type: "buy" | "sell";
  quantity: number;
  memo?: string;
}

export interface TradeResult {
  trade_id: number;
  trade_type: string;
  stock_code: string;
  stock_name: string;
  quantity: number;
  price: string;
  total_amount: string;
  realized_profit: string | null;
  avg_cost_price: string;
  position_quantity: number;
  position_total_cost: string;
}

export interface ResetResult {
  deleted_trades: number;
  deleted_positions: number;
}
