import ast
import importlib.util
import json
import os
import re
from pathlib import Path
import struct
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    spec = importlib.util.spec_from_file_location(path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

CONST = load(ROOT / 'custom_components/airprint/const.py')
IPP = load(ROOT / 'airprint/ipp-probe.py')

class ManualDriverTests(unittest.TestCase):
    def match(self, listing, device='ipp://192.168.0.21:631/printers/ipTIME_Printer', model='Samsung M2020 Series', override=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'options.json').write_text(json.dumps({'driver_overrides': [
                {'device': override if override is not None else device, 'model': model}]}))
            (path / 'listing').write_text(listing)
            lpinfo = path / 'lpinfo'
            lpinfo.write_text('#!/bin/sh\ncat "$TEST_LISTING"\n')
            lpinfo.chmod(0o755)
            env = {**os.environ, 'PATH': tmp + ':' + os.environ['PATH'],
                   'AIRPRINT_OPTIONS': str(path / 'options.json'), 'TEST_LISTING': str(path / 'listing')}
            result = subprocess.run(['bash', str(ROOT / 'airprint/manual-driver.sh'), device],
                                    env=env, text=True, capture_output=True, check=True)
            return result.stdout.strip()

    def test_manual_driver_without_discovery(self):
        self.assertEqual(self.match('drv:///splix-samsung.drv/m2020.ppd Samsung M2020 Series, 2.0.2\n'),
                         'drv:///splix-samsung.drv/m2020.ppd')

    def test_prefers_splix_identifier(self):
        self.assertEqual(self.match('vendor.ppd Samsung M2020 Series\ndrv:///splix-samsung.drv/m2020.ppd Samsung M2020 Series, 2.0.2\n'),
                         'drv:///splix-samsung.drv/m2020.ppd')

    def test_legacy_override_uri_matches_canonical_uri(self):
        self.assertEqual(self.match('splix.ppd Samsung M2020 Series\n',
                         override=' 192.168.0.21:631/printers/ipTIME_Printer '), 'splix.ppd')

    def test_missing_driver_does_not_select_unrelated_printer(self):
        self.assertEqual(self.match('splix.ppd Samsung ML-2160\n'), '')

    def test_ambiguous_model_is_not_arbitrarily_selected(self):
        self.assertEqual(self.match('splix-a.ppd Samsung M2020 Series\nsplix-b.ppd Samsung M2020 Series\n'), '')

    def test_large_listing_does_not_sigpipe(self):
        listing = 'splix.ppd Samsung M2020 Series\n' + 'other.ppd Another Printer\n' * 30000
        self.assertEqual(self.match(listing), 'splix.ppd')

    def test_no_override_for_other_device(self):
        self.assertEqual(self.match('splix.ppd Samsung M2020 Series\n', override='socket://other'), '')

class IntegrationTests(unittest.TestCase):
    def test_uri_normalization(self):
        for raw, expected in [
            ('192.168.0.21:631/printers/ipTIME_Printer', 'ipp://192.168.0.21:631/printers/ipTIME_Printer'),
            (' 192.168.0.21 ', 'socket://192.168.0.21'),
            ('dnssd://Printer._pdl-datastream._tcp.local/', 'dnssd://Printer._pdl-datastream._tcp.local/'),
            ('http://router:631/printers/p', 'http://router:631/printers/p'), ('', '')]:
            self.assertEqual(CONST.normalize_device(raw), expected)

    def test_printer_data_preserves_canonical_sensor_identity(self):
        # Execute the production pure function without requiring a full HA installation.
        tree = ast.parse((ROOT / 'custom_components/airprint/config_flow.py').read_text())
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'printer_data')
        scope = {'Any': object, 'normalize_device': CONST.normalize_device, 'device_name': CONST.device_name}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<printer_data>', 'exec'), scope)
        data = scope['printer_data']({'name': 'Samsung', 'device': '192.168.0.21:631/printers/ipTIME_Printer'}, [])
        self.assertEqual(data['device'], 'ipp://192.168.0.21:631/printers/ipTIME_Printer')
        edited = scope['printer_data']({'name': 'New name'}, [], data)
        self.assertEqual(edited['device'], data['device'])

    def test_empty_location_and_pipe_in_label_preserve_driver(self):
        source = (ROOT / 'airprint/monitor.sh').read_text()
        block = source[source.index('\t\tQUEUE=${ROW'):source.index('\t\t[ -n "${QUEUE}" ]')]
        script = "ROW=$'q\\tipp://router/printers/p\\tSamsung|Office\\t\\tsplix.ppd';\n" + block + "printf '%s:%s:%s' \"$LABEL\" \"$LOCATION\" \"$DRIVER\""
        result = subprocess.run(['bash', '-c', script], text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, 'Samsung|Office::splix.ppd')

    def test_versions_match_and_source_driver_is_pinned(self):
        version = re.search(r'^version: \"([^\"]+)\"$', (ROOT / 'airprint/config.yaml').read_text(), re.M).group(1)
        manifest = json.loads((ROOT / 'custom_components/airprint/manifest.json').read_text())
        self.assertEqual(version, manifest['version'])
        dockerfile = (ROOT / 'airprint/Dockerfile').read_text()
        self.assertIn('9bde257882a1ebcf15a97ff4685d34053383e3f8', dockerfile)
        self.assertIn('test -s /usr/share/cups/model/m2020.ppd', dockerfile)

class IPPTests(unittest.TestCase):
    def test_defaults_and_ipv6(self):
        for uri, port in [('ipp://router/p', 631), ('ipps://router/p', 631),
                          ('http://router/p', 80), ('https://router/p', 443)]:
            self.assertEqual(IPP.endpoint(uri)[1], port)
        self.assertEqual(IPP.endpoint('ipp://[::1]:8631/printers/p')[:2], ('::1', 8631))

    def test_probe_is_get_printer_attributes(self):
        self.assertEqual(IPP.request_body('ipp://router/p')[:8], struct.pack('>BBHI', 1, 1, 0x000b, 1))

    def test_invalid_uri_rejected(self):
        for uri in ['socket://router:9100', 'ipp:///p', 'ipp://user:password@router/p']:
            with self.assertRaises(ValueError):
                IPP.endpoint(uri)

    def test_real_http_round_trip_and_rejected_responses(self):
        responses = [
            ('application/ipp', struct.pack('>BBHI', 1, 1, 0, 1) + b'\x03', True),
            ('text/html', b'<html>router</html>', False),
            ('application/ipp', struct.pack('>BBHI', 1, 1, 0x0406, 1) + b'\x03', False),
            ('application/ipp', struct.pack('>BBHI', 1, 1, 0, 99) + b'\x03', False),
            ('application/ipp', b'short', False),
        ]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.server.requests.append((self.path, self.rfile.read(int(self.headers['Content-Length']))))
                content_type, body, _ = self.server.reply
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = HTTPServer(('127.0.0.1', 0), Handler)
        server.requests = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            uri = f'ipp://127.0.0.1:{server.server_port}/printers/ipTIME_Printer'
            for reply in responses:
                server.reply = reply
                self.assertEqual(IPP.check(uri), reply[2])
            self.assertTrue(all(path == '/printers/ipTIME_Printer' and body[2:4] == b'\x00\x0b'
                                for path, body in server.requests))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__':
    unittest.main()
