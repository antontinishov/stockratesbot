import logging

from sentry_sdk import capture_exception

from config.settings import DEBUG

logger = logging.getLogger(__name__)


def send_logging(exception):
	if not DEBUG:
		capture_exception(exception)
	else:
		logger.exception(exception)
	return True
