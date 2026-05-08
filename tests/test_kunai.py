"""Tests for Kunai JSON-lines parsing."""

from __future__ import annotations

from datetime import timezone
import unittest

from standalone_parser import kunai


class KunaiParserTest(unittest.TestCase):
    """Tests for dependency-light Kunai parsing."""

    def test_parse_sample_log(self) -> None:
        with open("testdata/events.log", "r", encoding="utf-8") as file_object:
            result = kunai.parse_lines(file_object)

        self.assertEqual(525, len(result.events))
        self.assertEqual(1, len(result.errors))
        self.assertEqual(
            {"execve", "execve_script", "file_create", "file_unlink", "kill", "mmap_exec", "send_data"},
            {event.event_name for event in result.events},
        )

    def test_parse_file_create(self) -> None:
        line = (
            '{"data":{"ancestors":"/usr/lib/systemd/systemd",'
            '"command_line":"/usr/bin/kunai run -c /etc/kunai/config.yaml -r rules.yml",'
            '"exe":{"path":"/usr/bin/kunai"},"path":"/var/log/kunai/.tmpgObnbg"},'
            '"info":{"host":{"uuid":"host-uuid","name":"SKUNK7","container":null},'
            '"event":{"source":"kunai","id":88,"name":"file_create","uuid":"event-uuid","batch":2077167},'
            '"task":{"name":"kunai","pid":7763,"tgid":300,"uid":0,"user":"root","gid":0,"group":"root"},'
            '"parent_task":{"name":"systemd","pid":1,"tgid":1,"uid":0,"user":"root","gid":0,"group":"root"},'
            '"utc_time":"2026-03-05T21:09:02.557051365Z"}}'
        )

        event = kunai.parse_line(line, 1)

        self.assertEqual("file_create", event.event_name)
        self.assertEqual(88, event.event_id)
        self.assertEqual("event-uuid", event.event_uuid)
        self.assertEqual("SKUNK7", event.fields["host_name"])
        self.assertEqual("/var/log/kunai/.tmpgObnbg", event.fields["path"])
        self.assertEqual("/usr/bin/kunai", event.fields["executable_path"])
        self.assertEqual(557051365, event.timestamp_nanoseconds)
        self.assertEqual(557051, event.timestamp.microsecond)
        self.assertEqual(timezone.utc, event.timestamp.tzinfo)

    def test_parse_send_data_network_fields(self) -> None:
        line = (
            '{"data":{"command_line":"/usr/share/filebeat/bin/filebeat",'
            '"exe":{"path":"/usr/share/filebeat/bin/filebeat"},'
            '"socket":{"domain":"AF_INET","type":"SOCK_STREAM","proto":"TCP"},'
            '"src":{"ip":"10.10.20.17","port":53168},'
            '"dst":{"hostname":"?","ip":"10.10.30.21","port":9200,"public":false,"is_v6":false},'
            '"community_id":"1:abc","data_entropy":7.9,"data_size":1455},'
            '"info":{"host":{"uuid":"host-uuid","name":"SKUNK7","container":null},'
            '"event":{"source":"kunai","id":62,"name":"send_data","uuid":"event-uuid","batch":2077576},'
            '"task":{"name":"filebeat","pid":1994,"tgid":682,"uid":0,"user":"root","gid":0,"group":"root"},'
            '"parent_task":{"name":"systemd","pid":1,"tgid":1},'
            '"utc_time":"2026-03-05T21:09:07.111734624Z"}}'
        )

        event = kunai.parse_line(line, 1)

        self.assertEqual("send_data", event.event_name)
        self.assertEqual("10.10.20.17", event.fields["source_ip"])
        self.assertEqual(53168, event.fields["source_port"])
        self.assertEqual("10.10.30.21", event.fields["destination_ip"])
        self.assertEqual(9200, event.fields["destination_port"])
        self.assertEqual("1:abc", event.fields["community_id"])

    def test_malformed_record_does_not_stop_later_events(self) -> None:
        lines = [
            '{"info":{"event":{"source":"kunai","name":"kill"},"utc_time":"2026-03-05T21:09:02Z"},"data":{}}\n',
            '{"info":\n',
            '{"info":{"event":{"source":"kunai","name":"file_unlink"},"utc_time":"2026-03-05T21:09:03Z"},"data":{}}\n',
        ]

        result = kunai.parse_lines(lines)

        self.assertEqual(["kill", "file_unlink"], [event.event_name for event in result.events])
        self.assertEqual(1, len(result.errors))
        self.assertEqual(2, result.errors[0].line_number)

    def test_missing_optional_fields(self) -> None:
        line = (
            '{"info":{"event":{"source":"kunai","name":"kill"},'
            '"utc_time":"2026-03-05T21:09:02Z"},"data":{}}'
        )

        event = kunai.parse_line(line, 1)

        self.assertEqual("kill", event.event_name)
        self.assertNotIn("host_name", event.fields)

    def test_invalid_timestamp_is_recoverable_error(self) -> None:
        result = kunai.parse_lines(
            ['{"info":{"event":{"source":"kunai","name":"kill"},"utc_time":"not-a-time"},"data":{}}']
        )

        self.assertEqual([], result.events)
        self.assertEqual(1, len(result.errors))
        self.assertIn("unsupported utc_time", result.errors[0].message)

    def test_default_kunai_log_path_matching(self) -> None:
        self.assertTrue(kunai.is_default_kunai_log_path("/var/log/kunai/events.log"))
        self.assertTrue(kunai.is_default_kunai_log_path("/var/log/kunai/events.log.1"))
        self.assertTrue(kunai.is_default_kunai_log_path("/var/log/kunai/events.log.1.gz"))
        self.assertFalse(kunai.is_default_kunai_log_path("/var/log/syslog"))


if __name__ == "__main__":
    unittest.main()
