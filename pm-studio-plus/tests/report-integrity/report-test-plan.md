# Report-integrity test plan

Automated offline coverage lives in `test_report_integrity.py` and `test_telemetry_backend_contract.py`.

- authenticated original and regenerated receipts;
- exact original/regenerated status strings;
- manual byte edit failure;
- copied report ID with different bytes failure;
- edited bytes plus edited hash failure because the receipt HMAC no longer authenticates;
- unknown/wrong signing key failure and historical key-version verification;
- stage-attempt/generation/prior-link consistency;
- one US Letter page, minimum readable font, and no forms/annotations;
- backend render/store/reread/hash/sign markers;
- Gate 6 plus internal 6B authorization;
- stored-byte redownload and opaque capability binding;
- instructor-only four-status verifier.

The disposable-tenant cases in `../apps-script/apps-script-test-plan.md` remain mandatory because static analysis cannot prove Drive permissions, transaction behavior, or actual byte streaming.
