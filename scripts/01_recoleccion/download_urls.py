import os
import requests
import re
from urllib.parse import urlparse
import time

raw_text = '''
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-05-2021-0047/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-02-2022-0043/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-01-2022-0015/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-10-2021-0214/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-08-2021-0158/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-04-2021-0036/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-11-2020-0433/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-02-2020-0044/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-07-2021-0118/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-09-2021-0178/full/pdf](https://www.google.com/search?q=...)
[https://www.emerald.com/insight/content/doi/10.1108/JEFAS-12-2020-0487/full/pdf](https://www.google.com/search?q=...)
[https://www.sciencedirect.com/science/article/pii/S003474502300050X/pdfft?isDTMRedir=true&download=true](...)
[https://www.sciencedirect.com/science/article/pii/S0034745023000122/pdfft?isDTMRedir=true&download=true](...)
[https://www.sciencedirect.com/science/article/pii/S0034745022001502/pdfft?isDTMRedir=true&download=true](...)
[https://www.sciencedirect.com/science/article/pii/S0034745023000857/pdfft?isDTMRedir=true&download=true](...)
[https://www.sciencedirect.com/science/article/pii/S0034745022001101/pdfft?isDTMRedir=true&download=true](...)
[https://estudiosdeeconomia.uchile.cl/index.php/EDE/article/download/70123/73258](...)
[https://estudiosdeeconomia.uchile.cl/index.php/EDE/article/download/68901/71540](...)
[https://estudiosdeeconomia.uchile.cl/index.php/EDE/article/download/71005/74100](...)
[https://journal.universidadean.edu.co/index.php/Revista/article/view/2976/2959](...)
[https://journal.universidadean.edu.co/index.php/Revista/article/view/1915/1938](...)
[https://journal.universidadean.edu.co/index.php/Revista/article/view/518/504](...)
[https://www.scielo.br/j/resr/a/HDhfTtTQ8LRyM6LG4qsN6wN/?lang=pt&format=pdf](...)
[https://www.scielo.br/j/resr/a/FCzmmPD8vvpFpgLSQHfrXKh/?format=pdf&lang=pt](...)
[https://www.scielo.br/j/resr/a/J49pFnnbhzN6MBYkWssB8RS/?format=pdf&lang=pt](...)
[https://www.scielo.br/j/resr/a/fggH8MjD8Cpf8nGK9sY59PQ/?format=pdf&lang=pt](...)
[https://www.scielo.br/j/resr/a/VKjSWQQrXqLwcXjJmpDsFTF/?format=pdf&lang=pt](...)
[https://www.scielo.br/j/resr/a/q9khtZfdD4sqm7P99fRbN3h/?format=pdf&lang=pt](...)
[https://www.scielo.br/j/resr/a/G6jRyxNvtpYs73rQdL7DvCm/?format=pdf&lang=pt](...)
[https://rasp.msal.gov.ar/index.php/rasp/article/view/754/768](...)
[http://www.scielo.edu.uy/pdf/agro/v16n2/v16n2a08.pdf](...)
[http://www.scielo.edu.uy/pdf/agro/v19n2/v19n2a07.pdf](...)
[https://www.scielo.org.mx/pdf/fn/v36/0187-7372-fn-v36-e2388.pdf](...)
[https://www.scielo.org.mx/pdf/fn/v22n44/v22n44a2.pdf](...)
[https://www.scielo.org.mx/scielo.php?script=sci_pdf&pid=S0187-73722025000100106&lng=es&nrm=iso](...)
[https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S0187-73722022000100121](...)
[https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S2683-14652022000100071](...)
[https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S0187-69612016000100006](...)
[http://scielo.iics.una.py/scielo.php?script=sci_arttext&pid=S1816-89492021000200051](...)
[https://scielo.iics.una.py/scielo.php?script=sci_arttext&pid=S1816-89492020000200037](...)
[https://scielo.iics.una.py/scielo.php?script=sci_arttext&pid=S1816-89492019000100025](...)
[https://scielo.iics.una.py/scielo.php?script=sci_arttext&pid=S1816-89492015000200005](...)
[https://www.scielo.cl/pdf/ru/n47/0717-5051-ru-47-00161.pdf](...)
[https://www.scielo.cl/pdf/caledu/n50/0718-4565-caledu-50-284.pdf](...)
[https://www.scielo.cl/pdf/ede/v40n2/art04.pdf](...)
[https://mail.revistachilenadepediatria.cl/index.php/rchped/article/download/2617/3186](...)
[https://www.scielo.br/j/jaos/a/ygnxVLVfDvRv88BWdXFTPkq/?format=pdf&lang=en](...)
[https://www.scielo.br/j/abd/a/WVcqhwZHkQqSw7fYRzSHyqB/?lang=en&format=pdf](...)
[https://www.scielo.br/j/rbccv/a/mDkqJWSPwxNw5r3FdccWWvR/?format=pdf&lang=en](...)
[https://www.scielo.br/j/asagr/a/v9xbXfYZWD6b53CwPyfxJKG/?format=pdf&lang=en](...)
[https://www.cabidigitallibrary.org/doi/pdf/10.5555/20230029263](...)
[https://www.scielo.br/j/rmat/a/T35K9dM8ZzZY6f8tHZshrPr/?format=pdf&lang=en](...)
[http://www.scielo.org.co/pdf/rmri/v31n1/0122-0667-rmri-31-01-47.pdf](...)
[http://www.scielo.org.co/pdf/rcg/v33n1/0120-9957-rcg-33-01-00016.pdf](...)
[http://www.scielo.org.co/pdf/aven/v39n2/0121-4500-aven-39-02-207.pdf](...)
[http://www.scielo.org.co/pdf/unmed/v63n1/2011-0839-unmed-63-01-92.pdf](...)
[http://www.scielo.org.co/pdf/cesm/v26n1/v26n1a03.pdf](...)
[http://www.scielo.org.pe/pdf/comunica/v10n1/a07v10n1.pdf](...)
[http://www.scielo.org.pe/pdf/rcudep/v22n1/2227-1465-rcudep-22-01-71.pdf](...)
[http://www.scielo.org.pe/pdf/kaw/n12/2709-3689-kaw-12-A-013.pdf](...)
[https://mail.comunicacionunap.com/index.php/rev/article/download/571/348/3030](...)
[http://www.scielo.org.pe/pdf/comunica/v6n1/a03v6n1.pdf](...)
[https://www.scielo.br/j/resr/grid](...)
[https://journal.universidadean.edu.co/index.php/Revista/issue/archive](...)
[https://revistas.unne.edu.ar/index.php/rfce/issue/archive](...)
[https://revistas.uta.edu.ec/erevista/index.php/bcoyu/issue/archive](...)
[https://rasp.msal.gov.ar/index.php/rasp/issue/archive](...)
[http://scielo.iics.una.py/scielo.php?script=sci_issues&pid=1816-8949&lng=es&nrm=iso](...)
[https://www.cnps.cl/index.php/cnps/issue/archive](...)
[https://www.scielo.br/j/cenf/grid](...)
[http://www.scielo.edu.uy/scielo.php?script=sci_issues&pid=2301-1548&lng=es&nrm=iso](...)
[http://revistas.unilasallista.edu.co/index.php/pl/issue/archive](...)
[https://bibliotecadigital.univalle.edu.co/handle/10893/1359](...)
[https://www.scielo.org.mx/scielo.php?script=sci_issues&pid=0187-7372&lng=es&nrm=iso](...)
[https://dialnet.unirioja.es/servlet/revista?codigo=5275](...)
[https://www.scielo.cl/scielo.php?script=sci_issues&pid=0718-7378&lng=es&nrm=iso](...)
'''

# We will just parse each line and extract what's inside the FIRST pair of brackets or directly starting with http
lines = raw_text.strip().split('\n')
urls = []
for line in lines:
    match = re.search(r'\[(http[^\]]+)\]', line)
    if match:
        urls.append(match.group(1))

output_dir = r"g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\articulos_descargados"
os.makedirs(output_dir, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def get_filename(url, ctype, index):
    ext = ".html"
    if "pdf" in ctype.lower() or url.lower().endswith(".pdf") or "download" in url.lower() or "pdfft" in url.lower() or "format=pdf" in url.lower():
        ext = ".pdf"
    
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path)
    if not basename:
        basename = "document"
        
    if "doi" in url and "emerald" in url:
        basename = url.split('/')[-3] if "full" in url else url.split('/')[-1]
    
    if "scielo" in url and "pid=" in parsed.query:
        pid = re.search(r'pid=([^&]+)', parsed.query)
        if pid:
            basename = pid.group(1)
            
    # fallback
    if len(basename) < 4 or basename in ("pdf", "download", "full", "view", "article"):
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) >= 2:
            basename = f"{parts[-2]}_{parts[-1]}"
            if basename.endswith('full_pdf'):
                basename = parts[-3] if len(parts) >= 3 else basename
            
    basename = re.sub(r'[\\/*?:"<>|]', "", basename)
    if not basename.endswith(ext):
        basename += ext
    
    return f"{index:03d}_{basename}"

results = []

for i, url in enumerate(urls, 1):
    try:
        print(f"[{i}/{len(urls)}] GET {url}")
        res = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        if res.status_code == 200:
            ctype = res.headers.get('Content-Type', '')
            fname = get_filename(url, ctype, i)
            fpath = os.path.join(output_dir, fname)
            
            with open(fpath, 'wb') as f:
                f.write(res.content)
            
            size_kb = len(res.content) // 1024
            print(f"  -> Saved {fname} (Size: {size_kb} KB)")
            results.append((url, "Success", fname))
        else:
            print(f"  -> Failed with status {res.status_code}")
            results.append((url, f"Failed: {res.status_code}", ""))
            
    except Exception as e:
        print(f"  -> Error: {e}")
        results.append((url, f"Error: {str(e)}", ""))
    
    time.sleep(1) # Be polite

# Write a log file
log_path = os.path.join(output_dir, "download_log.txt")
with open(log_path, 'w', encoding='utf-8') as f:
    for url, status, fname in results:
        f.write(f"{status}\t{fname}\t{url}\n")
        
print(f"Finished. Log saved to {log_path}")
