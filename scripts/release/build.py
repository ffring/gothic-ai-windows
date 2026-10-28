"""Repack only the verified public r6 archive, never the user's installation."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[2]
ROOT = 'GothicAI-windows-x64-r6-9cadf76-winfix1'
VERSION = '0.1.1'
URL = 'https://github.com/ffring/gothic-ai-windows/releases/download/v' + VERSION + '/'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def download(item, cache):
    path = cache / item['name']
    if not path.exists():
        with urllib.request.urlopen(item['url'], timeout=120) as response, path.open('wb') as out:
            shutil.copyfileobj(response, out)
    if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
        raise ValueError('Source download differs from the pinned release: ' + path.name)
    return path

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=REPO/'downloads')
    parser.add_argument('--dist', type=Path, default=REPO/'dist')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.dist.mkdir(parents=True, exist_ok=True)
    base = json.loads((REPO/'release/base-bundle.json').read_text(encoding='utf-8'))
    original_zip = download(base['asset'], args.cache)
    original_manifest = download(base['manifest'], args.cache)
    manifest = json.loads(original_manifest.read_text(encoding='utf-8-sig'))
    with tempfile.TemporaryDirectory(prefix='gothic-release-') as temp:
        stage = Path(temp)
        with zipfile.ZipFile(original_zip) as archive:
            for member in archive.infolist():
                relative = Path(member.filename)
                if relative.is_absolute() or '..' in relative.parts or ':' in member.filename or relative.parts[0] != base['asset']['root']:
                    raise ValueError('Unexpected source ZIP entry: ' + member.filename)
            archive.extractall(stage)
        original = stage/base['asset']['root']
        target = stage/ROOT
        original.rename(target)
        subprocess.run([sys.executable,str(REPO/'scripts/release/apply_windows_crt_fixes.py'),str(target),str(original_manifest)],check=True)
        shutil.copytree(REPO/'release/bundle-files',target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
        repair = target/'repair-source'
        repair.mkdir()
        for name in ('inspect_pe.py','apply_windows_crt_fixes.py'):
            shutil.copyfile(REPO/'scripts/release'/name,repair/name)
        shutil.copyfile(REPO/'release/windows-crt.patch',repair/'windows-crt.patch')
        (repair/'README.txt').write_text('Base source: https://github.com/ffring/GothicAI/tree/9cadf76b6886cefe48ce61580fe879e8441cb750\nSource-level Windows CRT changes: windows-crt.patch\nThe bounded binary repair is reproducible with the two Python files and the original release manifest.\nOriginal licenses are preserved in LICENSE and licenses/.\n',encoding='utf-8')
        fix = json.loads((target/'windows-crt-fix1.json').read_text(encoding='utf-8'))
        patched = {b['path']:b['fixed_sha256'] for b in fix['binaries']}
        for binary in manifest['binaries']:
            path=target/binary['path']
            expected=patched.get(binary['path'],binary['sha256'])
            if sha(path) != expected:
                raise ValueError('Unexpected packaged binary: ' + binary['path'])
            binary['sha256']=expected
            binary['bytes']=path.stat().st_size
        files=sorted(p for p in target.rglob('*') if p.is_file())
        forbidden={'.env','secrets.toml','chatgpt.json','settings.toml','memory.sqlite3'}
        for path in files:
            if path.name.lower() in forbidden or path.suffix.lower() in {'.sav','.vdf','.wav','.ogg','.log','.pyc','.pyo'} or any(part in {'.venv','__pycache__'} for part in path.parts):
                raise ValueError('Private or game/runtime data must never enter a release: '+str(path.relative_to(target)))
        manifest['name']=ROOT
        manifest['files']=len(files)
        manifest['repack']={'repository':'ffring/gothic-ai-windows','commit':os.environ.get('GITHUB_SHA','local-verification'),'run':os.environ.get('GITHUB_RUN_ID'),'binary_fixes':fix['binaries']}
        manifest['verified']='Base was compiled and unit-tested on windows-2022. Windows CRT fixes were verified on a real Windows 11 x64 PC: full base import, gameplay, speech recognition and voiced NPC response confirmed by the user.'
        zip_path=args.dist/(ROOT+'.zip')
        with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for path in files:
                info=zipfile.ZipInfo(ROOT+'/'+path.relative_to(target).as_posix(),(2026,10,28,0,0,0))
                info.create_system=0
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0x20
                archive.writestr(info,path.read_bytes(),compresslevel=9)
        manifest_path=args.dist/(ROOT+'.manifest.json')
        write_json(manifest_path,manifest)
        bundle=copy.deepcopy(base)
        bundle['version']=VERSION
        bundle['release']='https://github.com/ffring/gothic-ai-windows/releases/tag/v'+VERSION
        for key,path in (('asset',zip_path),('manifest',manifest_path)):
            bundle[key]={'name':path.name,'url':URL+path.name,'bytes':path.stat().st_size,'sha256':sha(path)}
        bundle['asset']['root']=ROOT
        bundle['required'] += ['windows-crt-fix1.json','Prepare-GothicAI-Game.cmd','Check-Microphone.cmd','scripts/windows/game_profile.py','scripts/windows/microphone-check.ps1']
        bundle['source']['fix_repository']='https://github.com/ffring/gothic-ai-windows'
        bundle['source']['fix_commit']=os.environ.get('GITHUB_SHA','local-verification')
        bundle['verified']=manifest['verified']
        write_json(args.dist/'bundle.json',bundle)
        (args.dist/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in (zip_path,manifest_path,args.dist/'bundle.json')),encoding='ascii')
        print(json.dumps({'version':VERSION,'zip_bytes':zip_path.stat().st_size,'zip_sha256':sha(zip_path),'files':len(files),'binaries':len(manifest['binaries'])},indent=2))

if __name__=='__main__':
    main()
