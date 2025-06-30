import logging


def create_logger() -> logging.Logger:
    logger = logging.getLogger("albert")
    logging.basicConfig(
        format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # TODO: Add controllable log level for users (e.g., via env var)

    return logger


logger = create_logger()
