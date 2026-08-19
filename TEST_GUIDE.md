# Kunai Plaso Parser — Integration Test Guide

This guide walks through installing the Kunai parser into an existing Plaso environment and validating it against the included sample evidence.

## Prerequisites

- A Linux system with Plaso / Log2Timeline `20260119` or later installed.
- Python 3 (the same interpreter used by Plaso).
- Root or `sudo` access (Plaso packages are typically installed system-wide).
- A copy of this repository on the target system.

Confirm Plaso is available before proceeding:

```bash
log2timeline.py --version
python3 -c "import plaso; print(plaso.__file__)"
```

Both commands should succeed. If Plaso is installed in a virtual environment, activate it first.

## Step 1 — Install the Parser

### Automated Install

Run the installer with the same Python interpreter that Plaso uses:

```bash
sudo python3 scripts/install_plaso_kunai.py
```

To preview what the installer will do without changing any files:

```bash
python3 scripts/install_plaso_kunai.py --dry-run
```

If the installer cannot locate the Plaso data directory (containing `timeliner.yaml`), provide it explicitly:

```bash
sudo python3 scripts/install_plaso_kunai.py --data-dir /usr/share/plaso
```

### Manual Install

If you prefer to install manually, see the "Manual Install" section in `README.md`.

## Step 2 — Verify Registration

Confirm the `kunai` parser appears in the parser list:

```bash
log2timeline.py --parsers list 2>&1 | grep -i kunai
```

Expected output should include a line referencing `kunai`. If nothing appears, the import lines may not have been added to Plaso's `__init__.py` files — check the installer output or add them manually as described in `README.md`.

## Step 3 — Run Log2Timeline Against the Sample Log

Process the included test data file:

```bash
log2timeline.py \
  --parsers kunai \
  --storage-file /tmp/kunai_test.plaso \
  test_data/kunai.log
```

This should complete without errors. A single extraction warning about a truncated final JSON line is acceptable — it indicates the log was captured mid-write.

## Step 4 — Inspect the Storage File

Use `pinfo.py` to confirm events were stored:

```bash
pinfo.py /tmp/kunai_test.plaso
```

Check the output for:

- A non-zero event count.
- The parser/plugin listed as `kunai`.

## Step 5 — Export and Validate the Timeline

Export events to CSV:

```bash
psort.py -o l2tcsv /tmp/kunai_test.plaso > /tmp/kunai_test.csv
```

Verify that Kunai events appear in the output:

```bash
grep -i 'Kunai' /tmp/kunai_test.csv | head -20
```

### Expected Validation Points

| Check | Expected Result |
| --- | --- |
| `pinfo.py` reports stored events | Event count matches the log (921 valid records in the sample) |
| `psort.py` exports without formatter errors | Clean CSV output, no stack traces |
| CSV contains Kunai event names | Values such as `execve`, `execve_script`, `file_create`, `file_unlink`, `kill`, `mmap_exec`, `send_data` |
| Timestamps are present and valid | UTC timestamps from March 2026 in the sample data |
| Network fields populated for `send_data` events | `src_ip`, `src_port`, `dst_ip`, `dst_port` columns have values |
| At most one extraction warning | Truncated final JSON line from a live-captured log |

## Step 6 — Spot-Check Specific Events

Verify a known record from the sample data. The first line in `test_data/kunai.log` is a `file_create` event at `2026-03-05T21:09:02.557051365Z` for the path `/var/log/kunai/.tmpgObnbg`. Confirm it appears in the CSV:

```bash
grep 'tmpgObnbg' /tmp/kunai_test.csv
```

The output should show a single row with:

- Timestamp: `2026-03-05 21:09:02` (microseconds may vary by output format).
- Source: `Kunai event` / `KUNAI`.
- Process: `kunai`, PID `7763`.
- Path: `/var/log/kunai/.tmpgObnbg`.

## Cleanup

Remove the temporary storage and CSV files when finished:

```bash
rm -f /tmp/kunai_test.plaso /tmp/kunai_test.csv
```

## Troubleshooting

**`log2timeline.py --parsers list` does not show `kunai`**
The parser import was not registered. Verify that Plaso's `parsers/__init__.py` contains `from plaso.parsers import kunai` and that `parsers/jsonl_plugins/__init__.py` contains `from plaso.parsers.jsonl_plugins import kunai`. Re-run the installer or add the lines manually.

**`ModuleNotFoundError: No module named 'standalone_parser'`**
The `standalone_parser` package was not copied to the correct `site-packages` directory. Run the installer again or copy the `standalone_parser/` directory to the same `site-packages` location where `plaso/` is installed.

**`WrongParser` raised immediately**
The parser checks file path patterns before parsing. When processing a standalone file (not inside a disk image), ensure the filename ends in `.log` or matches the expected Kunai naming convention. Alternatively, place the file at a path matching `/var/log/kunai/events.log`.

**Zero events extracted from a valid log**
Confirm the file contains valid Kunai JSON-lines records by checking the first line:

```bash
head -1 test_data/kunai.log | python3 -m json.tool | grep '"source"'
```

The output should include `"source": "kunai"`. If not, the file may not be a Kunai log.
