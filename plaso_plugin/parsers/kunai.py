"""Plaso parser for Kunai JSON-lines event logs."""

from __future__ import annotations

from plaso.lib import errors
from plaso.parsers import interface
from plaso.parsers import manager
from plaso.parsers.jsonl_plugins import kunai as kunai_jsonl_plugin

from standalone_parser import kunai


class KunaiParser(interface.FileObjectParser):
  """Parser that exposes Kunai JSON-L logs as ``--parsers kunai``."""

  NAME = 'kunai'
  DATA_FORMAT = 'Kunai JSON-lines event log'

  _MAXIMUM_LINE_LENGTH = 1024 * 1024

  def _GetLocations(self, file_object):
    """Retrieves best-effort file locations from a dfVFS file object."""

    file_entry = getattr(file_object, 'file_entry', None)
    path_spec = getattr(file_entry, 'path_spec', None)
    locations = []
    while path_spec:
      location = getattr(path_spec, 'location', '') or ''
      if location:
        locations.append(location)
      path_spec = getattr(path_spec, 'parent', None)
    return locations

  def _IsSupportedLocation(self, locations):
    """Checks if path locations indicate a Kunai log or stand-alone log."""

    if not locations:
      return True

    for location in locations:
      if kunai.is_default_kunai_log_path(location):
        return True

      normalized_location = location.replace('\\', '/')
      filename = normalized_location.rsplit('/', 1)[-1]
      if filename == 'events.log' or (
          filename.startswith('events.log.') and filename.endswith('.gz')):
        return True

    return False

  def ParseFileObject(self, parser_mediator, file_object):
    """Parses a Kunai JSON-L file-like object.

    Args:
      parser_mediator (ParserMediator): mediates parser interactions.
      file_object (dfvfs.FileIO): file-like object to parse.

    Raises:
      WrongParser: when the file is not a Kunai JSON-L log.
    """

    locations = self._GetLocations(file_object)
    if not self._IsSupportedLocation(locations):
      raise errors.WrongParser('Not a Kunai event log path.')

    # dfVFS exposes GZIP path specifications as decompressed file objects. Do
    # not wrap them with Python gzip again.
    compressed = False

    number_of_events = 0
    plugin = kunai_jsonl_plugin.KunaiJSONLPlugin()
    lines = kunai.iter_text_lines(file_object, compressed=compressed)
    for line_number, line in enumerate(lines, start=1):
      if not line.strip():
        continue

      try:
        event = kunai.parse_line(line, line_number)
      except kunai.KunaiParseError as exception:
        parser_mediator.ProduceExtractionWarning(
            'Kunai line {0:d}: {1:s}'.format(line_number, str(exception)))
        continue

      parser_mediator.ProduceEventData(plugin._CreateEventData(event))
      number_of_events += 1

    if not number_of_events:
      raise errors.WrongParser('Kunai JSON-L file did not contain events.')


manager.ParsersManager.RegisterParser(KunaiParser)
