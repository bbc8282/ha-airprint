"""Container-only check: hold and cancel a local job; never contact a printer."""
import base64
import json
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
import time

spec = importlib.util.spec_from_file_location("cups_logging", "/cups-logging.py")
logging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logging)
for level in logging.LOG_LEVELS:
    logging.configure("/etc/cups/cupsd.conf", "/etc/cups/cups-files.conf", level)
    subprocess.run(["cupsd", "-t"], check=True)

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp)
    log_path = path / "stderr.log"
    with log_path.open("w") as log:
        daemon = subprocess.Popen(["cupsd", "-f"], stdout=log, stderr=log)
        try:
            for attempt in range(50):
                if daemon.poll() is not None:
                    raise RuntimeError("CUPS exited before accepting requests")
                if subprocess.run(["lpstat", "-r"], capture_output=True).returncode == 0:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("CUPS did not start")

            options = path / "options.json"
            for password in ("print", "changed:test-password"):
                options.write_text(json.dumps({"cups_admin_password": password}))
                subprocess.run(["python3", "/cups-admin.py", str(options)], check=True)
                for candidate, expected in ((password, "200"), ("wrong-password", "401")):
                    token = base64.b64encode(("print:" + candidate).encode()).decode()
                    response = subprocess.run(
                        ["curl", "--silent", "--show-error", "--insecure", "--max-time", "10",
                         "--output", "/dev/null", "--write-out", "%{http_code}",
                         "--header", "Authorization: Basic " + token,
                         "https://localhost:631/admin/conf/cupsd.conf"],
                        capture_output=True, text=True, check=True)
                    assert response.stdout == expected, response.stdout
            print("PASS: CUPS admin login, password rotation, and incorrect-password rejection")

            # The job is held before filtering; the loopback URI is never used.
            subprocess.run(["lpadmin", "-p", "DiagnosticTest", "-v",
                            "ipp://127.0.0.1:9/printers/unused", "-m",
                            "drv:///splix-samsung.drv/m2020.ppd", "-E"], check=True)
            (path / "test.txt").write_text("Diagnostic job, held and canceled without printing.\n")
            result = subprocess.run(["lp", "-d", "DiagnosticTest", "-H", "hold",
                                     str(path / "test.txt")], capture_output=True, text=True, check=True)
            job = re.search(r"DiagnosticTest-\d+", result.stdout).group()
            subprocess.run(["cancel", job], check=True)
            for attempt in range(50):
                output = log_path.read_text()
                if "Cancel-Job successful-ok" in output and "Job canceled by" in output:
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Job cancellation was not visible on scheduler stderr")
            print("PASS: CUPS accepted all log levels and logged cancellation to stderr")
            for line in output.splitlines():
                if "Cancel-Job successful-ok" in line or "Job canceled by" in line:
                    print(line)
        except Exception:
            print(log_path.read_text())
            raise
        finally:
            daemon.terminate()
            try:
                daemon.wait(timeout=5)
            except subprocess.TimeoutExpired:
                daemon.kill()
                daemon.wait()
            if daemon.returncode not in (0, -15):
                print(log_path.read_text())
