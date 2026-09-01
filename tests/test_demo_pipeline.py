from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
ETL = REPO_ROOT / "src" / "mindlink_etl_sprint3_oracle.py"


def test_demo_pipeline_end_to_end(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ETL), "--demo", "--demo-linhas", "300"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "MindLink ETL concluído com sucesso" in result.stdout

    staging = tmp_path / "data" / "processed" / "stg_mindlink_internacoes_python.csv"
    comorbidades = tmp_path / "data" / "processed" / "stg_mindlink_comorbidades_python.csv"
    evidencia = tmp_path / "data" / "evidence" / "mindlink_resumo_etl.csv"

    assert staging.exists()
    assert comorbidades.exists()
    assert evidencia.exists()

    df_staging = pd.read_csv(staging, dtype={"CODIGO_IBGE": str, "CNES": str})
    assert not df_staging.empty
    assert {
        "COMPETENCIA",
        "CODIGO_IBGE",
        "CNES",
        "CID_PRINCIPAL",
        "QTD_INTERNACOES",
        "DIAS_PERMANENCIA",
        "VALOR_TOTAL",
        "QTD_OBITOS",
    }.issubset(df_staging.columns)

    assert df_staging["COMPETENCIA"].between(202401, 202512).all()
    assert (df_staging["QTD_INTERNACOES"] > 0).all()
    assert (df_staging["DIAS_PERMANENCIA"] >= 0).all()
    assert (df_staging["VALOR_TOTAL"] >= 0).all()
