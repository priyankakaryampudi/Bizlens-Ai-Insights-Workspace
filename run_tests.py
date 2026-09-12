import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TESTS=['tests/smoke_test.py','tests/test_v3_architecture.py','tests/test_regressions.py','tests/test_new_features.py']
for test in TESTS:
    print(f'\n=== {test} ===')
    result=subprocess.run([sys.executable,str(ROOT/test)],cwd=str(ROOT))
    if result.returncode!=0:
        raise SystemExit(result.returncode)
print('\nALL BIZLENS TESTS PASSED')
