"""
スケジューラー設定

定期的なタスクを管理する
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.match_scraper import run_scraper

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# グローバルスケジューラーインスタンス
scheduler: BackgroundScheduler | None = None


def start_scheduler():
    """スケジューラーを開始

    1日1回、午前3時に試合情報をスクレイピングしてDBを更新する
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler is already running")
        return

    scheduler = BackgroundScheduler()

    # 毎日午前3時に実行
    scheduler.add_job(
        run_scraper,
        trigger=CronTrigger(hour=3, minute=0),
        id="match_scraper",
        name="試合情報スクレイピング",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started. Match scraper will run daily at 3:00 AM")


def shutdown_scheduler():
    """スケジューラーを停止"""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shutdown")


def run_scraper_now():
    """スクレイパーを今すぐ実行（手動実行用）"""
    logger.info("Running match scraper manually...")
    run_scraper()
