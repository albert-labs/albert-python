import logging
import os


def create_logger() -> logging.Logger:
    logger = logging.getLogger("albert")

    if not logger.handlers:
        level_str = os.getenv("ALBERT_LOG_LEVEL", "WARNING").upper()

        if level_str not in logging._nameToLevel:
            print(
                f"[albert] Invalid ALBERT_LOG_LEVEL: '{level_str}'. "
                "Falling back to WARNING. Valid options: DEBUG, INFO, WARNING, ERROR, CRITICAL."
            )
            level_str = "WARNING"

        log_level = logging._nameToLevel[level_str]

        logging.basicConfig(
            level=log_level,
            format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logger.setLevel(log_level)

    return logger


logger = create_logger()
