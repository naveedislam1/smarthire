"""Jobs service database wiring."""

from smarthire_common.database import (
    Base,
    make_engine,
    make_get_db,
    make_session_factory,
)

from app.config import settings

engine = make_engine(settings.database_url, echo=settings.debug)
SessionFactory = make_session_factory(engine)
get_db = make_get_db(SessionFactory)

__all__ = ["Base", "engine", "SessionFactory", "get_db"]
