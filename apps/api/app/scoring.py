"""Versioned exact-alias matching. No model, fuzzy inference, or hiring prediction."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .models import AnalyzeRequest
from .parser import PARSER_VERSION, parse_resume, source_hash

TAXONOMY = json.loads(Path(__file__).with_name('taxonomy.json').read_text())
SKILLS = {x['id']: x for x in TAXONOMY['skills']}
SCORE_VERSION = 'coverage-1.0.0'
ALIAS_PATTERNS = [(s['id'], re.compile(r'(?<![\w+#])' + re.escape(a) + r'(?![\w+#])', re.I))
                  for s in SKILLS.values() for a in s['aliases']]
NEGATION = re.compile(r"\b(?:no|not|without|lack(?:ing)?|never|cannot|don['\u2019]t|doesn['\u2019]t|haven['\u2019]t|can['\u2019]t)\b", re.I)
LEARNING = re.compile(r'\b(?:learning|studying|beginner|planned|planning|will learn|want to learn|aspiring|interested in)\b', re.I)
NON_SKILL = re.compile(r'\b(?:\d+\+?\s*(?:years?|months?)|degree|bachelor|master|notice period|relocat|salary|certifi(?:ed|cation))', re.I)


def occurrences(text: str):
    matches = []
    for sid, pattern in ALIAS_PATTERNS:
        for m in pattern.finditer(text):
            matches.append({'skill_id': sid, 'start': m.start(), 'end': m.end(), 'text': m.group()})
    # Longest overlapping phrase wins, e.g. Google Analytics 4 vs Google Analytics.
    selected = []
    for match in sorted(matches, key=lambda x: (-(x['end'] - x['start']), x['start'], x['skill_id'])):
        if not any(match['start'] < x['end'] and match['end'] > x['start'] for x in selected):
            selected.append(match)
    return sorted(selected, key=lambda x: (x['start'], x['skill_id']))


FILLER_WORDS = set('and or in with of the a an to for using use used knowledge experience skills skill required require requirements preferred desirable bonus is are have must should be good familiarity proficient proficiency working practical'.split())

def context_status(text: str, start: int, end: int) -> str:
    prefix = re.split(r'\bbut\b|[;.!?]', text[:start], flags=re.I)[-1]
    suffix = text[end:]
    negative = bool(NEGATION.search(prefix)) and not re.search(r'not only\s*$', prefix, re.I)
    negative = negative or bool(re.match(r"\s*(?:[:=(,-]\s*)?(?:(?:is|are)\s+)?(?:not\b|none\b|no experience\b)", suffix, re.I))
    learning = bool(LEARNING.search(prefix)) or bool(re.match(r'\s*(?:[:=(,-]\s*)?(?:learning|beginner|planned)\b', suffix, re.I))
    return 'negated' if negative else 'learning' if learning else 'mentioned'

def has_unclassified_remainder(line: str, hits: list[dict]) -> bool:
    remaining = list(line)
    for hit in hits:
        remaining[hit['start']:hit['end']] = ' ' * (hit['end'] - hit['start'])
    words = re.findall(r"[A-Za-z0-9]+", ''.join(remaining).lower())
    return any(word not in FILLER_WORDS for word in words)

def requirements(jd: str) -> list[dict]:
    found, seen, offset = [], set(), 0
    for raw in jd.splitlines(keepends=True):
        line = raw.strip()
        if not line:
            offset += len(raw)
            continue
        start = offset + len(raw) - len(raw.lstrip())
        hits = [h for h in occurrences(line) if context_status(line, h['start'], h['end']) != 'negated']
        ids = list(dict.fromkeys(x['skill_id'] for x in hits))
        alternative = len(ids) == 2 and bool(re.search(r'\bor\b', line, re.I)) and not re.search(r'\band\b', line, re.I)
        groups = [ids] if alternative else [[sid] for sid in ids]
        for group in groups:
            key = '|'.join(sorted(group))
            if key in seen:
                continue
            seen.add(key)
            found.append({
                'id': 'r_' + hashlib.sha256(key.encode()).hexdigest()[:12],
                'kind': 'skill', 'skill_ids': group,
                'label': ' OR '.join(SKILLS[x]['label'] for x in group),
                'jd_text': line, 'jd_start': start, 'jd_end': start + len(line),
                'priority': 'preferred' if re.search(r'preferred|nice to have|bonus|desirable', line, re.I) else 'required',
                'alternative': alternative,
            })
        # Every unrecognized line is surfaced. Known lines with non-skill constraints
        # get an additional item so years/degrees are never silently treated as satisfied.
        if not ids or NON_SKILL.search(line) or has_unclassified_remainder(line, hits) or (re.search(r'\bor\b', line, re.I) and not alternative):
            identity = hashlib.sha256(f'{start}:{line}'.encode()).hexdigest()[:12]
            found.append({
                'id': 'u_' + identity, 'kind': 'unresolved', 'skill_ids': [],
                'label': 'Review context / non-skill constraints', 'jd_text': line,
                'jd_start': start, 'jd_end': start + len(line), 'priority': 'unclassified', 'alternative': False,
            })
        offset += len(raw)
    if len(found) > 200:
        raise ValueError('Too many requirements. Narrow the job description.')
    return found


def resume_evidence(text: str):
    results = {}
    for block in parse_resume(text):
        if block.kind in ('heading', 'name') or block.section == 'contact':
            continue
        for hit in occurrences(block.source_text):
            status = context_status(block.source_text, hit['start'], hit['end'])
            if status == 'mentioned' and block.section == 'skills':
                status = 'listed'
            results.setdefault(hit['skill_id'], []).append({
                'block_id': block.id, 'text': hit['text'], 'quote': block.source_text,
                'start': block.source_start + hit['start'], 'end': block.source_start + hit['end'],
                'status': status, 'source': 'user_provided',
            })
    return results


def analyze(req: AnalyzeRequest) -> dict:
    reqs = requirements(req.job_description)
    known_ids = {r['id'] for r in reqs}
    decisions = {d.id: d for d in req.decisions}
    if set(decisions) - known_ids:
        raise ValueError('Requirement decisions are stale. Analyze the current job description again.')
    evidence = resume_evidence(req.resume_text)
    numerator = denominator = unresolved = 0
    for r in reqs:
        decision = decisions.get(r['id'])
        if decision and decision.decision == 'exclude' and not decision.reason.strip():
            raise ValueError('Excluded requirements need a reason.')
        if decision and decision.decision == 'include' and r['kind'] == 'unresolved':
            raise ValueError('Unclassified requirements cannot be counted as matched skills.')
        r['excluded'] = bool(decision and decision.decision == 'exclude')
        r['exclusion_reason'] = decision.reason if r['excluded'] else ''
        r['evidence'] = [e for sid in r['skill_ids'] for e in evidence.get(sid, [])]
        supported = any(e['status'] in ('listed', 'mentioned') for e in r['evidence'])
        r['status'] = 'excluded' if r['excluded'] else 'unresolved' if r['kind'] == 'unresolved' else 'matched' if supported else 'missing'
        if r['status'] == 'unresolved':
            unresolved += 1
        if r['kind'] == 'skill' and not r['excluded']:
            denominator += 1
            numerator += int(supported)
    versioned = {
        'resume_text': req.resume_text, 'job_description': req.job_description,
        'decisions': [decisions[k].model_dump() for k in sorted(decisions)],
        'requirements_reviewed': req.requirements_reviewed,
        'scoring_version': SCORE_VERSION, 'taxonomy_version': TAXONOMY['version'],
        'taxonomy_hash': source_hash(json.dumps(TAXONOMY, sort_keys=True)),
        'parser_version': PARSER_VERSION,
    }
    return {
        'source_hash': source_hash(req.resume_text),
        'assessment_hash': source_hash(json.dumps(versioned, sort_keys=True, ensure_ascii=False)),
        'score': round(100 * numerator / denominator, 1) if denominator else None,
        'matched': numerator, 'total': denominator, 'unresolved': unresolved,
        'complete': req.requirements_reviewed and unresolved == 0 and denominator > 0,
        'requirements': reqs, 'blocks': [b.public() for b in parse_resume(req.resume_text)],
        'versions': {k: versioned[k] for k in ('scoring_version', 'taxonomy_version', 'taxonomy_hash', 'parser_version')},
        'warnings': [
            'Coverage measures visible skill mentions, not proficiency, employment truth, or hiring probability.',
            'Starter dictionary only. Read every original JD line; wording, years, degrees and proficiency may need manual review.',
            'All resume claims remain user-provided unless separately assessed. No evidence is independently verified here.',
        ],
    }
