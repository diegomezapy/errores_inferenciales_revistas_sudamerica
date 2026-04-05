# config.py
from pathlib import Path

# Cambia esta línea por tu ruta real (puedes dejarla así si ya estás trabajando ahí)
BASE_DIR = Path("G:/Mi unidad/DECENA_FACEN/REPO")

# Rutas relativas correctas (¡así sí funciona!)
DATA_DIR = BASE_DIR / "data"
RAW_PDF_DIR = DATA_DIR / "raw_pdf"

# Crear carpetas si no existen
DATA_DIR.mkdir(exist_ok=True)
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Años y configuración general
YEAR_START = 2020
YEAR_END = 2024
REQUEST_DELAY = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
}