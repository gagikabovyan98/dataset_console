#app/config.py

import os
from dotenv import load_dotenv

load_dotenv(override=False)

def _get(name: str, default=None):
    v = os.getenv(name)
    return v if (v is not None and v != "") else default

def _bool(name: str, default=False) -> bool:
    v = _get(name, None)
    if v is None:
        return default
    return str(v).lower() in ("1","true","yes","on")

class Settings:
    # Exec limits
    TIMEOUT_SECONDS  = int(_get("TIMEOUT_SECONDS","12"))
    STARTUP_OVERHEAD_SEC = int(_get("STARTUP_OVERHEAD_SEC", "20"))

    MAX_SCRIPT_BYTES = int(_get("MAX_SCRIPT_BYTES","64000"))
    STDOUT_MAX       = int(_get("STDOUT_MAX","200000"))
    STDERR_MAX       = int(_get("STDERR_MAX","200000"))
    MAX_DATASETS     = int(_get("MAX_DATASETS","10"))

    # Child resource limits
    RLIMIT_CPU_SECS  = int(_get("RLIMIT_CPU_SECS","5"))
    RLIMIT_AS_BYTES  = int(_get("RLIMIT_AS_BYTES", str(512*1024*1024)))  # 512MB
    RLIMIT_FSIZE     = int(_get("RLIMIT_FSIZE", str(10*1024*1024)))      # 10MB
    RLIMIT_NPROC     = int(_get("RLIMIT_NPROC","64"))

    # Auth
    DISABLE_AUTH     = _bool("DISABLE_AUTH", False)

    # ClickHouse (RO creds)
    CH_HOST     = _get("CONSOLE_CH_HOST", _get("CLICKHOUSE_HOST","127.0.0.1"))
    CH_PORT     = _get("CONSOLE_CH_PORT", _get("CLICKHOUSE_PORT","8123"))
    CH_USER     = _get("CONSOLE_CH_USER", _get("CLICKHOUSE_USER","default"))
    CH_PASSWORD = _get("CONSOLE_CH_PASSWORD", _get("CLICKHOUSE_PASSWORD",""))
    CH_DATABASE = _get("CONSOLE_CH_DATABASE", _get("CLICKHOUSE_DATABASE", None))
    CH_SECURE   = "1" if _bool("CONSOLE_CH_SECURE", _bool("CLICKHOUSE_SECURE", False)) else "0"

    # PostgreSQL
    DATABASE_URL = _get("DATABASE_URL", None)  # e.g. postgresql://user:pass@host:5432/db
    META_DATABASE_URL = _get("META_DATABASE_URL", None)  # e.g. postgresql+psycopg://postgres:postgres@127.0.0.1:5544/postgres
    PG_POOL_SIZE = int(_get("PG_POOL_SIZE", "5"))
    PG_MAX_OVERFLOW = int(_get("PG_MAX_OVERFLOW", "5"))
    PG_POOL_PRE_PING = _bool("PG_POOL_PRE_PING", True)

    # parallelism
    MAX_CONCURRENT_RUNS = int(_get("MAX_CONCURRENT_RUNS", "4"))

settings = Settings()