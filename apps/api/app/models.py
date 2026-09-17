"""Authoritative API contracts. Changes must update web/lib/schemas.ts + fixtures."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CONTRACT_VERSION = '1.0.0'

class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=False)

    @field_validator('adult_confirmed', 'processing_consent', 'storage_consent', 'network_consent', mode='before', check_fields=False)
    @classmethod
    def literal_consent(cls, value):
        # Python equality makes True == 1; do not let Literal[True] coerce 1.
        if value is not True:
            raise ValueError('Explicit boolean consent is required.')
        return value

class SourceInput(StrictModel):
    resume_text: str = Field(min_length=10, max_length=20000)
    job_description: str = Field(min_length=10, max_length=30000)
    adult_confirmed: Literal[True]
    processing_consent: Literal[True]

    @field_validator('resume_text', 'job_description')
    @classmethod
    def readable(cls, value: str) -> str:
        if len(value.strip()) < 10:
            raise ValueError('Enter at least 10 non-whitespace characters.')
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\u202a-\u202e\u2066-\u2069]', value):
            raise ValueError('Unsupported control characters. Paste plain text instead.')
        if len(value.splitlines()) > 250:
            raise ValueError('Maximum 250 lines per input.')
        return value

class RequirementDecision(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    decision: Literal['include', 'exclude']
    reason: str = Field(default='', max_length=300)

class AnalyzeRequest(SourceInput):
    decisions: list[RequirementDecision] = Field(default_factory=list, max_length=200)
    requirements_reviewed: bool = False

    @model_validator(mode='after')
    def unique_decisions(self):
        ids = [x.id for x in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate requirement decisions.')
        return self

class RewriteRequest(SourceInput):
    source_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    use_llm: bool = False
    llm_consent: bool = False

class GuardRequest(SourceInput):
    source_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    block_id: str = Field(min_length=1, max_length=80)
    candidate: str = Field(min_length=1, max_length=3000)

class ExportRequest(SourceInput):
    source_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    overrides: dict[str, str] = Field(default_factory=dict, max_length=200)
    template: Literal['professional', 'fresher'] = 'professional'

    @field_validator('overrides')
    @classmethod
    def bounded_overrides(cls, value):
        if any(len(k) > 80 or len(v) > 3000 for k, v in value.items()):
            raise ValueError('An override is too long.')
        return value

class Workspace(StrictModel):
    schema_version: Literal['1.0.0'] = '1.0.0'
    resume_text: str = Field(max_length=20000)
    job_description: str = Field(max_length=30000)
    template: Literal['professional', 'fresher'] = 'professional'
    decisions: list[RequirementDecision] = Field(default_factory=list, max_length=200)
    requirements_reviewed: bool = False
    overrides: dict[str, str] = Field(default_factory=dict, max_length=200)
    source_hash: str = ''

class SaveDraftRequest(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    storage_consent: Literal[True]
    workspace: Workspace

class InspectRepoRequest(StrictModel):
    url: str = Field(max_length=300)
    adult_confirmed: Literal[True]
    network_consent: Literal[True]

class LLMItem(StrictModel):
    block_id: str = Field(max_length=80)
    candidate: str = Field(max_length=3000)

class LLMResponse(StrictModel):
    items: list[LLMItem] = Field(max_length=100)
