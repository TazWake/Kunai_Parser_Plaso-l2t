# Plaso Integration Files

Copy these files into a matching Plaso source tree or package:

- `jsonl_plugins/kunai.py` -> `plaso/parsers/jsonl_plugins/kunai.py`
- `parsers/kunai.py` -> `plaso/parsers/kunai.py`
- `data/timeliner_kunai.yaml` -> append to the active Plaso `timeliner.yaml`
- `data/formatter_kunai.yaml` -> copy into the active Plaso formatter data directory

Also copy the `standalone_parser` package so the adapter can use the tested JSON-lines parsing helpers.

After copying, make sure the Plaso package imports these modules according to the target version's registration pattern. For a source checkout this commonly means adding imports to `plaso/parsers/__init__.py` and `plaso/parsers/jsonl_plugins/__init__.py`.

The direct parser wrapper is intended to support:

```bash
log2timeline.py --parsers kunai --storage_file output.plaso /path/to/source
```

If the target Plaso version only exposes the JSON-L plugin form, try `--parsers jsonl/kunai` and record that in `TESTPLAN.md` results.

For E01 testing with Plaso 20260119, prefer a YAML `--filter-file` include list for `/var/log/kunai/events.log` and rotated `events.log.[0-9]+.gz` files to avoid scanning unrelated files.

Plaso 20260119 also requires a timeliner mapping for new event data types. Append `data/timeliner_kunai.yaml` to the active `timeliner.yaml`, commonly `/usr/share/plaso/timeliner.yaml`, otherwise `ProduceEventData()` will not create stored timeline events for `linux:kunai:event`.
