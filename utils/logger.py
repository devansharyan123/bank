"""
logger.py — Shared logger for the entire application.

Usage in any file:
    from utils.logger import logger
    logger.info("User registered: john@example.com")
    logger.warning("Fraud detected on account ACC1001")
    logger.error("Database connection failed")
"""

import logging

# Configure once — all modules share this same logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("banking_app")
