from pathlib import Path
import sys
import pypdfium2 as pdfium
from pypdf import PdfReader

base = Path(__file__).resolve().parents[1]
stem=sys.argv[1] if len(sys.argv)>1 else 'plan_v0.3'
out = base / '.qa' / stem
out.mkdir(parents=True, exist_ok=True)
for i in range(len(PdfReader(base / (stem+'.pdf')).pages)):
    doc = pdfium.PdfDocument(base / (stem+'.pdf'))
    page = doc[i]
    page.render(scale=1.6).to_pil().save(out / f'page-{i+1}.png')
    page.close()
    doc.close()
reader = PdfReader(base / (stem+'.pdf'))
print('Pages:', len(reader.pages))
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    print(i+1, 'chars:', len(text), 'footer:', f'{i+1} / 6' in text, 'replacement:', '\ufffd' in text)
