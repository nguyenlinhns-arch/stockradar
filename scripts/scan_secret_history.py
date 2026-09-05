"""Scan tracked source and reachable Git blobs; report fingerprints, never credentials."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess

PATTERNS={
 'private_key':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'openai_key':rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{30,}',
 'resend_key':rb'\bre_[A-Za-z0-9]{25,}',
 'aws_access_key':rb'\bAKIA[0-9A-Z]{16}\b',
 'github_token':rb'\bgh[pousr]_[A-Za-z0-9]{30,}',
}

def findings(data):
 hits=[]
 for label,pattern in PATTERNS.items():
  for m in re.finditer(pattern,data):
   hits.append({'kind':label,'fingerprint':hashlib.sha256(m.group()).hexdigest()[:12]})
 for m in re.finditer(rb'eyJ[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+',data):
  try:
   payload=json.loads(base64.urlsafe_b64decode(m[1]+b'='*((-len(m[1]))%4)))
   if payload.get('role')=='service_role':hits.append({'kind':'service_role_jwt','fingerprint':hashlib.sha256(m[0]).hexdigest()[:12]})
  except (ValueError,TypeError):pass
 return hits

def main():
 rows=[]
 tracked=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
 for name in filter(None,tracked):
  p=Path(name)
  if p.is_file():
   rows.extend({'location':name,**hit} for hit in findings(p.read_bytes()))
 objects=subprocess.check_output(['git','rev-list','--objects','--all']).decode().splitlines()
 proc=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
 count=0
 try:
  for line in objects:
   oid,_,name=line.partition(' ')
   proc.stdin.write((oid+'\n').encode());proc.stdin.flush()
   header=proc.stdout.readline().decode().split();size=int(header[2]);data=proc.stdout.read(size);proc.stdout.read(1)
   if header[1]=='blob':
    count+=1;rows.extend({'location':name or oid,'object':oid,**hit} for hit in findings(data))
 finally:proc.stdin.close();proc.wait()
 result={'tracked_files':len(tracked)-1,'history_blobs':count,'findings':rows}
 print(json.dumps(result,indent=2))
 return bool(rows)

if __name__=='__main__':raise SystemExit(main())
