import logging
from logging import config as logging_config

from trackyai.config import settings

logger = logging.getLogger(__name__)

_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'general': {'format': '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', 'datefmt': '%Y-%m-%dT%H:%M:%S%z'}
    },
    'handlers': {
        'file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'general',
            'level': 'NOTSET',
            'filename': f'{settings.log_dir}/trackyai.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'mode': 'a',
            'encoding': 'utf-8',
        }
    },
    'root': {'handlers': ['file_handler'], 'level': settings.log_level},
    'loggers': {'httpx': {'level': 'WARNING'}, 'httpcore': {'level': 'WARNING'}},
}


def setup_logging() -> None:
    logging_config.dictConfig(_LOGGING_CONFIG)
    logging.captureWarnings(True)
    logger.info('Logging has been initialized')
