"""Apply reviewed release files to the existing checkout, with drift checks and backup."""
import argparse
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import sys


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',type=Path,default=Path.home()/'SUMO_KARS')
    args=parser.parse_args();target=args.target.resolve();source=Path(__file__).resolve().parent
    if target==source:raise RuntimeError('Choose your existing Git checkout as the target')
    if not (target/'main.py').is_file() or not (target/'.git').exists():
        raise RuntimeError('Target must be the existing SUMO_KARS Git checkout')
    changes=json.loads((source/'UPDATE_FILES.json').read_text())
    for item in changes:
        relative=Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('Invalid update path')
        prepared=source/relative;current=target/relative
        if digest(prepared)!=item['after']:raise RuntimeError('Release file changed: '+item['path'])
        if current.exists() and digest(current) not in (item['before'],item['after']):
            raise RuntimeError('Your file changed: '+item['path']+'. Nothing has been replaced; merge that file first.')
        if item['before'] is not None and not current.exists():raise RuntimeError('Expected file missing: '+item['path'])
    backup=target.parent/('SUMO_KARS_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    for item in changes:
        relative=Path(item['path']);current=target/relative
        if current.exists():
            saved=backup/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(current,saved)
        current.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/relative,current)
    print('Updated',target)
    print('Backup:',backup)
    print('Review git diff before committing. No commit or push was performed.')
    print('Start the project using Start_City.cmd in your Git checkout.')


if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError) as error:
        print('Update stopped:',error);sys.exit(1)
