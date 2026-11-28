# Current-source validation — v0.1.3

Date: 2026-11-28. This record covers the v0.1.3 release metadata and world-class source based on parent commit `d206436` on `world-class/v1`. Verification ran locally on Windows with Python 3.12.3 before the release commit. It does not claim hosted CI, release, or GitHub Pages results for this source.

## Source and static checks

```sh
python scripts/verify.py
python scripts/check_docs.py
python -m compileall -q src tests scripts
python -m streamcontract demo --json <temporary-report>
git diff --check
```

Results:

- Full suite: **42 tests, 42 passed, 0 skipped**.
- Current synthetic demo: reference `pass` after **384 cases**, with exhaustive single cuts; broken control `fail` after **2 cases**.
- Documentation checker and compilation passed.
- One workflow parsed as YAML. Both external Action references are immutable 40-character lowercase commit SHAs.
- `git diff --check` passed; Git reported only the repository's existing CRLF-to-LF normalization warnings.

The OpenAI SDK 2.36.0 result in [openai-decoder-2.36.0.json](openai-decoder-2.36.0.json) is a historical, version-specific local comparison. The optional SDK was not installed or rerun for this record. It is not evidence about current SDK releases or the live OpenAI service.

## Distribution and installed artifact

```sh
python -m build --no-isolation --outdir <temporary-artifact-directory>
python scripts/check_sdist.py <artifact-directory>/streamcontract-0.1.3.tar.gz
```

- Built `streamcontract-0.1.3-py3-none-any.whl` and `streamcontract-0.1.3.tar.gz`.
- Initial inspection found **14 wheel members** and **38 sdist members**; neither contained private/internal, VCS, virtual-environment, or bytecode paths. The final sdist adds this validation document.
- `check_sdist.py` passed the source-byte, required-file, safe-path, duplicate-member, and internal-path checks.
- Installed the actual wheel into a fresh temporary venv outside the checkout with `--no-index --no-deps`; removed `PYTHONPATH`/`PYTHONHOME` and ran outside the repository.
- Installed console demo passed with reference `pass`/broken control `fail` after 384 reference cases. The isolated module check returned `complete`. Isolated import resolved to the temporary venv's `site-packages`, reported version `0.1.3`, and classified an empty stream as `incomplete`.
- SHA-256 checksums are retained with the local release evidence.

## Boundaries

The package has no runtime dependencies. The suite covers the documented bounded fixture and partition model, not all partitions, transport timing, backpressure, reconnect behavior, model correctness, or full provider compliance. Checksums identify local artifact bytes; they do not establish publication or trust.
