#!/bin/bash
# run inside the verifier image: /g = a task's tests/ tree, /newprobes = the v6 probe programs
rm -rf /opt/pyedguard; mkdir -p /opt/pyedguard; cp -r /g/guard.py /g/guardcheck /g/guardvendor /opt/pyedguard/
cp /newprobes/*.py /opt/pyedguard/guardcheck/; chmod -R a+rX /opt/pyedguard; chmod 700 "$(readlink -f /usr/bin/ed)"
cd /tmp
for p in launcher exec_launcher vendored native installed forkexec reimport tamper gcreach plain; do
  out=$(setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs -- env -i LC_ALL=C PATH=/usr/local/bin:/usr/bin:/bin python3 /opt/pyedguard/guard.py /opt/pyedguard/guardcheck/$p.py --version 2>/tmp/err </dev/null); st=$?
  printf '%s\t%s\t%s\t%s\n' "$p" "$st" "$(echo $out | head -c 80)" "$(tail -c 160 /tmp/err | tr '\n' ' ')"
done
