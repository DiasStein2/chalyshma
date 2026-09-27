from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


database_url = make_url(settings.database_url)
if database_url.drivername in {"postgres", "postgresql"}:
    database_url = database_url.set(drivername="postgresql+psycopg")
if database_url.host and database_url.host.endswith(("supabase.com", "supabase.co")):
    if "sslmode" not in database_url.query:
        database_url = database_url.update_query_dict({"sslmode": "require"})

connect_args = {}
engine_options = {"pool_pre_ping": True, "connect_args": connect_args}

if database_url.drivername.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif database_url.host and database_url.host.endswith(("supabase.com", "supabase.co")):
    if database_url.port == 6543:
        # Supabase transaction pooling is intended for serverless functions.
        # It doesn't support prepared statements or client-side connection pools.
        connect_args["prepare_threshold"] = None
        engine_options["poolclass"] = NullPool

engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
