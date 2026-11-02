#!/usr/bin/env python3
"""Fail on KubeJS (Rhino) declarations that break at run time.

Rhino rejects a const/let declared inside a try block ("redeclaration of var x", every time it runs), and a const/let
declared inside a loop body keeps its first value. Both look fine on a test server that runs the code once.
Use var there. Run by build_server.sh; exits 1 with file:line for each offender.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../pack


def blank(m):
    return re.sub(r'[^\n]', ' ', m.group(0))


def offenders(src):
    # Blank out comments and strings (keeping line breaks) so braces and keywords in them don't count.
    clean = re.sub(r'//[^\n]*|/\*.*?\*/', blank, src, flags=re.S)
    clean = re.sub(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", blank, clean)
    stack, found = [], []
    for m in re.finditer(r'\btry\s*\{|\b(?:for|while)\s*\([^)]*\)\s*\{|\{|\}|\b(?:const|let)\s+[\w\[{]', clean):
        t = m.group(0)
        if t.startswith('try'):
            stack.append('try')
        elif t.startswith(('for', 'while')):
            stack.append('loop')
        elif t == '{':
            stack.append('{')
        elif t == '}':
            if stack:
                stack.pop()
        elif 'try' in stack or 'loop' in stack:
            found.append((clean.count('\n', 0, m.start()) + 1, 'try block' if 'try' in stack else 'loop'))
    return found


def main():
    bad = 0
    for path in sorted(glob.glob(os.path.join(ROOT, 'kubejs', '*_scripts', '*.js'))):
        lines = open(path, encoding='utf-8').read().split('\n')
        for line, where in offenders('\n'.join(lines)):
            print(f'{os.path.relpath(path, ROOT)}:{line}: const/let inside a {where}, use var: {lines[line - 1].strip()}')
            bad += 1
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
