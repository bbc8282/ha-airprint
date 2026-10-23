"""Configure the dedicated CUPS web administrator without logging credentials."""
import json
import pwd
import subprocess
import sys


def configure(options):
    password = options.get("cups_admin_password", "print")
    if not isinstance(password, str) or not password or any(c in password for c in "\r\n\x00"):
        raise ValueError("cups_admin_password must be nonempty and contain no line breaks or NUL")
    try:
        pwd.getpwnam("print")
    except KeyError:
        subprocess.run(["useradd", "--no-create-home", "--shell", "/usr/sbin/nologin", "print"], check=True)
    subprocess.run(["usermod", "--append", "--groups", "lpadmin", "print"], check=True)
    subprocess.run(["chpasswd"], input="print:" + password + "\n", text=True, check=True)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as stream:
        configure(json.load(stream))
    print("[airprint] CUPS web administrator configured: print")
