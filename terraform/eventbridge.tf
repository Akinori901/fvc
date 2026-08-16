# =============================================================================
# EventBridge Scheduler — 定期同期スケジュール
#
# J-Quants Standard プランの制約:
#   - 株価: 当日データは翌営業日 19:00 頃に公開 → 20:00 に取得
#   - 信用残高: 週次公表（週末残高）→ 週1回で十分
#   - 財務: 決算発表後に更新 → 平日1回
# =============================================================================

# -----------------------------------------------------------------------------
# スケジュールグループ（同期関連スケジュールをまとめて管理）
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule_group" "sync" {
  name = "${var.project_name}-sync"

  tags = { Name = "${var.project_name}-sync-schedule-group" }
}

# -----------------------------------------------------------------------------
# Scheduler 用 IAM ロール（Worker Lambda の invoke 権限のみ）
# -----------------------------------------------------------------------------

resource "aws_iam_role" "scheduler_execution" {
  name = "${var.project_name}-scheduler-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
      }
    ]
  })

  tags = { Name = "${var.project_name}-scheduler-role" }
}

resource "aws_iam_role_policy" "scheduler_invoke_lambda" {
  name = "${var.project_name}-scheduler-invoke-worker"
  role = aws_iam_role.scheduler_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.worker.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# 株価同期 — メイン（17:30 JST, 月〜金）
# J-Quants は引け後 16:30 頃に当日終値データを配信するため、
# 30分のバッファを取って 17:30 に同期し、引け 2 時間以内にダッシュボードへ反映
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_prices_evening" {
  name       = "${var.project_name}-sync-prices-evening"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(30 17 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_prices"
      args    = ["--market", "JP"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 株価同期 — 翌朝キャッチアップ（8:00 JST, 月〜金）
# 前日 20:00 の同期が失敗した場合のセーフティネット。
# --days 3 で直近3営業日分をカバーし、欠損データを補完
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_prices_morning" {
  name       = "${var.project_name}-sync-prices-morning"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 8 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_prices"
      args    = ["--market", "JP", "--days", "3"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 財務データ同期（17:00 JST, 月〜金）
# 決算発表は引け後のため、1日1回17時に取得
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_financials_daily" {
  name       = "${var.project_name}-sync-financials-daily"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 17 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_financials"
      args    = ["--market", "JP"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 信用残高同期 — 週次（土曜 18:00 JST）
# J-Quants の信用残高は週次公表（週末残高）のため、週1回で十分。
# --days 7 で直近1週間分を取得し、レート制限(429)を回避
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_margin_weekly" {
  name       = "${var.project_name}-sync-margin-weekly"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 18 ? * SAT *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_margin"
      args    = ["--market", "JP", "--days", "7"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 配当データ同期 — 週次（日曜 4:30 JST）
# 配当は低頻度更新のため週1回で十分
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_dividends_weekly" {
  name       = "${var.project_name}-sync-dividends-weekly"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(30 4 ? * SUN *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 30
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_dividends"
      args    = ["--market", "JP"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 国内株（普通株）配当同期 — 週次（日曜 5:30 JST）
# ETF/REIT 用と分離。yfinance 経由で各銘柄の配当履歴を取得。
# おすすめ機能（長期保有判定）で連続配当年数・配当利回りを使用するため必須。
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_dividends_jp_stock_weekly" {
  name       = "${var.project_name}-sync-dividends-jp-stock-weekly"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(30 5 ? * SUN *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 60
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_dividends"
      args    = ["--market", "JP", "--instrument-type", "stock"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# FXデータ同期 — 日次（7:00 JST, 月〜金）
# FRED + yfinance から為替レート・金利データを取得
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_fx_data_daily" {
  name       = "${var.project_name}-sync-fx-data-daily"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 7 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_fx_data"
      args    = []
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# FXデータ全量再同期 — 週次（日曜 3:00 JST）
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_fx_data_full_weekly" {
  name       = "${var.project_name}-sync-fx-data-full-weekly"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 3 ? * SUN *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 30
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_fx_data"
      args    = ["--full"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# =============================================================================
# 米国株 定期同期（yfinance ベース）
# =============================================================================

# -----------------------------------------------------------------------------
# 米国株価同期（火〜土 7:00 JST）
# NY 市場引け（夏時間 5:00 JST、冬時間 6:00 JST）後にデータ取得
# 月曜は前週金曜のデータを既に火曜朝に取得済みなので不要
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_prices_us_daily" {
  name       = "${var.project_name}-sync-prices-us-daily"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 7 ? * TUE-SAT *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_prices"
      args    = ["--market", "US"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 米国株 財務データ同期（平日 18:00 JST）
# yfinance は決算公開後に更新されるため、JP 17:00 と 1 時間ずらして 18:00
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_financials_us_daily" {
  name       = "${var.project_name}-sync-financials-us-daily"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 18 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_financials"
      args    = ["--market", "US"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 米国株 配当同期 — 週次（日曜 5:00 JST）
# 配当は低頻度更新で週1回。JP 4:30 と時間をずらして 5:00
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_dividends_us_weekly" {
  name       = "${var.project_name}-sync-dividends-us-weekly"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 5 ? * SUN *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 30
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_dividends"
      args    = ["--market", "US"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 個別銘柄ニュース取り込み — 引け後 (17:30 JST, 月〜金)
# Google News RSS で全 JP アクティブ銘柄のニュースを取得（Phase 1）
# 株価同期と同時刻スタートで、株価更新と同じタイミングで反映される
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "sync_news_stocks_evening" {
  name       = "${var.project_name}-sync-news-stocks-evening"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(30 17 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 30
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "sync_news"
      args    = ["--category", "stock"]
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# 日次急騰急落集計 — 引け後 (18:00 JST, 月〜金)
# 株価同期 (17:30 JST) 完了後 30 分のバッファを取って
# t_daily_movers に当日の前日比・出来高比・UL/LL を再生成する
# MCP ツール get_price_movers が読み取り対象とする
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "compute_movers_evening" {
  name       = "${var.project_name}-compute-movers-evening"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 18 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "compute_movers"
      args    = []
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# =============================================================================
# おすすめスナップショット生成（平日 9:00 JST）
#
# 朝の株価補完同期(8:00)の完了後に実行することで、最新の株価ベースで
# 推奨銘柄を再計算する。重い処理(約40秒)のため API Gateway 経由ではなく、
# Worker Lambda で直接実行→DBに保存するスナップショット方式を採る。
# =============================================================================

resource "aws_scheduler_schedule" "generate_recommendations_daily" {
  name       = "${var.project_name}-generate-recommendations-daily"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(0 9 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 30
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "generate_recommendations"
      args    = []
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

# -----------------------------------------------------------------------------
# スクリーニング一覧スナップショット生成（平日 8:45 / 17:45 JST）
# 朝の株価同期(8:00)後と、夕方の財務同期(17:00)後に、全銘柄の growth_rate 非依存な
# 計算結果を t_screening_snapshots に事前計算・保存する。銘柄一覧APIはこれを SELECT
# するだけで即応答できる（リクエスト毎の全件フル計算を回避）。
# -----------------------------------------------------------------------------

resource "aws_scheduler_schedule" "generate_screening_morning" {
  name       = "${var.project_name}-generate-screening-morning"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(45 8 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "generate_screening_snapshot"
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}

resource "aws_scheduler_schedule" "generate_screening_evening" {
  name       = "${var.project_name}-generate-screening-evening"
  group_name = aws_scheduler_schedule_group.sync.name

  schedule_expression          = "cron(45 17 ? * MON-FRI *)"
  schedule_expression_timezone = "Asia/Tokyo"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler_execution.arn

    input = jsonencode({
      command = "generate_screening_snapshot"
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  state = "ENABLED"
}
