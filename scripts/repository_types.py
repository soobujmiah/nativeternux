#!/usr/bin/env python3
"""Canonical repository type taxonomy for the SKB new-repository standard.

This module is the single source of the type enum introduced by
``standards/new-repository-standard.md`` and documented in
``standards/repository-types/README.md``. Both ``tools/bootstrap_repo.py`` and
``scripts/validate_new_repository.py`` import it, so the documented taxonomy and
the enforced taxonomy cannot drift apart.

The enum is the eleven profiles originally named in ``standards/project-factory.md``
§1, adopted rather than replaced. Adding a type requires a profile document under
``standards/repository-types/`` plus an entry here.

No third-party dependencies: this module must import cleanly in CI before PyYAML
is installed, because the bootstrap and readiness paths both use it early.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# Canonical enum
# --------------------------------------------------------------------------

TYPES: tuple[str, ...] = (
    "android-app",
    "backend-service",
    "web-app",
    "cli-tool",
    "library-sdk",
    "ai-ml",
    "data-extraction",
    "automation",
    "creative-tool",
    "knowledge-system",
    "research",
)

#: Types whose product is installed and used on a physical device.
DEVICE_VALIDATED: tuple[str, ...] = ("android-app", "creative-tool", "ai-ml")

#: Requirement sets per type. Values are REQUIRED / RECOMMENDED / OPTIONAL /
#: NOT_APPLICABLE, matching the vocabulary used in the type profiles.
REQUIREMENTS: dict[str, dict[str, str]] = {
    "android-app": {
        "security_md": "REQUIRED",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "REQUIRED",
        "phases": "RECOMMENDED",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "backend-service": {
        "security_md": "REQUIRED",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "REQUIRED",
        "phases": "RECOMMENDED",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "web-app": {
        "security_md": "REQUIRED_WHEN_DATA",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "RECOMMENDED",
        "phases": "OPTIONAL",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "cli-tool": {
        "security_md": "REQUIRED_WHEN_PRIVILEGED",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "RECOMMENDED",
        "phases": "OPTIONAL",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "library-sdk": {
        "security_md": "REQUIRED_WHEN_DATA",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "RECOMMENDED",
        "phases": "OPTIONAL",
        "changelog": "REQUIRED",
        "license": "REQUIRED",
    },
    "ai-ml": {
        "security_md": "REQUIRED",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "REQUIRED",
        "phases": "RECOMMENDED",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "data-extraction": {
        "security_md": "REQUIRED",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "REQUIRED",
        "phases": "RECOMMENDED",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "automation": {
        "security_md": "REQUIRED",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "RECOMMENDED",
        "phases": "OPTIONAL",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "creative-tool": {
        "security_md": "REQUIRED_WHEN_DATA",
        "tests": "REQUIRED",
        "docs_dirs": "REQUIRED",
        "adrs": "REQUIRED",
        "phases": "RECOMMENDED",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "knowledge-system": {
        "security_md": "REQUIRED_WHEN_PRIVATE_CONTEXT",
        "tests": "REQUIRED_WHEN_VALIDATORS_EXIST",
        "docs_dirs": "REQUIRED",
        "adrs": "RECOMMENDED",
        "phases": "NOT_APPLICABLE",
        "changelog": "RECOMMENDED",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
    "research": {
        "security_md": "REQUIRED_WHEN_PRIVILEGED",
        "tests": "REQUIRED_WHEN_REPRODUCIBLE",
        "docs_dirs": "REQUIRED",
        "adrs": "OPTIONAL",
        "phases": "NOT_APPLICABLE",
        "changelog": "OPTIONAL",
        "license": "REQUIRED_WHEN_CHOSEN",
    },
}

#: Build/test semantics per type. These strings are surfaced by the readiness
#: validator so an agent reads the rule instead of copying a neighbour.
BUILD_TEST: dict[str, dict[str, str]] = {
    "android-app": {
        "build": "Assembly of the declared installable artefact by the authoritative CI workflow.",
        "test": "Unit, widget, or instrumented suite that CI can run.",
        "unknown": "No assembly step configured (build) or no test step exists (test).",
        "observe": "Observe the authoritative native build via the run observer rather than re-running it.",
    },
    "backend-service": {
        "build": "Compilation/typecheck plus production artefact construction, including schema/migration validation where the service owns a schema.",
        "test": "Unit suite plus the integration or contract suite CI can actually run; excluded suites must be declared.",
        "unknown": "No build step configured, or no test framework configured.",
        "observe": "Observe a long deployment build rather than duplicating it in the sync workflow.",
    },
    "web-app": {
        "build": "Production build or static export that produces the deliverable directory.",
        "test": "Unit/component suite, plus E2E where declared as the signal.",
        "unknown": "No build step, or a static site with no suite (test stays unknown).",
        "observe": "Where the hosting platform builds the site, observe that build conclusion.",
    },
    "cli-tool": {
        "build": "Packaging or install-and-run smoke build; a pure syntax check may be nominated only if declared as such.",
        "test": "Unit suite plus at least one end-to-end invocation test.",
        "unknown": "No packaging step, or no test framework (common for small utilities).",
        "observe": "Not normally required.",
    },
    "library-sdk": {
        "build": "Packaging: produce the distributable artefact with a reproducible step.",
        "test": "Unit suite plus API-surface/contract tests that catch accidental breaking changes.",
        "unknown": "No packaging step, or no suite configured.",
        "observe": "Not normally required.",
    },
    "ai-ml": {
        "build": "Environment/artefact construction; large artefact preparation is declared outside the signal unless CI performs it reproducibly.",
        "test": "Deterministic unit suite plus a bounded, reproducible inference smoke test. Non-deterministic generation quality is never a test signal.",
        "unknown": "No build/packaging step, or no deterministic suite.",
        "observe": "Record training and device-only evaluation as evidence, not as the test signal.",
    },
    "data-extraction": {
        "build": "Packaging/compilation plus schema and contract validation.",
        "test": "Parser and schema suite against recorded fixtures.",
        "unknown": "No fixtures or suite yet; never test against the live source.",
        "observe": "Record live extraction runs as evidence, not as the test signal.",
    },
    "automation": {
        "build": "Static validation: syntax, lint, config validation, and a clean dry-run.",
        "test": "Unit suite plus idempotency tests against a sandbox or fake.",
        "unknown": "No static validation/dry-run configured, or no suite configured.",
        "observe": "Real privileged runs are operator-authorised evidence, never CI gates.",
    },
    "creative-tool": {
        "build": "Build of the application or shell (core plus shell, as declared).",
        "test": "Deterministic suite: document-model logic plus widget/render tests. Unstable golden suites are declared separately.",
        "unknown": "No build step, or no deterministic suite.",
        "observe": "Device validation of interaction and fidelity is evidence, not a CI test.",
    },
    "knowledge-system": {
        "build": "Structural validation: link integrity, required contract files, schema validity, contract invariants.",
        "test": "The validator suite, if one exists.",
        "unknown": "Documentation-only repositories with no validators are unknown by policy. A report-only check is unknown, never passed.",
        "observe": "Not normally required.",
    },
    "research": {
        "build": "The reproduction or artefact-build step that runs the harness to completion.",
        "test": "A reproducibility or checksum check within declared tolerance.",
        "unknown": "No reproduction step, or a prose-only findings repository.",
        "observe": "Benchmarks are recorded as evidence with their conditions.",
    },
}

#: Documentation directories created at bootstrap, per type.
DOCS_DIRS: dict[str, tuple[str, ...]] = {
    "android-app": ("product", "architecture", "development", "testing", "security", "operations"),
    "backend-service": ("product", "architecture", "development", "testing", "security", "operations"),
    "web-app": ("product", "architecture", "development", "testing"),
    "cli-tool": ("product", "architecture", "development", "testing"),
    "library-sdk": ("product", "architecture", "development", "testing"),
    "ai-ml": ("product", "architecture", "development", "testing", "security"),
    "data-extraction": ("product", "architecture", "development", "testing", "security"),
    "automation": ("product", "architecture", "development", "testing", "security", "operations"),
    "creative-tool": ("product", "architecture", "design", "development", "testing"),
    "knowledge-system": ("architecture", "development"),
    "research": ("research",),
}

#: Types for which a SECURITY.md is installed unconditionally at bootstrap.
SECURITY_REQUIRED: tuple[str, ...] = (
    "android-app",
    "backend-service",
    "ai-ml",
    "data-extraction",
    "automation",
)


def is_valid_type(value: str | None) -> bool:
    """True when *value* is one of the canonical enum values."""
    return isinstance(value, str) and value in TYPES


def normalize_type(value: str | None) -> str | None:
    """Return the canonical slug for *value*, or None when it is not a type."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower().replace("_", "-").replace(" ", "-")
    return candidate if candidate in TYPES else None


def requirements_for(value: str | None) -> dict[str, str]:
    """Requirement set for a type; neutral defaults for an unclassified repository."""
    slug = normalize_type(value)
    if slug is None:
        return {
            "security_md": "REQUIRED_WHEN_DATA",
            "tests": "REQUIRED",
            "docs_dirs": "REQUIRED",
            "adrs": "RECOMMENDED",
            "phases": "OPTIONAL",
            "changelog": "RECOMMENDED",
            "license": "REQUIRED_WHEN_CHOSEN",
        }
    return REQUIREMENTS[slug]


def build_test_for(value: str | None) -> dict[str, str]:
    slug = normalize_type(value)
    if slug is None:
        return {
            "build": "Not yet defined: the repository has no classified type, so build semantics are undetermined.",
            "test": "Not yet defined: the repository has no classified type, so test semantics are undetermined.",
            "unknown": "Unknown until a type is declared and checks are configured.",
            "observe": "Decide after classification.",
        }
    return BUILD_TEST[slug]


def docs_dirs_for(value: str | None) -> tuple[str, ...]:
    slug = normalize_type(value)
    return DOCS_DIRS.get(slug or "", ("product", "architecture", "development", "testing"))


def security_required_for(value: str | None) -> bool:
    return normalize_type(value) in SECURITY_REQUIRED


def describe_type(value: str | None) -> str:
    slug = normalize_type(value)
    if slug is None:
        return "unclassified (no canonical type declared)"
    return slug
