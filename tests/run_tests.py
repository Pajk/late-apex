#!/usr/bin/env python3
"""Runs the whole suite.

    ./test.sh                 # everything
    ./test.sh geometry ui     # just those

Rendered frames land in tests/output/ so a run can also be eyeballed.
"""

import importlib
import sys
import time

from tests import harness

SUITES = ['geometry', 'rules', 'render', 'ui', 'balance']


def main(argv):
    wanted = [a for a in argv[1:] if not a.startswith('-')] or SUITES
    unknown = [w for w in wanted if w not in SUITES]
    if unknown:
        print('unknown suite(s): %s\navailable: %s'
              % (', '.join(unknown), ', '.join(SUITES)))
        return 2

    harness.setup()
    print('LATE APEX - test suite\n')
    failed = []
    started = time.perf_counter()
    for name in wanted:
        print('%s:' % name)
        module = importlib.import_module('tests.test_%s' % name)
        try:
            if not module.run():
                failed.append(name)
        except Exception as exc:                     # noqa: BLE001
            import traceback
            print('  ERROR %s - %s' % (name, exc))
            traceback.print_exc()
            failed.append(name)
        print()

    took = time.perf_counter() - started
    if failed:
        print('FAILED: %s  (%.1fs)' % (', '.join(failed), took))
        return 1
    print('All %d suites passed (%.1fs)' % (len(wanted), took))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
