import pytest
from pydantic import ValidationError
from app.models import SourceInput, AnalyzeRequest, ExportRequest, Workspace
from app.parser import source_hash

@pytest.mark.parametrize('value', [False, 1, 0, 'true', 'false', None, [], {}])
def test_age_requires_boolean_true(sample, value):
    with pytest.raises(ValidationError):
        SourceInput(**{**sample, 'adult_confirmed': value})

@pytest.mark.parametrize('key', ['adult_confirmed', 'processing_consent'])
def test_missing_consent_rejected(sample, key):
    del sample[key]
    with pytest.raises(ValidationError): SourceInput(**sample)

def test_extra_fields_forbidden(sample):
    with pytest.raises(ValidationError): SourceInput(**sample, ats_score=99)

@pytest.mark.parametrize('value', [123, '     ', 'ok\x00hidden', 'Text with \u202e bidi control'])
def test_invalid_text(sample, value):
    with pytest.raises(ValidationError): SourceInput(**{**sample, 'resume_text': value})

def test_strict_boolean_for_review(sample):
    with pytest.raises(ValidationError): AnalyzeRequest(**sample, requirements_reviewed='true')

def test_export_template_and_hash(sample):
    with pytest.raises(ValidationError): ExportRequest(**sample, source_hash='not-a-hash')
    with pytest.raises(ValidationError): ExportRequest(**sample, source_hash=source_hash(sample['resume_text']), template='unsafe')

def test_duplicate_decisions_rejected(sample):
    with pytest.raises(ValidationError):
        AnalyzeRequest(**sample, decisions=[{'id': 'x', 'decision': 'include'}, {'id': 'x', 'decision': 'include'}])

def test_unicode_preserved(sample):
    text = 'Jos\u00e9 N\u00fa\u00f1ez\nSkills\nPython'
    assert SourceInput(**{**sample, 'resume_text': text}).resume_text == text

def test_workspace_unexpected_fields():
    with pytest.raises(ValidationError): Workspace(resume_text='', job_description='', token='secret')

def test_shared_contract_fixture_file():
    import json
    from pathlib import Path
    cases = json.loads((Path(__file__).resolve().parents[3] / 'fixtures/contract-cases.json').read_text())
    for case in cases:
        try:
            SourceInput.model_validate(case['payload'])
            actual = True
        except ValidationError:
            actual = False
        assert actual is case['valid'], case['name']
