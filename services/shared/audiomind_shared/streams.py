"""Single source of truth for Redis Streams topology constants.

Both api-gateway (producer) and worker (consumer) import from here to
guarantee they always agree on stream names, preventing silent job loss.
"""

#: Redis Stream key where job messages are published.
STREAM_KEY: str = "audiomind:jobs"

#: Consumer group name for the worker fleet.
CONSUMER_GROUP: str = "audiomind:workers"

#: Prefix for per-job Redis hash keys  (full key: ``f"{JOB_KEY_PREFIX}:{job_id}"``).
JOB_KEY_PREFIX: str = "audiomind:job"
