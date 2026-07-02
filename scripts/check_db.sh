#!/usr/bin/env bash
set -euo pipefail

docker compose exec -T worker python - <<'PY'
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as c:
    print(c.execute(text("select 1")).scalar())
PY
