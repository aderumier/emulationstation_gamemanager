#!/usr/bin/env python3
"""Probe which rename strategies actually work on a (possibly case-insensitive) share.

Usage: python3 tools/probe_case_rename.py /path/to/media/dir

Creates throwaway files named .probe_* in that directory, tries each strategy,
verifies the result with a fresh os.listdir(), and cleans up after itself.
Nothing else in the directory is touched.
"""
import os
import shutil
import sys

d = sys.argv[1]
print(f"directory: {d}")


def entries():
    return os.listdir(d)


def exists_exact(name):
    return name in entries()


def cleanup(*names):
    for n in names:
        try:
            os.remove(os.path.join(d, n))
        except OSError:
            pass


def result(label, ok, extra=''):
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}{(' - ' + extra) if extra else ''}")


UPPER = '.probe_Case_TEST.txt'
LOWER = '.probe_case_test.txt'
TMP = '.probe_tmp_holder.txt'

cleanup(UPPER, LOWER, TMP)

print("\n1) direct case-only rename")
with open(os.path.join(d, UPPER), 'w') as f:
    f.write('probe')
try:
    os.rename(os.path.join(d, UPPER), os.path.join(d, LOWER))
    raised = None
except OSError as e:
    raised = e
ok = exists_exact(LOWER) and not exists_exact(UPPER)
result('rename(Case_TEST -> case_test)', ok,
       f"raised={raised!r}; listing now: {[n for n in entries() if n.startswith('.probe')]!r}")
cleanup(UPPER, LOWER)

print("\n2) two-step rename via temp name (what app.py does today)")
with open(os.path.join(d, UPPER), 'w') as f:
    f.write('probe')
step1 = step2 = None
try:
    os.rename(os.path.join(d, UPPER), os.path.join(d, TMP))
except OSError as e:
    step1 = e
print(f"     after step 1: {[n for n in entries() if n.startswith('.probe')]!r} raised={step1!r}")
os.listdir(d)
try:
    os.rename(os.path.join(d, TMP), os.path.join(d, LOWER))
except OSError as e:
    step2 = e
ok = exists_exact(LOWER) and not exists_exact(TMP)
result('rename(UPPER->tmp) + rename(tmp->lower)', ok,
       f"step2 raised={step2!r}; listing now: {[n for n in entries() if n.startswith('.probe')]!r}")
cleanup(UPPER, LOWER, TMP)

print("\n3) copy to the target name, then delete the source")
with open(os.path.join(d, UPPER), 'w') as f:
    f.write('probe')
copied = None
try:
    shutil.copy2(os.path.join(d, UPPER), os.path.join(d, LOWER))
except OSError as e:
    copied = e
listing_after_copy = [n for n in entries() if n.startswith('.probe')]
print(f"     after copy: {listing_after_copy!r} raised={copied!r}")
# Did the copy land on a distinct file, or did it fold onto the source?
same_inode = None
try:
    same_inode = os.stat(os.path.join(d, UPPER)).st_ino == os.stat(os.path.join(d, LOWER)).st_ino
except OSError:
    pass
print(f"     UPPER and LOWER are the same inode: {same_inode}")
ok = exists_exact(LOWER)
result('copy2(UPPER -> lower)', ok)
cleanup(UPPER, LOWER, TMP)

print("\n4) delete source first, then create the target fresh")
with open(os.path.join(d, UPPER), 'w') as f:
    f.write('probe')
data = open(os.path.join(d, UPPER), 'rb').read()
os.remove(os.path.join(d, UPPER))
os.listdir(d)
with open(os.path.join(d, LOWER), 'wb') as f:
    f.write(data)
ok = exists_exact(LOWER) and not exists_exact(UPPER)
result('remove(UPPER) + write(lower)', ok,
       f"listing now: {[n for n in entries() if n.startswith('.probe')]!r}")
cleanup(UPPER, LOWER, TMP)

print("\nmount info:")
os.system(f"findmnt -T {d!r} -o TARGET,SOURCE,FSTYPE,OPTIONS")
