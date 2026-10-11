
from datetime import datetime

from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow_iso(_context=None) -> str:
    return datetime.utcnow().isoformat()
