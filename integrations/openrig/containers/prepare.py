#!/usr/bin/env python3
"""Prepare four private local account homes and a Compose environment; never logs in or launches."""
import argparse
import json
import os
from pathlib import Path
import secrets

ACCOUNTS = ('anthropic-alpha','anthropic-bravo','openai-alpha','openai-bravo')

def prepare(root):
    root = root.expanduser().absolute()
    if root.is_symlink() or any(p.is_symlink() for p in root.parents):
        raise ValueError('choose a root without symlink components')
    if any(c in str(root) for c in ('\n','\r','$','"',"'",'#')):
        raise ValueError('root contains unsupported Compose env-file characters')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    hosts=[]
    for index,name in enumerate(ACCOUNTS):
        account=root/name
        if account.is_symlink(): raise ValueError('refusing symlink account directory')
        for relative in ('home','workspace','secrets'):
            folder=account/relative
            if folder.is_symlink(): raise ValueError('refusing symlink directory')
            folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        token=account/'secrets/control-token'
        if not token.exists():
            fd=os.open(token,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream: stream.write(secrets.token_urlsafe(32)+'\n')
        elif token.is_symlink() or not token.is_file():
            raise ValueError('unsafe token path')
        hosts.append({'id':name,'transport':'http','url':f'http://127.0.0.1:{17433+index}', 'bearer_file':str(token)})
    # Candidate registry only; never overwrite the user's active OpenRig hosts.
    (root/'hosts.candidate.json').write_text(json.dumps({'hosts':hosts},indent=2)+'\n')
    (root/'compose.env').write_text('AI_ENV_ROOT='+str(root)+'\nAI_ENV_UID='+str(os.getuid())+'\nAI_ENV_GID='+str(os.getgid())+'\n')
    return root

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    args=parser.parse_args()
    print(prepare(args.root))
