"""Apply narrowly verified Windows CRT fixes to a NEW copy of the release."""
import hashlib
import json
import pathlib
import sys
from inspect_pe import PE

root = pathlib.Path(sys.argv[1])
manifest = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8-sig'))
expected = {entry['path'].replace('\\', '/'): entry['sha256'].lower() for entry in manifest['binaries']}
date_old = b'%-d.%-m.%Y %H:%M:%S\0'
date_new = b'%#d.%#m.%Y %H:%M:%S\0'
records = []
for relative in ('OpenGothic/build/opengothic/Gothic2Notr.exe', 'OpenGothic/ai_bridge/storygraph/build/storygraph.exe'):
    path = root / relative
    pe = PE(path)
    original = bytes(pe.data)
    before = hashlib.sha256(original).hexdigest()
    if before != expected[relative]:
        raise RuntimeError(f'Original release hash mismatch: {relative}')
    if original.count(date_old) != 1:
        raise RuntimeError(f'Expected exactly one unsupported GNU date format: {relative}')
    offset = original.index(date_old)
    pe.data[offset:offset+len(date_old)] = date_new
    changes = [{'offset':offset,'before':date_old.decode().rstrip('\0'),'after':date_new.decode().rstrip('\0'),'reason':'Windows strftime uses # rather than - for unpadded day/month'}]
    if path.name == 'storygraph.exe':
        matches = [(rva, off) for rva, off in pe.calls('setvbuf') if pe.data[off-11:off] == bytes.fromhex('45 33 c9 33 d2 41 b8 40 00 00 00')]
        if len(matches) != 1:
            raise RuntimeError(f'Expected one zero-length line-buffer call: {matches}')
        rva, off = matches[0]
        pe.data[off-4] = 4
        changes.append({'offset':off-4,'call_rva':hex(rva),'before':64,'after':4,'reason':'_IONBF safely ignores the zero size; _IOLBF with size zero invokes the invalid parameter handler on Windows'})
    diffs = [i for i, (a,b) in enumerate(zip(original, pe.data)) if a != b]
    required = 3 if path.name == 'storygraph.exe' else 2
    if len(original) != len(pe.data) or len(diffs) != required:
        raise RuntimeError(f'Unexpected binary change count: {len(diffs)}')
    path.write_bytes(pe.data)
    records.append({'path':relative,'original_sha256':before,'fixed_sha256':hashlib.sha256(pe.data).hexdigest(),'changed_bytes':len(diffs),'changes':changes})
result = {'release':'GothicAI-windows-x64-r6-9cadf76','local_revision':'windows-crt-fix1','original_release_preserved':True,'binaries':records}
(root/'windows-crt-fix1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
