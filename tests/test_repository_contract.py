from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_artifacts_exist() -> None:
    expected = [
        "src/mindlink_etl_sprint3_oracle.py",
        "dags/mindlink_primeira_dag.py",
        "sql/01_ddl_mindlink_sprint3.sql",
        "sql/02_dml_mindlink_sprint3.sql",
        "docs/ARCHITECTURE.md",
        "docs/STATUS.md",
        "docs/EVIDENCE.md",
    ]

    for relative in expected:
        assert (ROOT / relative).is_file(), f"Artefato ausente: {relative}"


def test_no_credentials_are_versioned() -> None:
    forbidden_names = {".env", "tnsnames.ora", "cwallet.sso", "ewallet.p12"}
    tracked_candidates = {
        path.name.lower()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    assert forbidden_names.isdisjoint(tracked_candidates)
