import copy
import pytest
from app.models import AnalyzeRequest
from app.scoring import analyze, occurrences, requirements
from app.parser import parse_resume

def score(sample, resume, jd):
    return analyze(AnalyzeRequest(**{**sample, 'resume_text': resume, 'job_description': jd}))

def test_sample_score(sample):
    result = analyze(AnalyzeRequest(**sample))
    assert (result['matched'], result['total'], result['score'], result['unresolved']) == (5, 8, 62.5, 2)
    assert result['complete'] is False

def test_reproducible(sample):
    first = analyze(AnalyzeRequest(**sample))
    for _ in range(20): assert analyze(AnalyzeRequest(**sample)) == first

def test_span_provenance(sample):
    result = analyze(AnalyzeRequest(**sample))
    for r in result['requirements']:
        assert sample['job_description'][r['jd_start']:r['jd_end']] == r['jd_text']
        for e in r['evidence']:
            assert sample['resume_text'][e['start']:e['end']] == e['text']
    for b in parse_resume(sample['resume_text']):
        assert sample['resume_text'][b.source_start:b.source_end] == b.source_text

def test_deduplicate(sample):
    r = score(sample, 'Person Name\nSkills\nExcel, Excel, Excel', 'Excel\nMicrosoft Excel\nMS Excel')
    assert (r['total'], r['matched']) == (1, 1)

def test_or_is_one_requirement(sample):
    r = score(sample, 'Person Name\nSkills\nExcel', 'Excel or Google Sheets')
    assert r['matched'] == r['total'] == 1

def test_and_is_two(sample):
    r = score(sample, 'Person Name\nSkills\nExcel', 'Excel and Google Sheets')
    assert r['matched'] == 1 and r['total'] == 2

@pytest.mark.parametrize('text,status', [('No experience with SQL', 'negated'), ('Learning SQL', 'learning'), ('Without SQL experience', 'negated')])
def test_negative_learning_excluded(sample, text, status):
    r = score(sample, 'Person Name\nSkills\n' + text, 'SQL required')
    assert r['matched'] == 0
    assert r['requirements'][0]['evidence'][0]['status'] == status

def test_contrast_does_not_negate_next_skill(sample):
    r = score(sample, 'Person Name\nSkills\nNo SQL but Python', 'SQL and Python')
    assert r['matched'] == 1

def test_java_not_javascript():
    assert {x['skill_id'] for x in occurrences('JavaScript')} == {'javascript'}

def test_longer_phrase_wins():
    assert {x['skill_id'] for x in occurrences('Google Analytics 4')} == {'ga4'}

def test_punctuation_skills():
    assert {x['skill_id'] for x in occurrences('C++, C#, .NET')} == {'cpp', 'csharp', 'dotnet'}

def test_fuzzy_typo_not_auto_matched():
    assert occurrences('Pythno') == []

def test_no_denominator_is_not_100(sample):
    r = score(sample, 'Person Name\nSkills\nPython', 'Be a good colleague')
    assert r['score'] is None and r['unresolved'] == 1 and not r['complete']

def test_years_remain_unresolved(sample):
    r = score(sample, 'Person Name\nSkills\nPython', '3 years of Python experience')
    assert r['matched'] == 1 and r['unresolved'] == 1

def test_reviewed_complete_and_hash_changes(sample):
    initial = analyze(AnalyzeRequest(**sample))
    decisions = [{'id': r['id'], 'decision': 'exclude', 'reason': 'Manually reviewed context; not a skill.'} for r in initial['requirements'] if r['kind'] == 'unresolved']
    reviewed = analyze(AnalyzeRequest(**sample, decisions=decisions, requirements_reviewed=True))
    assert reviewed['complete'] and reviewed['score'] == initial['score']
    assert reviewed['assessment_hash'] != initial['assessment_hash']

def test_bad_decisions_fail(sample):
    with pytest.raises(ValueError): analyze(AnalyzeRequest(**sample, decisions=[{'id':'unknown', 'decision':'include'}]))
    initial = analyze(AnalyzeRequest(**sample))
    known = initial['requirements'][0]['id']
    with pytest.raises(ValueError): analyze(AnalyzeRequest(**sample, decisions=[{'id':known, 'decision':'exclude'}]))
    unknown = next(r['id'] for r in initial['requirements'] if r['kind'] == 'unresolved')
    with pytest.raises(ValueError): analyze(AnalyzeRequest(**sample, decisions=[{'id':unknown, 'decision':'include'}]))

def test_source_does_not_drop_lines(sample):
    nonblank = [line.strip() for line in sample['resume_text'].splitlines() if line.strip()]
    assert [b.source_text for b in parse_resume(sample['resume_text'])] == nonblank

@pytest.mark.parametrize('text', ["I don't know SQL", 'SQL: none', 'SQL is not used', 'SQL (learning)'])
def test_additional_negative_contexts(sample, text):
    r = score(sample, 'Person Name\nSkills\n' + text, 'SQL required')
    assert r['matched'] == 0

def test_unknown_requirement_inside_known_line_surfaces(sample):
    r = score(sample, 'Person Name\nSkills\nPython', 'Python and FluxCapacitor')
    assert r['unresolved'] == 1 and not r['complete']

def test_negated_jd_requirement_is_not_scored(sample):
    r = score(sample, 'Person Name\nSkills\nPython', 'We do not require SQL')
    assert r['total'] == 0 and r['unresolved'] == 1
