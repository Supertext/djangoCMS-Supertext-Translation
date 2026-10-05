"""Creates the demo database (DJANGOCMS_DB_NAME, default "djangocms") on the server from DATABASE_URL."""

import os
import re
import sys
import time
from urllib.parse import urlparse

import psycopg

url = urlparse(os.environ.get("DATABASE_URL", ""))
if not url.scheme.startswith("postgres"):
    sys.exit("DATABASE_URL must be a postgresql:// URL")
name = os.environ.get("DJANGOCMS_DB_NAME", "djangocms")
if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
    sys.exit("DJANGOCMS_DB_NAME may only contain a-z, 0-9 and _")

for attempt in range(20):
    try:
        conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
        break
    except psycopg.OperationalError as error:
        if attempt == 19:
            sys.exit(f"Cannot reach PostgreSQL: {error}")
        time.sleep(3)

with conn:
    if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
        conn.execute(f'CREATE DATABASE "{name}"')
        print(f"Created database {name}")
