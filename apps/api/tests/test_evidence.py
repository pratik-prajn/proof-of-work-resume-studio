import json
import pytest
from app.evidence import inspect_notebook, inspect_github

def test_notebook_observations_only(tmp_path):
    sentinel = tmp_path / 'executed.txt'
    raw = json.dumps({'nbformat':4,'cells':[{'cell_type':'code','source':f'import pandas as pd\nfrom numpy import array\nopen({str(sentinel)!r}, "w").write("bad")'}]}).encode()
    result = inspect_notebook(raw)
    assert not sentinel.exists()
    assert 'An import of pandas appears in the code.' in result['facts']
    assert not result['automatically_added_to_resume']

def test_notebook_invalid():
    with pytest.raises(ValueError): inspect_notebook(b'{"cells":[]}')

@pytest.mark.parametrize('url',['http://127.0.0.1/a/b','https://github.com.evil.example/a/b','https://github.com/a/b?next=bad','https://github.com/a/..','https://github.com/a/b/tree/main'])
def test_github_ssrf_rejected(url):
    import asyncio
    with pytest.raises(ValueError): asyncio.run(inspect_github(url))
