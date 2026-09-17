"""Lossless line parser. Heuristic presentation labels are not verified facts."""
from __future__ import annotations
import hashlib
import re
from dataclasses import asdict, dataclass

PARSER_VERSION = 'line-parser-1.0.0'
SECTION_NAMES = {
    'summary': 'summary', 'professional summary': 'summary', 'profile': 'summary',
    'experience': 'experience', 'work experience': 'experience',
    'professional experience': 'experience', 'employment': 'experience',
    'projects': 'projects', 'personal projects': 'projects', 'academic projects': 'projects',
    'education': 'education', 'academic qualifications': 'education',
    'skills': 'skills', 'technical skills': 'skills', 'core skills': 'skills',
    'certifications': 'certifications', 'certificates': 'certifications',
    'achievements': 'other', 'awards': 'other', 'volunteering': 'other',
    'languages': 'other', 'additional information': 'other',
}

@dataclass(frozen=True)
class Block:
    id: str
    kind: str
    section: str
    group: int
    text: str
    source_start: int
    source_end: int
    source_text: str
    evidence: str = 'user_provided'

    def public(self):
        return asdict(self)


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def parse_resume(text: str) -> list[Block]:
    blocks: list[Block] = []
    section, group, offset = 'contact', 0, 0
    for raw in text.splitlines(keepends=True):
        line = raw.strip()
        if not line:
            offset += len(raw)
            continue
        start = offset + len(raw) - len(raw.lstrip())
        end = start + len(line)
        heading = line.casefold().rstrip(':').strip()
        if not blocks:
            kind = 'name'
        elif heading in SECTION_NAMES:
            section = SECTION_NAMES[heading]
            group += 1
            kind = 'heading'
        elif re.match(r'^(?:[-*\u2022]\s+|\d+[.)]\s+)', line):
            kind = 'bullet'
        else:
            kind = 'line'
        # Source includes the original marker; displayed text may remove only that marker.
        content = re.sub(r'^(?:[-*\u2022]\s+|\d+[.)]\s+)', '', line) if kind == 'bullet' else line
        if len(content) > 3000:
            raise ValueError('A resume line exceeds 3,000 characters. Add line breaks.')
        identity = hashlib.sha256(f'{start}:{end}:{line}'.encode()).hexdigest()[:16]
        blocks.append(Block(f'b_{identity}', kind, section, group, content, start, end, line))
        offset += len(raw)
    if not blocks:
        raise ValueError('No readable resume content.')
    return blocks


def ordered_blocks(blocks: list[Block], template: str) -> list[Block]:
    if template == 'professional':
        return blocks
    # Move entire section groups, never facts within or between roles.
    order = {'contact': 0, 'summary': 1, 'education': 2, 'projects': 3,
             'experience': 4, 'skills': 5, 'certifications': 6, 'other': 7}
    return sorted(blocks, key=lambda b: (order.get(b.section, 7), b.group, b.source_start))
