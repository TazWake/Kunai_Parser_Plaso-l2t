"""JSON-L parser plugin for Kunai event logs."""

from __future__ import annotations

from dfdatetime import posix_time as dfdatetime_posix_time

from plaso.containers import events
from plaso.parsers import jsonl_parser
from plaso.parsers.jsonl_plugins import interface

from standalone_parser import kunai


class KunaiEventData(events.EventData):
  """Kunai event data.

  Attributes:
    recorded_time (dfdatetime.DateTimeValues): date and time the event was
        recorded.
  """

  DATA_TYPE = 'linux:kunai:event'
  DATE_TIME = 'recorded_time'
  DATE_TIME_DESCRIPTION = 'Written'

  def __init__(self):
    """Initializes event data."""
    super(KunaiEventData, self).__init__(data_type=self.DATA_TYPE)
    self.ancestors = None
    self.command_line = None
    self.community_id = None
    self.container_name = None
    self.container_type = None
    self.data_entropy = None
    self.data_size = None
    self.destination_hostname = None
    self.destination_ip = None
    self.destination_is_v6 = None
    self.destination_port = None
    self.destination_public = None
    self.event_batch = None
    self.event_id = None
    self.event_name = None
    self.event_source = None
    self.event_uuid = None
    self.executable_path = None
    self.gid = None
    self.group = None
    self.host_name = None
    self.host_uuid = None
    self.line_number = None
    self.original_timestamp = None
    self.parent_group = None
    self.parent_pid = None
    self.parent_process_guid = None
    self.parent_process_name = None
    self.parent_tgid = None
    self.parent_user = None
    self.path = None
    self.pid = None
    self.process_flags = None
    self.process_guid = None
    self.process_name = None
    self.process_zombie = None
    self.recorded_time = None
    self.signal = None
    self.socket_domain = None
    self.socket_protocol = None
    self.socket_type = None
    self.source_ip = None
    self.source_port = None
    self.success = None
    self.target_command_line = None
    self.target_executable_path = None
    self.target_pid = None
    self.target_process_name = None
    self.target_tgid = None
    self.tgid = None
    self.uid = None
    self.user = None


class KunaiJSONLPlugin(interface.JSONLPlugin):
  """JSON-L parser plugin for Kunai event logs."""

  NAME = 'kunai'
  DATA_FORMAT = 'Kunai event log'

  def _CreateEventData(self, event):
    """Creates Plaso event data from a normalized Kunai event.

    Args:
      event (KunaiEvent): normalized Kunai event.

    Returns:
      KunaiEventData: event data.
    """

    event_data = KunaiEventData()
    event_data.recorded_time = dfdatetime_posix_time.PosixTimeInMicroseconds(
        timestamp=event.timestamp_epoch_microseconds)
    event_data.line_number = event.line_number or None
    event_data.original_timestamp = event.original_timestamp
    event_data.event_name = event.event_name
    event_data.event_id = event.event_id
    event_data.event_uuid = event.event_uuid
    event_data.event_batch = event.event_batch
    event_data.event_source = event.source

    for name, value in event.fields.items():
      setattr(event_data, name, value)

    return event_data

  def _ParseRecord(self, parser_mediator, json_dict):
    """Parses a Kunai JSON-L record.

    Args:
      parser_mediator (ParserMediator): mediates parser interactions.
      json_dict (dict[str, object]): decoded Kunai JSON record.
    """

    try:
      event = kunai.parse_record(json_dict)
    except kunai.KunaiParseError as exception:
      parser_mediator.ProduceExtractionWarning(
          'Unable to parse Kunai record with error: {0!s}'.format(exception))
      return

    parser_mediator.ProduceEventData(self._CreateEventData(event))

  def CheckRequiredFormat(self, json_dict):
    """Check if the record has the minimal Kunai event structure.

    Args:
      json_dict (dict[str, object]): decoded JSON record.

    Returns:
      bool: True if this is a Kunai event record.
    """

    if not isinstance(json_dict, dict):
      return False

    try:
      kunai.parse_record(json_dict)
    except kunai.KunaiParseError:
      return False

    return True


jsonl_parser.JSONLParser.RegisterPlugin(KunaiJSONLPlugin)
