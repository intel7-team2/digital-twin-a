from pathlib import Path
import sys
import re
import pypdfium2 as pdfium
from pypdf import PdfReader

base = Path(__file__).resolve().parents[1]
stem=sys.argv[1] if len(sys.argv)>1 else 'plan_v0.15'
out = base / '.qa' / stem
out.mkdir(parents=True, exist_ok=True)
doc = pdfium.PdfDocument(base / (stem+'.pdf'))
for i in range(len(doc)):
    page = doc[i]
    page.render(scale=1.6).to_pil().save(out / f'page-{i+1}.png')
    page.close()
doc.close()
reader = PdfReader(base / (stem+'.pdf'))
print('Pages:', len(reader.pages))
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    footer = bool(re.search(rf'-\s*{i+1}\s*-\s*$', text))
    print(i+1, 'chars:', len(text), 'footer:', footer, 'replacement:', '\ufffd' in text)
    if not footer or '\ufffd' in text:
        raise ValueError(f'Invalid page text or footer on page {i+1}')
