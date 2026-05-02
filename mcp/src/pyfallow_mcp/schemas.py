from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SummaryCounts(FlexibleModel):
    total_issues: int = 0
    errors: int = 0
    warnings: int = 0
    info: int = 0


class DiffScope(FlexibleModel):
    since: str | None = None
    since_resolved: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    changed_modules: list[str] = Field(default_factory=list)
    filtering_active: bool = False
    reason: str | None = None


class Finding(FlexibleModel):
    id: str
    rule: str
    severity: str
    confidence: str
    path: str | None = None
    symbol: str | None = None
    module: str | None = None
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    fingerprint: str


class AnalysisResult(BaseModel):
    summary: SummaryCounts
    findings: list[Finding]
    diff_scope: DiffScope
    truncated: bool = False
    next_cursor: str | None = None


class ProjectOverview(BaseModel):
    roots: list[str]
    entrypoints: list[dict[str, Any]]
    frameworks: list[str]
    dependency_files: list[str]
    modules_count: int


class ArchitectureMap(BaseModel):
    cycles: list[dict[str, Any]]
    high_fan_in: list[dict[str, Any]]
    high_fan_out: list[dict[str, Any]]
    hotspots: list[Finding]


class ExportRef(FlexibleModel):
    module: str
    path: str
    name: str


class BoundaryRuleSummary(BaseModel):
    name: str
    from_patterns: list[str]
    disallow: list[str]
    severity: str


class RiskItem(FlexibleModel):
    rule: str
    severity: str
    confidence: str
    path: str | None = None
    message: str
    fingerprint: str


class AgentContext(BaseModel):
    project_overview: ProjectOverview
    architecture_map: ArchitectureMap
    public_api: list[ExportRef]
    boundary_rules: list[BoundaryRuleSummary]
    risk_map: list[RiskItem]
    dead_code_candidates: list[Finding]
    dependency_findings: list[Finding]
    limitations: list[str]


class FixOption(BaseModel):
    description: str
    minimal_patch: str | None = None
    safe: bool = False


class Remediation(BaseModel):
    finding: Finding
    classification: Literal["auto_safe", "review_needed", "blocking"]
    one_liner: str
    investigation_hints: list[str]
    fix_options: list[FixOption]
    safety_notes: list[str]
    related_findings: list[str]


class HallucinatedImport(BaseModel):
    import_name: str
    reason: str


class CyclePrediction(BaseModel):
    import_name: str
    cycle_path: list[str]


class BoundaryViolation(BaseModel):
    import_name: str
    rule: str
    reason: str


class VerifyResult(BaseModel):
    status: str = "not_implemented"
    file: str
    planned_imports: list[str]
    hallucinated: list[HallucinatedImport] = Field(default_factory=list)
    cycles_introduced: list[CyclePrediction] = Field(default_factory=list)
    boundary_violations: list[BoundaryViolation] = Field(default_factory=list)
    safe: list[str] = Field(default_factory=list)


class Classification(BaseModel):
    fingerprint: str
    decision: Literal["safe-auto", "review-needed", "manual-only"]
    rationale: str
