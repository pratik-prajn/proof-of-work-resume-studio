from dataclasses import dataclass
import os
DEV_SECRET = 'local-development-only-change-before-deployment'

@dataclass(frozen=True)
class Settings:
    environment: str
    internal_key: str
    token_secret: str
    pdf_engine: str
    history_enabled: bool
    database_url: str
    encryption_key: str
    llm_url: str
    llm_key: str
    llm_model: str
    github_enabled: bool

def settings() -> Settings:
    s = Settings(
        environment=os.getenv('APP_ENV', 'development'),
        internal_key=os.getenv('INTERNAL_API_KEY', DEV_SECRET),
        token_secret=os.getenv('API_TOKEN_SECRET', DEV_SECRET),
        pdf_engine=os.getenv('PDF_ENGINE', 'typst'),
        history_enabled=os.getenv('ENABLE_HISTORY', 'false').lower() == 'true',
        database_url=os.getenv('DATABASE_URL', 'sqlite:///./studio.db'),
        encryption_key=os.getenv('HISTORY_ENCRYPTION_KEY', ''),
        llm_url=os.getenv('LLM_BASE_URL', ''), llm_key=os.getenv('LLM_API_KEY', ''),
        llm_model=os.getenv('LLM_MODEL', ''),
        github_enabled=os.getenv('ENABLE_GITHUB_INSPECTOR', 'false').lower() == 'true',
    )
    if s.environment == 'production':
        for key in (s.internal_key, s.token_secret):
            if len(key) < 32 or key == DEV_SECRET:
                raise RuntimeError('Set independent production API secrets with at least 32 characters.')
        if s.internal_key == s.token_secret:
            raise RuntimeError('INTERNAL_API_KEY and API_TOKEN_SECRET must differ.')
    if s.pdf_engine not in {'typst', 'reportlab'}:
        raise RuntimeError('PDF_ENGINE must be typst or reportlab.')
    if s.history_enabled and not s.encryption_key:
        raise RuntimeError('History requires HISTORY_ENCRYPTION_KEY. Run scripts/setup.py.')
    return s
