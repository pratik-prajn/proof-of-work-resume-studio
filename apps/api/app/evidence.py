"""Inspects artefacts as data only. Never executes cells or clones/runs code."""
import ast
import hashlib
import json
import re
import httpx

def inspect_notebook(raw: bytes) -> dict:
    doc = json.loads(raw)
    if not isinstance(doc, dict) or doc.get('nbformat') != 4 or not isinstance(doc.get('cells'), list):
        raise ValueError('Expected a version 4 notebook.')
    if len(doc['cells']) > 500:
        raise ValueError('Maximum 500 notebook cells.')
    imports, code_cells = set(), 0
    for cell in doc['cells']:
        if not isinstance(cell, dict):
            raise ValueError('Invalid cell.')
        if cell.get('cell_type') != 'code':
            continue
        code_cells += 1
        source = cell.get('source', '')
        if isinstance(source, list) and all(isinstance(x, str) for x in source):
            source = ''.join(source)
        if not isinstance(source, str) or len(source) > 50000:
            continue
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(x.name.split('.')[0] for x in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split('.')[0])
        except (SyntaxError, RecursionError):
            continue
    return {
        'kind': 'inspected_notebook', 'sha256': hashlib.sha256(raw).hexdigest(),
        'facts': [f'{code_cells} code cells are present.'] + [f'An import of {name} appears in the code.' for name in sorted(imports)],
        'limitations': ['No code was executed.', 'Imports do not prove proficiency, authorship, or successful execution.', 'No business outcomes were verified.'],
        'automatically_added_to_resume': False,
    }

async def inspect_github(url: str) -> dict:
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9_.-]{1,100})/?', url)
    if not match or match.group(2) in ('.', '..'):
        raise ValueError('Use a public https://github.com/owner/repository URL, without query parameters.')
    owner, repo = match.groups()
    if repo.endswith('.git'):
        repo = repo[:-4]
    base = f'https://api.github.com/repos/{owner}/{repo}'
    async with httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False,
                                 headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'ProofOfWorkResumeStudio/1.0'}) as client:
        responses = []
        for suffix in ('', '/languages'):
            async with client.stream('GET', base + suffix) as response:
                if response.status_code != 200:
                    raise ValueError('Repository unavailable or GitHub rate limit reached. Private repositories are not supported.')
                parts, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 200000:
                        raise ValueError('GitHub response too large.')
                    parts.append(chunk)
                responses.append(json.loads(b''.join(parts)))
    metadata, languages = responses
    if not isinstance(languages, dict):
        raise ValueError('Unexpected repository response.')
    return {
        'kind': 'inspected_public_repository', 'url': f'https://github.com/{owner}/{repo}',
        'facts': [f"Repository name reported by GitHub: {metadata.get('full_name', owner + '/' + repo)}."] +
                 [f'GitHub reports files classified as {name}.' for name in sorted(languages)[:40]],
        'limitations': ['Repository-level observations do not prove your contribution or skill.', 'README claims and business outcomes are not verified.', 'No repository code was executed.'],
        'automatically_added_to_resume': False,
    }
