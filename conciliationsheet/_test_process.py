import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from services.file_processor import procesar_archivo

try:
    origenes, destinos = procesar_archivo(
        r"C:\Aldo\CONCILIATIONSHEETS\conciliationsheet\data\uploads\extracto_banco_nacion.xlsx",
        archivo_id=1,
        fuente="banco"
    )
    print(f"OK: {len(origenes)} origenes, {len(destinos)} destinos")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
