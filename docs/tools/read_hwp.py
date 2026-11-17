"""Read-only extraction of HWP 5 OLE streams and paragraph text."""
import struct
import sys
import zlib
from pathlib import Path
from PIL import Image
import io


class Compound:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.size = 1 << struct.unpack_from('<H', self.data, 30)[0]
        self.mini_size = 1 << struct.unpack_from('<H', self.data, 32)[0]
        difat = list(struct.unpack_from('<109I', self.data, 76))
        sector, count = struct.unpack_from('<II', self.data, 68)
        for _ in range(count):
            more = struct.unpack('<'+'I'*(self.size//4), self.sector(sector))
            difat.extend(more[:-1])
            sector = more[-1]
        self.fat = []
        for sid in difat:
            if sid < 0xfffffffa:
                self.fat.extend(struct.unpack('<'+'I'*(self.size//4), self.sector(sid)))
        directory = self.chain(struct.unpack_from('<I', self.data, 48)[0])
        self.entries = []
        for n in range(0, len(directory), 128):
            e = directory[n:n+128]
            length = struct.unpack_from('<H', e, 64)[0]
            self.entries.append({'name':e[:max(0,length-2)].decode('utf-16-le'),
                                 'type':e[66], 'start':struct.unpack_from('<I',e,116)[0],
                                 'size':struct.unpack_from('<Q',e,120)[0]})
        root = self.entries[0]
        self.mini = self.chain(root['start'])[:root['size']]
        mf, mc = struct.unpack_from('<II', self.data, 60)
        mbytes = self.chain(mf)[:mc*self.size]
        self.minifat = list(struct.unpack('<'+'I'*(len(mbytes)//4), mbytes)) if mbytes else []

    def sector(self, sid):
        return self.data[(sid+1)*self.size:(sid+2)*self.size]

    def chain(self, sid, mini=False):
        chunks, seen = [], set()
        fat = self.minifat if mini else self.fat
        while sid < 0xfffffffa:
            if sid in seen:
                raise ValueError('cyclic chain')
            seen.add(sid)
            chunks.append(self.mini[sid*self.mini_size:(sid+1)*self.mini_size] if mini else self.sector(sid))
            sid = fat[sid]
        return b''.join(chunks)

    def read(self, entry):
        return self.chain(entry['start'], mini=entry['size']<4096)[:entry['size']]


def main():
    doc = Compound(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True,exist_ok=True)
    header = next(e for e in doc.entries if e['name']=='FileHeader')
    flags = struct.unpack_from('<I',doc.read(header),36)[0]
    lines = []
    for e in doc.entries:
        if e['type']!=2:
            continue
        print(e['name'],e['size'])
        data = doc.read(e)
        if e['name']=='PrvText':
            (out/'preview.txt').write_text(data.decode('utf-16-le'),encoding='utf-8')
        elif e['name']=='PrvImage':
            Image.open(io.BytesIO(data)).save(out/'preview.png')
        elif e['name'].startswith('Section'):
            if flags & 1:
                data=zlib.decompress(data,-15)
            p=0
            while p+4<=len(data):
                rec=struct.unpack_from('<I',data,p)[0];p+=4
                tag,size=rec&1023,rec>>20
                if size==4095:
                    size=struct.unpack_from('<I',data,p)[0];p+=4
                payload=data[p:p+size];p+=size
                if tag==67:
                    words=struct.unpack('<'+'H'*(len(payload)//2),payload)
                    text=[];i=0
                    while i<len(words):
                        c=words[i]
                        if c in (1,2,3,4,5,6,7,8,11,12,14,15,16,17,18,19,20,21,22,23):i+=8;continue
                        if c>=32 or c in (9,10,13):text.append(c)
                        i+=1
                    lines.append(struct.pack('<'+'H'*len(text),*text).decode('utf-16-le',errors='replace'))
    text='\n'.join(lines)
    (out/'body.txt').write_text(text,encoding='utf-8')
    print('\nBODY\n'+text)


if __name__=='__main__':main()
