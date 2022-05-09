import time
import itertools

from .. import Service, command

class HealthService(Service):
    """Provides basic connectivity commands"""
    _name_ = 'health'

    @command()
    def ping(self, count=1, interval=1.0):
        it = range(count-1) if count > 0 else itertools.count()
        for _ in it:
            yield
            time.sleep(interval)
