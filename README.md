# Kunai Plaso Parser

Kunai Plaso Parser adds Log2Timeline / Plaso support for Kunai JSON-lines event logs. It is designed for Linux evidence images and stand-alone Kunai log files.

Supported Kunai paths include:

- `/var/log/kunai/events.log`
- `/var/log/kunai/events.log.[0-9]+`
- `/var/log/kunai/events.log.[0-9]+.gz`

The parser has been developed against Plaso / Log2Timeline `20260119`.

## Repository Layout

- `standalone_parser/`: dependency-light Kunai JSON-lines parser helpers used by the Plaso plugin.
- `plaso_plugin/parsers/kunai.py`: Plaso parser exposed as `--parsers kunai`.
- `plaso_plugin/jsonl_plugins/kunai.py`: JSON-L plugin and `linux:kunai:event` event data.
- `plaso_plugin/data/timeliner_kunai.yaml`: timeliner mapping required for event creation.
- `plaso_plugin/data/formatter_kunai.yaml`: YAML formatter used by `psort.py`.
- `scripts/install_plaso_kunai.py`: installer for the active Plaso Python environment.
- `tests/`: local parser unit tests using `testdata/events.log`.

## Install

Run the installer with the same Python environment used by Plaso. On system installs this commonly requires `sudo`:

```bash
sudo python3 scripts/install_plaso_kunai.py
```

Preview changes first:

```bash
python3 scripts/install_plaso_kunai.py --dry-run
```

If the installer cannot find Plaso's data directory, provide it explicitly:

```bash
sudo python3 scripts/install_plaso_kunai.py --data-dir /usr/share/plaso
```

The installer copies the standalone helper package, parser files, formatter YAML, and appends the Kunai timeliner mapping. It also adds the required parser imports to Plaso's package `__init__.py` files.

Verify registration:

```bash
log2timeline.py --parsers list | grep -i kunai
```

## Manual Install

If you prefer to install manually, locate the active Plaso package:

```bash
python3 -c "import plaso, pathlib; print(pathlib.Path(plaso.__file__).parent)"
```

Copy files:

```bash
sudo cp plaso_plugin/parsers/kunai.py <plaso_path>/parsers/kunai.py
sudo cp plaso_plugin/jsonl_plugins/kunai.py <plaso_path>/parsers/jsonl_plugins/kunai.py
sudo cp -r standalone_parser <site_packages>/
sudo cp plaso_plugin/data/formatter_kunai.yaml <plaso_data>/formatters/kunai.yaml
cat plaso_plugin/data/timeliner_kunai.yaml | sudo tee -a <plaso_data>/timeliner.yaml
```

Then add these imports if your Plaso version does not auto-discover modules:

```python
from plaso.parsers import kunai
from plaso.parsers.jsonl_plugins import kunai
```

## Usage

For targeted evidence-image processing, create a Plaso YAML filter such as `kunai_filter.yaml`:

```yaml
description: Kunai files
type: include
path_separator: '/'
paths:
- '/var/log/kunai/events.log'
- '/var/log/kunai/events.log.[0-9]+'
- '/var/log/kunai/events.log.[0-9]+.gz'
```

Run Log2Timeline:

```bash
log2timeline.py \
  --filter-file kunai_filter.yaml \
  --parsers kunai \
  --storage-file kunai.plaso \
  evidence.E01
```

Run against a stand-alone Kunai log:

```bash
log2timeline.py --parsers kunai --storage-file kunai.plaso events.log
```

Export a CSV timeline:

```bash
psort.py -o l2tcsv kunai.plaso > kunai.csv
```

## Notes

Kunai active logs can be captured mid-write. A final truncated JSON line should produce an extraction warning, but valid records before it should still be stored.

Rotated gzip logs are handled through Plaso / dfVFS GZIP path specifications. The parser reads the decompressed stream provided by Plaso.

## Evidence Validation

Validate a generated storage file before reporting results:

```bash
pinfo.py kunai.plaso
psort.py -o l2tcsv kunai.plaso > kunai.csv
grep -i 'Kunai' kunai.csv | head
```

Expected validation points:

- `pinfo.py` reports stored events.
- `psort.py` exports without formatter errors.
- CSV output includes Kunai event names such as `file_create`, `file_unlink`, `kill`, or `send_data`.
- A captured-live active log may produce a warning for one truncated JSON line; valid records should still be present.

## Development

Run local tests:

```powershell
python -m unittest discover -v
```

Run a syntax check:

```powershell
python -m compileall standalone_parser tests plaso_plugin scripts
```
