import json
import os
from pathlib import Path
import pytest
os.environ['PDF_ENGINE'] = 'reportlab'
os.environ['ENABLE_HISTORY'] = 'false'

@pytest.fixture
def sample():
    return json.loads((Path(__file__).resolve().parents[3] / 'fixtures/sample.json').read_text())

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app, request_times
    request_times.clear()
    with TestClient(app) as c:
        yield c

@pytest.fixture
def headers():
    from app.config import DEV_SECRET
    return {'X-Internal-Key': DEV_SECRET}
