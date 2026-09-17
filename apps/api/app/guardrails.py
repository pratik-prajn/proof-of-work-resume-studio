"""Closed-world guard: accept only an enumerated, source-local transformation.

This intentionally rejects many semantically safe paraphrases. It does not claim
that an entity diff, model, or user-controlled source can prove real-world truth.
"""
from __future__ import annotations
import re
from .parser import Block

GUARD_VERSION = 'closed-world-1.0.0'
PAST_ACTION = re.compile(r'^I (created|built|assisted|supported|managed|prepared|used|developed|designed|wrote|analyzed|analysed|maintained|tested|completed|edited|produced|organized|organised|coordinated|tracked|reported)\b')
CLICHES = ('results-driven', 'dynamic professional', 'synergy', 'go-getter', 'rockstar', 'visionary leader')
NUMBERS = re.compile(r'(?:[\u20b9$\u00a3\u20ac]\s*)?\d+(?:[,.]\d+)*(?:\s*(?:%|crore|lakh|million|billion|hours|years|months|days))?', re.I)


def variants(block: Block) -> set[str]:
    # Whitespace is the only generally permitted normalization.
    base = ' '.join(block.text.split())
    allowed = {block.text, base}
    if block.kind == 'bullet' and PAST_ACTION.match(base):
        short = base[2:]
        allowed.add(short[0].upper() + short[1:])
    return allowed


def suggestion(block: Block) -> str:
    base = ' '.join(block.text.split())
    if block.kind == 'bullet' and PAST_ACTION.match(base):
        return base[2].upper() + base[3:]
    return base


def evaluate(block: Block, candidate: str) -> dict:
    if candidate in variants(block):
        return {
            'block_id': block.id, 'status': 'accepted', 'original': block.text,
            'candidate': candidate, 'output': candidate, 'changed': candidate != block.text,
            'reasons': ['Allowed source-preserving transformation.' if candidate != block.text else 'Original retained; no safe tightening needed.'],
            'source_start': block.source_start, 'source_end': block.source_end,
            'guard_version': GUARD_VERSION,
        }
    reasons = []
    added = sorted(set(NUMBERS.findall(candidate)) - set(NUMBERS.findall(block.text)))
    if added:
        reasons.append('Unsupported number, amount, unit or date: ' + ', '.join(added))
    lower, original = candidate.casefold(), block.text.casefold()
    if any(x in lower and x not in original for x in ('led ', 'owned ', 'spearheaded ', 'directed ')):
        reasons.append('Responsibility or ownership may have increased.')
    if any(x in lower and x not in original for x in CLICHES):
        reasons.append('Introduced promotional cliche.')
    reasons.append('The wording is not an approved transformation of this exact source block. Arbitrary paraphrases are not trusted.')
    return {
        'block_id': block.id, 'status': 'rejected', 'original': block.text,
        'candidate': candidate, 'output': block.text, 'changed': False, 'reasons': reasons,
        'source_start': block.source_start, 'source_end': block.source_end,
        'guard_version': GUARD_VERSION,
    }
