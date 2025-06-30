#!/usr/bin/env python3
"""
MongoDB Backup and Restore Script
Backup MongoDB dari server production ke server replica menggunakan SSH tunnel
"""

import subprocess
import time
import os
import glob
import logging
import json
from datetime import datetime, timedelta
import shutil

# Load configuration


def load_config():
    """Load configuration from config.json"""
    config_file = 'config.json'
    if not os.path.exists(config_file):
        print(f"[ERROR] File konfigurasi '{config_file}' tidak ditemukan!")
        print("Silakan copy 'config.example.json' ke 'config.json' dan sesuaikan konfigurasinya.")
        exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)


# Load configuration
CONFIG = load_config()

# === KONFIGURASI DARI FILE CONFIG ===
SSH_USER = CONFIG['ssh']['user']
SSH_HOST = CONFIG['ssh']['host']
REMOTE_PORT = CONFIG['mongodb']['remote_port']
LOCAL_TUNNEL_PORT = CONFIG['mongodb']['local_tunnel_port']
DUMP_PATH = CONFIG['backup']['dump_path']

# URI MongoDB remote (tanpa auth)
MONGO_URI = f"mongodb://localhost:{LOCAL_TUNNEL_PORT}"

# URI MongoDB lokal (dengan auth)
LOCAL_RESTORE_URI = CONFIG['mongodb']['local_restore_uri']

# === KONFIGURASI LOGGING ===
LOG_DIR = CONFIG['logging']['log_dir']
LOG_RETENTION_DAYS = CONFIG['logging']['retention_days']


def setup_logging():
    """Setup logging dengan rotasi harian dan pembersihan otomatis"""
    # Buat direktori log jika belum ada
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Format nama file log berdasarkan tanggal
    today = datetime.now().strftime("%Y-%m-%d")
    log_filename = os.path.join(LOG_DIR, f"mongo-backup-{today}.log")

    # Konfigurasi logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # Tetap tampilkan di console
        ]
    )

    # Bersihkan log yang sudah lebih dari retention period
    cleanup_old_logs()

    return logging.getLogger(__name__)


def cleanup_old_logs():
    """Hapus file log yang lebih dari LOG_RETENTION_DAYS hari"""
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)

    # Cari semua file log
    log_pattern = os.path.join(LOG_DIR, "mongo-backup-*.log")
    log_files = glob.glob(log_pattern)

    for log_file in log_files:
        try:
            # Extract tanggal dari nama file
            filename = os.path.basename(log_file)
            date_str = filename.replace(
                "mongo-backup-", "").replace(".log", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")

            # Hapus jika sudah melewati retention period
            if file_date < cutoff_date:
                os.remove(log_file)
                print(f"[*] Log file lama dihapus: {log_file}")
        except (ValueError, OSError) as e:
            print(f"[!] Error saat membersihkan log {log_file}: {e}")


def run_command_with_output(command, description, logger):
    """Jalankan command dan log hasilnya"""
    logger.info(f"Memulai: {description}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    output_lines = []
    for line in process.stdout:
        line = line.strip()
        print("    " + line)
        output_lines.append(line)
        logger.info(f"OUTPUT: {line}")

    process.wait()

    if process.returncode != 0:
        logger.error(
            f"Gagal saat: {description} (Return code: {process.returncode})")
        logger.error(f"Command: {' '.join(command)}")
        return False

    logger.info(f"Berhasil: {description}")
    return True


def check_ssh_connection(logger):
    """Test SSH connection to remote server"""
    logger.info("Testing SSH connection...")
    try:
        result = subprocess.run([
            "ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
            f"{SSH_USER}@{SSH_HOST}", "echo 'SSH connection test successful'"
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            logger.info("SSH connection test berhasil")
            return True
        else:
            logger.error(f"SSH connection test gagal: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("SSH connection test timeout")
        return False
    except Exception as e:
        logger.error(f"Error saat test SSH connection: {e}")
        return False


def cleanup_ssh_tunnels(logger):
    """Bersihkan semua SSH tunnel yang mungkin masih berjalan"""
    logger.info("Membersihkan SSH tunnel yang ada...")
    try:
        subprocess.run(["pkill", "-f", f"ssh.*{SSH_HOST}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Tunggu proses benar-benar mati
    except Exception as e:
        logger.warning(f"Error saat cleanup SSH tunnel: {e}")


def main():
    # Setup logging
    logger = setup_logging()

    logger.info("="*60)
    logger.info("MEMULAI PROSES BACKUP DAN RESTORE MONGODB")
    logger.info(f"Source: {SSH_USER}@{SSH_HOST}:{REMOTE_PORT}")
    logger.info(f"Target: localhost:{CONFIG['mongodb']['local_port']}")
    logger.info("="*60)

    # === 0. Bersihkan tunnel yang mungkin masih ada ===
    cleanup_ssh_tunnels(logger)

    # === 1. Test SSH connection ===
    if not check_ssh_connection(logger):
        logger.error("SSH connection gagal, menghentikan proses")
        return False

    # === 2. Buka SSH tunnel ===
    logger.info("Membuka SSH tunnel...")
    try:
        tunnel_process = subprocess.Popen([
            "ssh", "-4", "-f", "-N", "-o", "StrictHostKeyChecking=no", "-o", "ExitOnForwardFailure=yes",
            "-L", f"{LOCAL_TUNNEL_PORT}:localhost:{REMOTE_PORT}",
            f"{SSH_USER}@{SSH_HOST}"
        ])

        # Tunggu tunnel siap
        time.sleep(5)

        # Verify tunnel is working
        test_result = subprocess.run([
            "nc", "-z", "localhost", str(LOCAL_TUNNEL_PORT)
        ], capture_output=True)

        if test_result.returncode != 0:
            logger.error("SSH tunnel gagal dibuka atau tidak dapat diakses")
            return False

        logger.info("SSH tunnel berhasil dibuka dan dapat diakses")

    except Exception as e:
        logger.error(f"Error saat membuka SSH tunnel: {e}")
        return False

    try:
        # === 3. Hapus backup lama jika ada ===
        if os.path.exists(DUMP_PATH):
            logger.info(f"Menghapus backup lama: {DUMP_PATH}")
            shutil.rmtree(DUMP_PATH)

        # === 4. Dump dari remote ===
        success = run_command_with_output(
            ["mongodump", "--uri", MONGO_URI, "--out", DUMP_PATH],
            "Proses mongodump dari remote",
            logger
        )

        if not success:
            logger.error("Mongodump gagal, menghentikan proses")
            return False

        # === 5. Restore ke lokal (TIDAK DROP database admin) ===
        # Cari semua database kecuali admin
        if not os.path.exists(DUMP_PATH):
            logger.error(f"Direktori backup tidak ditemukan: {DUMP_PATH}")
            return False

        db_dirs = [d for d in os.listdir(DUMP_PATH)
                   if os.path.isdir(os.path.join(DUMP_PATH, d)) and d != 'admin']

        if not db_dirs:
            logger.warning(
                "Tidak ada database yang akan di-restore (selain admin)")
            return True

        logger.info(f"Database yang akan di-restore: {db_dirs}")

        # Restore setiap database secara individual
        all_success = True
        for db_name in db_dirs:
            db_path = os.path.join(DUMP_PATH, db_name)
            success = run_command_with_output(
                ["mongorestore", "--drop", "--db", db_name,
                    db_path, "--uri", LOCAL_RESTORE_URI],
                f"Restore database: {db_name}",
                logger
            )

            if not success:
                logger.error(f"Gagal restore database: {db_name}")
                all_success = False
                break

        if all_success:
            logger.info("SEMUA PROSES BACKUP DAN RESTORE BERHASIL!")
            return True
        else:
            logger.error("BEBERAPA PROSES GAGAL!")
            return False

    except KeyboardInterrupt:
        logger.warning("Script dihentikan oleh user (Ctrl+C)")
        return False
    except Exception as e:
        logger.error(f"Error tidak terduga: {e}")
        return False
    finally:
        # === 6. Tutup SSH tunnel ===
        logger.info("Membersihkan SSH tunnel...")
        cleanup_ssh_tunnels(logger)
        logger.info("SSH tunnel ditutup")

        logger.info("="*60)
        logger.info("PROSES SELESAI")
        logger.info("="*60)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
