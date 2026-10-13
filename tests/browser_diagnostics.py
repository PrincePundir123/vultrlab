"""Diagnose Chromium namespace compatibility without disabling its sandbox."""
import json
from pathlib import Path
from worker.app import client

profile = json.loads(Path('/app/infra/security/seccomp_profile.json').read_text())
code = '''import ctypes,os
lib=ctypes.CDLL(None,use_errno=True)
result=lib.unshare(0x10000000)
print("unshare_user",result,"errno",ctypes.get_errno(),flush=True)
if result==0:
 try:
  os.chroot("/")
  print("chroot_in_user_namespace",True,flush=True)
 except OSError as e: print("chroot_in_user_namespace",e.errno,flush=True)
'''
with client() as c:
    for extra in (False, True):
        if extra:
            profile['syscalls'].append({'names':['chroot'],'action':'SCMP_ACT_ALLOW','args':[]})
            profile['syscalls'].append({'names':['clone3'],'action':'SCMP_ACT_ERRNO','errnoRet':38,'args':[]})
        result = c.containers.run('skg-browser:local', ['python','-c',code], user='10001:10001',
            network='none', read_only=True, cap_drop=['ALL'],
            security_opt=['no-new-privileges:true','seccomp='+json.dumps(profile)], remove=True)
        print('minimal_namespace_compatibility' if extra else 'upstream_profile', result.decode())
