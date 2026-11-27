# Offline verification

A fresh Python 3.12 environment on the Linux development machine was
created in a separate network namespace with only loopback and no default
route. All dependencies installed from wheels using `--no-index`.
The application loaded the cached PC-14 demo with 276 events and verified
all 12 artifact hashes and an intact audit chain.

All 30 Python tests passed. Three successive Chromium walkthroughs
verified the hashes, opened the exact PC log row, toggled calibration,
reviewed the badge alert, and exported JSON and PDF. The walkthroughs
also checked that the blurry frame remained flagged for manual time entry.

The handoff archive contains Python 3.12 wheels for Linux x86-64 and Windows
x64. The isolated run was performed on Linux. The repository includes a
Windows and Linux CI workflow. The presenting laptop still needs its
physical Wi-Fi-off rehearsal and setup timing. The cached software run did
not require Ollama.
