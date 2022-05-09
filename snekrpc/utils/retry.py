import time

from .. import logs
from .format import format_exc

RETRY_COUNT = 0
RETRY_INTERVAL = 1.0
RETRY_ERRORS = (Exception,)
RETRY_LOG_TEMPLATE = '{error} (retrying: {retries})'

log = logs.get(__name__)

class Retry(object):
    def __init__(self, count=None, interval=None, errors=None, logger=None,
            log_template=None):
        self.count = RETRY_COUNT if count is None else count
        self.interval = RETRY_INTERVAL if interval is None else interval
        self.errors = tuple(errors or RETRY_ERRORS)

        logger = logger or log
        self.log = (logger.exception
            if logger.isEnabledFor(logs.DEBUG) else log.warning)
        self.log_template = log_template or RETRY_LOG_TEMPLATE

    def call(self, func, *args, **kwargs):
        retries = 0
        count = self.count
        interval = self.interval
        errors = self.errors

        while True:
            try:
                return func(*args, **kwargs)
            except errors as e:
                if retries >= count >= 0:
                    raise

                time.sleep(interval)
                retries += 1

                self._log(retries, e)

    def call_gen(self, func, *args, **kwargs):
        retries = 0
        count = self.count
        interval = self.interval
        errors = self.errors

        while True:
            try:
                for x in func(*args, **kwargs):
                    yield x
                return
            except errors as e:
                if retries >= count >= 0:
                    raise

                time.sleep(interval)
                retries += 1

                self._log(retries, e)

    def _log(self, retries, exc):
        self.log(self.log_template.format(
            error=format_exc(exc),
            retries=retries,
            count=self.count,
            interval=self.interval,
            ))
