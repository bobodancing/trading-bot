"""
pull_db.py — Pull performance.db from rwUbuntu via SFTP (password auth).
Usage: python pull_db.py
"""
from pathlib import Path
import sys

REMOTE_HOST = "100.67.114.104"
REMOTE_USER = "rwfunder"
REMOTE_PASS = "0602"
REMOTE_PATH = "/home/rwfunder/文件/tradingbot/trading_bot/performance.db"
LOCAL_PATH = Path(__file__).parent / "performance.db"


def pull():
    try:
        import paramiko
    except ImportError:
        print("ERROR: paramiko not installed. Run: pip install paramiko")
        sys.exit(1)

    print(f"Connecting to {REMOTE_USER}@{REMOTE_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=15)

    sftp = ssh.open_sftp()
    print(f"Pulling {REMOTE_PATH} ...")
    sftp.get(REMOTE_PATH, str(LOCAL_PATH))
    size_kb = LOCAL_PATH.stat().st_size // 1024
    sftp.close()
    ssh.close()

    print(f"Done: {LOCAL_PATH} ({size_kb} KB)")


if __name__ == "__main__":
    pull()
