import time

import redis


class RateLimiter:
    """
    A simple rate limiter using Redis to limit requests per minute and per day for a user.
    """

    def __init__(self, redis_host: str, redis_port: int, per_minute: int, per_day: int):
        self.r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.per_minute = per_minute
        self.per_day = per_day

    def check(
        self,
        user_id: str,
    ) -> bool:
        """
        Checks if the user has exceeded the rate limits. Increments counters.
        Returns True if within limits, False otherwise.
        """

        now = time.time()
        minute_key = f"rate:{user_id}:minute:{int(now // 60)}"
        day_key = f"rate:{user_id}:day:{time.strftime('%Y-%m-%d', time.gmtime(now))}"

        m = self.r.incr(minute_key)
        if m == 1:
            self.r.expire(minute_key, 60)

        d = self.r.incr(day_key)
        if d == 1:
            self.r.expire(day_key, 86400)

        return m <= self.per_minute and d <= self.per_day

    def check_health(self) -> bool:
        try:
            return self.r.ping()
        except redis.RedisError as e:
            print(f"Redis health check failed: {e}")
            return False
