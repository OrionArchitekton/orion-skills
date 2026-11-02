# Tool evidence fixtures

Synthetic local data only. Tests never invoke a provider. Scanner fixtures exercise the published shell
example; clean scanner output is an empty JSON array. No credentials are required.

`gitleaks-clean.json` is the exact report emitted by installed Gitleaks 8.24.3 for a
disposable Git repository containing one staged non-secret text file. The other JSON
files are deliberately invalid or non-clean synthetic reports, not scanner claims.
