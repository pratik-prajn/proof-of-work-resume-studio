"""Opt-in, encrypted workspace history. Never called for anonymous processing."""
import datetime as dt
import json
import uuid
from functools import lru_cache
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, String, Text, DateTime, select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from .config import settings

class Base(DeclarativeBase):
    pass

class Draft(Base):
    __tablename__ = 'drafts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(128), index=True)
    # Title and workspace are encrypted together; no plaintext resume/title in SQL.
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)

@lru_cache(maxsize=4)
def get_engine(url: str):
    kwargs = {'connect_args': {'check_same_thread': False}} if url.startswith('sqlite') else {}
    return create_engine(url, pool_pre_ping=True, **kwargs)

def init_storage():
    cfg = settings()
    if cfg.history_enabled:
        Fernet(cfg.encryption_key.encode())
        # Migrations are explicit in production; create tables for local SQLite only.
        if cfg.database_url.startswith('sqlite'):
            Base.metadata.create_all(get_engine(cfg.database_url))

def _cipher():
    return Fernet(settings().encryption_key.encode())

def _cleanup(session):
    session.execute(delete(Draft).where(Draft.expires_at <= dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)))

def save(owner: str, title: str, workspace: dict):
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    with Session(get_engine(settings().database_url)) as session:
        _cleanup(session)
        count = len(session.scalars(select(Draft.id).where(Draft.owner == owner)).all())
        if count >= 100:
            raise ValueError('History is limited to 100 snapshots. Delete an old snapshot first.')
        payload = _cipher().encrypt(json.dumps({'title': title, 'workspace': workspace}).encode()).decode()
        draft = Draft(id=str(uuid.uuid4()), owner=owner, payload=payload, created_at=now, expires_at=now + dt.timedelta(days=30))
        session.add(draft)
        session.commit()
        return {'id': draft.id, 'title': title, 'created_at': now.isoformat() + 'Z', 'expires_at': draft.expires_at.isoformat() + 'Z'}

def list_drafts(owner: str):
    with Session(get_engine(settings().database_url)) as session:
        _cleanup(session)
        rows = session.scalars(select(Draft).where(Draft.owner == owner).order_by(Draft.created_at.desc())).all()
        result = [{'id': d.id, 'title': json.loads(_cipher().decrypt(d.payload.encode()))['title'],
                   'created_at': d.created_at.isoformat() + 'Z', 'expires_at': d.expires_at.isoformat() + 'Z'} for d in rows]
        session.commit()
        return result

def get_draft(owner: str, draft_id: str):
    with Session(get_engine(settings().database_url)) as session:
        _cleanup(session)
        row = session.scalar(select(Draft).where(Draft.id == draft_id, Draft.owner == owner))
        result = json.loads(_cipher().decrypt(row.payload.encode())) if row else None
        session.commit()
        return result

def remove(owner: str, draft_id: str | None = None):
    with Session(get_engine(settings().database_url)) as session:
        stmt = delete(Draft).where(Draft.owner == owner)
        if draft_id:
            stmt = stmt.where(Draft.id == draft_id)
        count = session.execute(stmt).rowcount
        session.commit()
        return count


def prune_expired():
    with Session(get_engine(settings().database_url)) as session:
        _cleanup(session)
        session.commit()
