import logging.config
from pathlib import Path

import yaml

from app.core.config import settings


def configure_logging() -> None:
    config_path = Path("logging.yaml")
    if not config_path.exists():
        logging.basicConfig(level=settings.log_level)
        return

    with config_path.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    formatter_name = "json" if settings.log_json else "text"
    config["handlers"]["console"]["formatter"] = formatter_name
    config["handlers"]["console"]["level"] = settings.log_level
    config["root"]["level"] = settings.log_level

    logging.config.dictConfig(config)
