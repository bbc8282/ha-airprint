import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cups_logging", ROOT / "airprint/cups-logging.py")
LOGGING = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LOGGING)


class CupsLoggingTests(unittest.TestCase):
    def test_routes_logs_without_changing_other_directives(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = Path(tmp) / "cupsd.conf"
            files = Path(tmp) / "cups-files.conf"
            server.write_text("# LogLevel debug\n  loglevel warn\nLogLevel info\nListen 631\n<Policy default>\n</Policy>\n")
            files.write_text("# ErrorLog syslog\nErrorLog /old/error_log\n errorlog syslog\nSystemGroup root lpadmin\n")
            files.chmod(0o640)
            LOGGING.configure(server, files, "debug")
            self.assertEqual(server.read_text(), "# LogLevel debug\nLogLevel debug\nListen 631\n<Policy default>\n</Policy>\nAccessLogLevel actions\n")
            self.assertEqual(files.read_text(), "# ErrorLog syslog\nErrorLog stderr\nSystemGroup root lpadmin\nAccessLog stderr\n")
            self.assertEqual(files.stat().st_mode & 0o777, 0o640)
            before = (server.read_text(), files.read_text())
            LOGGING.configure(server, files, "debug")
            self.assertEqual((server.read_text(), files.read_text()), before)
            LOGGING.configure(server, files, "info")
            self.assertIn("LogLevel info\n", server.read_text())
            self.assertNotIn("LogLevel debug\n", server.read_text().split("\n", 1)[1])

    def test_invalid_level_does_not_change_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = Path(tmp) / "cupsd.conf"
            files = Path(tmp) / "cups-files.conf"
            server.write_text("LogLevel warn\n")
            files.write_text("ErrorLog /old/error_log\n")
            before = (server.read_bytes(), files.read_bytes())
            with self.assertRaises(ValueError):
                LOGGING.configure(server, files, "debug\nWebInterface No")
            self.assertEqual((server.read_bytes(), files.read_bytes()), before)
