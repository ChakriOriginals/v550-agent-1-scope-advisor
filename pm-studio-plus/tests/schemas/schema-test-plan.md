# Schema and validator test plan

The discoverable suite validates behavior through the public validators and OpenAPI/backend contracts:

- exactly six frozen gates plus internal Gate 6B;
- one failing fixture for every named hard check;
- all-hard-checks-pass fixtures with weak criteria that remain `OPEN`;
- retry-envelope behavior only after a prior closure;
- strict unknown-field rejection;
- consent assertion/version/client-observed time;
- no client-owned attempt, generation, report prose, bytes, hash, signature, or storage ID;
- minimized telemetry and privacy rejection;
- exact four-operation Action surface;
- canonical manifest hashes and byte equality;
- authenticated one-page report validation.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s pm-studio-plus/tests -p 'test_*.py'
```
