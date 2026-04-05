"""
descargar_pdfs_articulos.py
============================
Descarga los PDFs de los artículos listados en base_articulos_muestra.csv.

Estrategias por plataforma:
  1. URL directa .pdf            → descarga inmediata
  2. OJS  (/article/view/{id})   → prueba /article/download/{id}/pdf
                                    si falla → parsea HTML buscando link PDF
  3. SciELO (sci_arttext)        → cambia a sci_pdf en la URL
  4. Redalyc / otros             → parsea HTML buscando link PDF

Salidas:
  pdfs_articulos/                → PDFs descargados
  descarga_pdfs_log.csv          → estado por artículo

Uso:
  python descargar_pdfs_articulos.py
  python descargar_pdfs_articulos.py --limite 100    (prueba con 100)
  python descargar_pdfs_articulos.py --reiniciar     (reprocesa errores)
"""

import argparse
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path("j:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO")
INPUT_CSV  = BASE_DIR / "base_articulos_muestra.csv"
PDF_DIR    = BASE_DIR / "pdfs_articulos"
OUT_LOG    = BASE_DIR / "descarga_pdfs_log.csv"

# ── Parámetros ─────────────────────────────────────────────────────────────────
DELAY_SEG        = 1.2       # pausa entre descargas (segundos)
DELAY_ERROR      = 3.0       # pausa adicional tras error
TIMEOUT          = 25        # timeout por request (segundos)
MAX_TAM_MB       = 30        # ignorar PDFs > 30 MB (probablemente no es un artículo)
MIN_TAM_BYTES    = 5_000     # ignorar respuestas < 5 KB (páginas de error disfrazadas)
MAX_REINTENTOS   = 2         # reintentos por artículo

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8,pt;q=0.7",
}

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from requests.adapters import HTTPAdapter

class _NoSSLAdapter(HTTPAdapter):
    """Adapter que deshabilita verificación SSL — necesario para servidores latinoamericanos."""
    def send(self, request, **kwargs):
        kwargs["verify"] = False
        return super().send(request, **kwargs)

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount("https://", _NoSSLAdapter())
SESSION.mount("http://",  _NoSSLAdapter())

# ── Nombre del archivo PDF ─────────────────────────────────────────────────────

def nombre_pdf(nro: int, row: dict) -> str:
    """Genera nombre de archivo único y legible para el PDF."""
    revista = re.sub(r"[^\w\s-]", "", str(row.get("revista", "rev")))[:30].strip()
    revista = re.sub(r"\s+", "_", revista)
    anio    = str(row.get("anio", "0000"))[:4]
    return f"{nro:05d}_{revista}_{anio}.pdf"


# ── Detección de PDF ───────────────────────────────────────────────────────────

def es_pdf(response: requests.Response) -> bool:
    """Verifica si la respuesta es un PDF real."""
    ct = response.headers.get("Content-Type", "").lower()
    if "pdf" in ct:
        return True
    if len(response.content) >= 4 and response.content[:4] == b"%PDF":
        return True
    return False


def tamanio_valido(content: bytes) -> bool:
    tam = len(content)
    return MIN_TAM_BYTES <= tam <= MAX_TAM_MB * 1024 * 1024


# ── Estrategias de descarga ────────────────────────────────────────────────────

def descargar_directo(url: str) -> tuple[bytes | None, str]:
    """Descarga una URL esperando PDF directo."""
    r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    if es_pdf(r) and tamanio_valido(r.content):
        return r.content, "pdf_directo"
    return None, f"no_pdf (Content-Type: {r.headers.get('Content-Type','')})"


def extraer_pdf_desde_html(url_pagina: str, html: str) -> str | None:
    """
    Busca el link de PDF en una página HTML.
    Retorna URL absoluta del PDF o None.
    """
    soup = BeautifulSoup(html, "lxml")

    # Prioridad 0: <meta name="citation_pdf_url"> — usado por OJS, Redalyc, etc.
    meta_pdf = soup.find("meta", {"name": "citation_pdf_url"})
    if meta_pdf:
        content = meta_pdf.get("content", "").strip()
        if content:
            return urljoin(url_pagina, content)

    patrones_texto = re.compile(
        r"\b(pdf|download|descargar|baixar|télécharger|full.?text|artigo completo)\b",
        re.IGNORECASE,
    )
    patrones_href = re.compile(r"\.pdf($|\?|#)", re.IGNORECASE)

    candidatos = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        texto = a.get_text(strip=True)
        href_abs = urljoin(url_pagina, href)

        # Prioridad 1: href termina en .pdf
        if patrones_href.search(href):
            candidatos.insert(0, href_abs)
            continue

        # Prioridad 2: texto del link menciona PDF
        if patrones_texto.search(texto):
            candidatos.append(href_abs)
            continue

        # Prioridad 3: href contiene /pdf/ o download
        if re.search(r"/(pdf|download|artigo)/", href, re.IGNORECASE):
            candidatos.append(href_abs)

    # Meta refresh o canonical en algunos portales
    for meta in soup.find_all("meta"):
        c = meta.get("content", "")
        if patrones_href.search(c):
            candidatos.append(urljoin(url_pagina, c.strip()))

    # Devolver el primer candidato único
    vistos = set()
    for c in candidatos:
        if c not in vistos and c.startswith("http"):
            vistos.add(c)
            return c

    return None


def estrategia_ojs(url: str) -> tuple[bytes | None, str]:
    """
    OJS: primero busca citation_pdf_url en el HTML, luego prueba rutas estándar.
    URL base: .../article/view/{article_id}[/{galley_id}]
    """
    # Paso 1: Cargar HTML del artículo y buscar citation_pdf_url
    try:
        r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            url_pdf = extraer_pdf_desde_html(url, r.text)
            if url_pdf and url_pdf != url:
                r2 = SESSION.get(url_pdf, timeout=TIMEOUT, allow_redirects=True)
                if r2.status_code == 200 and es_pdf(r2) and tamanio_valido(r2.content):
                    return r2.content, "ojs_citation_pdf_url"
    except Exception:
        pass

    # Paso 2: Extraer article_id y probar rutas estándar de descarga
    m = re.search(r"/article/view/(\d+)", url)
    if not m:
        return None, "ojs_id_no_encontrado"

    art_id   = m.group(1)
    base_url = url[:m.start()]

    candidatos_pdf = [
        f"{base_url}/article/download/{art_id}/pdf",
        f"{base_url}/article/download/{art_id}/1",
        f"{base_url}/article/view/{art_id}/pdf",
        f"{base_url}/article/view/{art_id}/1",
    ]

    for url_pdf in candidatos_pdf:
        try:
            r = SESSION.get(url_pdf, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and es_pdf(r) and tamanio_valido(r.content):
                return r.content, f"ojs_download ({url_pdf.split('/')[-1]})"
        except Exception:
            continue

    return None, "ojs_sin_pdf"


def estrategia_scielo(url: str) -> tuple[bytes | None, str]:
    """
    SciELO: cambia sci_arttext → sci_pdf y descarga.
    También prueba la URL de PDF directa de SciELO.
    """
    # 1. Cambiar parámetro script
    url_pdf_viewer = url.replace("sci_arttext", "sci_pdf")
    try:
        r = SESSION.get(url_pdf_viewer, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            if es_pdf(r) and tamanio_valido(r.content):
                return r.content, "scielo_sci_pdf"
            # sci_pdf puede devolver HTML con iframe del PDF
            url_pdf = extraer_pdf_desde_html(url_pdf_viewer, r.text)
            if url_pdf:
                r2 = SESSION.get(url_pdf, timeout=TIMEOUT, allow_redirects=True)
                if r2.status_code == 200 and es_pdf(r2) and tamanio_valido(r2.content):
                    return r2.content, "scielo_iframe_pdf"
    except Exception:
        pass

    # 2. Intentar URL directa de PDF en SciELO
    # Formato: https://www.scielo.br/j/{journal}/a/{code}/ → PDF en /pdf/{journal}/{vol}/{art}.pdf
    m = re.search(r"pid=(S[\w-]+)", url)
    if m:
        # Parsear la página original buscando link PDF
        try:
            r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                url_pdf = extraer_pdf_desde_html(url, r.text)
                if url_pdf:
                    r2 = SESSION.get(url_pdf, timeout=TIMEOUT, allow_redirects=True)
                    if r2.status_code == 200 and es_pdf(r2) and tamanio_valido(r2.content):
                        return r2.content, "scielo_html_parse"
        except Exception:
            pass

    return None, "scielo_sin_pdf"


def estrategia_html(url: str) -> tuple[bytes | None, str]:
    """Estrategia genérica: parsear HTML buscando link al PDF."""
    try:
        r = SESSION.get(url, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()

        # Si ya es PDF
        if es_pdf(r) and tamanio_valido(r.content):
            return r.content, "html_directo_es_pdf"

        # Buscar en HTML
        url_pdf = extraer_pdf_desde_html(url, r.text)
        if url_pdf and url_pdf != url:
            r2 = SESSION.get(url_pdf, timeout=TIMEOUT, allow_redirects=True)
            if r2.status_code == 200 and es_pdf(r2) and tamanio_valido(r2.content):
                return r2.content, "html_parse"

    except Exception as e:
        return None, f"html_error: {e}"

    return None, "html_sin_pdf"


# ── Despachador principal ──────────────────────────────────────────────────────

def descargar_pdf(url: str) -> tuple[bytes | None, str]:
    """Selecciona la estrategia correcta según el patrón de la URL."""
    url = url.strip()

    # PDF directo
    if re.search(r"\.pdf($|\?|#)", url, re.IGNORECASE):
        return descargar_directo(url)

    # SciELO
    if "scielo" in url.lower() and "sci_arttext" in url:
        return estrategia_scielo(url)

    # OJS
    if "/article/view/" in url:
        return estrategia_ojs(url)

    # Genérico (Redalyc, otros)
    return estrategia_html(url)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite",    type=int, default=0,      help="Límite de artículos (0=todos)")
    parser.add_argument("--reiniciar", action="store_true",      help="Reprocesar artículos con error")
    args = parser.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("  DESCARGA DE PDFs — BASE ARTÍCULOS MUESTRA")
    print(f"  Fecha  : {datetime.today().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Destino: {PDF_DIR}")
    print("=" * 72)

    # ── Cargar base ────────────────────────────────────────────────────────────
    df = pd.read_csv(INPUT_CSV, sep=";", encoding="utf-8-sig", index_col="nro")
    df = df[df["url_fulltext"].notna() & (df["url_fulltext"] != "")]

    # ── Cargar progreso anterior ───────────────────────────────────────────────
    log_previo: dict[int, dict] = {}
    if OUT_LOG.exists():
        df_log = pd.read_csv(OUT_LOG, sep=";", encoding="utf-8-sig")
        if "nro" in df_log.columns:
            for _, r in df_log.iterrows():
                log_previo[int(r["nro"])] = r.to_dict()

    # Decidir qué procesar
    def necesita_procesar(nro: int) -> bool:
        if nro not in log_previo:
            return True                          # nunca procesado
        estado = log_previo[nro].get("estado", "")
        if args.reiniciar and estado != "OK":
            return True                          # reprocesar errores
        return estado != "OK"                    # procesar si no fue OK

    indices = [nro for nro in df.index if necesita_procesar(nro)]
    if args.limite > 0:
        indices = indices[:args.limite]

    ya_ok = sum(1 for nro in df.index if log_previo.get(nro, {}).get("estado") == "OK")
    print(f"\n  Total artículos   : {len(df)}")
    print(f"  Ya descargados    : {ya_ok}")
    print(f"  A procesar ahora  : {len(indices)}")

    if not indices:
        print("\n  Nada que descargar.")
        return

    # ── Bucle de descarga ──────────────────────────────────────────────────────
    log_acumulado = {**log_previo}  # conservar historial
    ok = err = 0

    print(f"\n  {'#':>5}  {'Archivo':<40}  {'Estrategia':<22}  Estado")
    print(f"  {'─'*68}")

    for i, nro in enumerate(indices, 1):
        row       = df.loc[nro].to_dict()
        url       = str(row["url_fulltext"]).strip()
        nombre    = nombre_pdf(nro, row)
        ruta_dest = PDF_DIR / nombre

        contenido = None
        estrategia_usada = ""
        estado = ""

        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                contenido, estrategia_usada = descargar_pdf(url)
                break
            except requests.exceptions.SSLError:
                # Reintentar sin verificar SSL (algunos servidores latinoamericanos)
                SESSION.verify = False
                try:
                    contenido, estrategia_usada = descargar_pdf(url)
                    estrategia_usada += " (ssl_off)"
                except Exception as e:
                    estrategia_usada = f"ssl_error: {e}"
                SESSION.verify = True
                break
            except requests.exceptions.ConnectionError as e:
                if intento < MAX_REINTENTOS:
                    time.sleep(DELAY_ERROR)
                else:
                    estrategia_usada = f"conn_error: {e}"
            except requests.exceptions.Timeout:
                if intento < MAX_REINTENTOS:
                    time.sleep(DELAY_ERROR)
                else:
                    estrategia_usada = "timeout"
            except Exception as e:
                estrategia_usada = f"error: {e}"
                break

        if contenido:
            ruta_dest.write_bytes(contenido)
            tam_kb = len(contenido) // 1024
            estado = "OK"
            ok += 1
            icono = "✅"
        else:
            estado = f"FALLO: {estrategia_usada}"
            tam_kb = 0
            err += 1
            icono = "❌"

        log_acumulado[nro] = {
            "nro":              nro,
            "nombre_archivo":   nombre,
            "revista":          row.get("revista", ""),
            "pais":             row.get("pais", ""),
            "macroarea":        row.get("macroarea", ""),
            "anio":             row.get("anio", ""),
            "url_fulltext":     url,
            "estrategia":       estrategia_usada,
            "tam_kb":           tam_kb,
            "estado":           estado,
            "timestamp":        datetime.now().isoformat(),
        }

        print(f"  {nro:>5}  {nombre:<40}  {estrategia_usada:<22}  {icono} {tam_kb} KB")

        # Guardar log incremental cada 20 artículos
        if i % 20 == 0:
            pd.DataFrame(list(log_acumulado.values())).to_csv(
                OUT_LOG, sep=";", encoding="utf-8-sig", index=False
            )
            pct_ok = ok / (ok + err) * 100 if (ok + err) > 0 else 0
            print(f"  {'─'*68}")
            print(f"  [Progreso: {i}/{len(indices)} — ✅ {ok}  ❌ {err}  ({pct_ok:.0f}% éxito)]")
            print(f"  {'─'*68}")

        time.sleep(DELAY_SEG)

    # ── Guardado final ─────────────────────────────────────────────────────────
    df_log_final = pd.DataFrame(list(log_acumulado.values()))
    df_log_final = df_log_final.sort_values("nro").reset_index(drop=True)
    df_log_final.to_csv(OUT_LOG, sep=";", encoding="utf-8-sig", index=False)

    # ── Resumen ────────────────────────────────────────────────────────────────
    total_ok  = (df_log_final["estado"] == "OK").sum()
    total_err = (df_log_final["estado"] != "OK").sum()
    pct       = total_ok / len(df_log_final) * 100

    print(f"\n{'='*72}")
    print("  RESUMEN FINAL")
    print(f"{'='*72}")
    print(f"  Descargados  : {total_ok} ({pct:.1f}%)")
    print(f"  Fallidos     : {total_err}")
    tam_total_mb = df_log_final.loc[df_log_final["estado"]=="OK","tam_kb"].sum() / 1024
    print(f"  Tamaño total : {tam_total_mb:.1f} MB")

    if total_ok > 0:
        print("\n  Por estrategia:")
        for est, cnt in (df_log_final[df_log_final["estado"]=="OK"]
                         ["estrategia"].value_counts().items()):
            print(f"    {est:<35} {cnt:>5}")

    if total_err > 0:
        print("\n  Tipos de fallo:")
        fallos = df_log_final[df_log_final["estado"] != "OK"]["estado"]
        fallos_agrupados = fallos.str.extract(r"FALLO: (\w+)")[0].value_counts()
        for tip, cnt in fallos_agrupados.items():
            print(f"    {tip:<35} {cnt:>5}")

    print(f"\n  PDFs en: {PDF_DIR}")
    print(f"  Log en : {OUT_LOG}")
    print("=" * 72)
    print("  Completado.")


if __name__ == "__main__":
    main()
