from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
SOURCE_DIR = WORKSPACE_ROOT / "infoRocolectada"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

FILES_TO_COPY = [
    "datos_abiertos_EV_colombia_realista.xlsx",
    "infraestructura_generacion_86_registros.xlsx",
    "PARATEC_Phidráulica_18-05-2026.xlsx",
    "base_baterias_EV_red_electrica.xlsx",
    "base_realista_baterias_EV_APA7.xlsx",
]


def copy_raw_files() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for file_name in FILES_TO_COPY:
        source_path = SOURCE_DIR / file_name
        target_path = RAW_DATA_DIR / file_name
        if not source_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo fuente: {source_path}")
        shutil.copy2(source_path, target_path)
        print(f"Copiado: {source_path.name}")


if __name__ == "__main__":
    copy_raw_files()
