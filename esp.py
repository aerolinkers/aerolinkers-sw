import requests
import sqlite3
import subprocess
import tempfile
import threading
import queue
import time
import os

try:
    from gtts import gTTS
    import io
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[WARN] gtts not installed. Audio will be skipped.")

SERVER   = "http://192.168.0.138:7000"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Audio queue (single background thread — no overlap, no delay) ──────────────

_audio_queue = queue.Queue()

def _audio_worker():
    """Dedicated thread: generates + plays audio one at a time, no blocking main loop."""
    while True:
        text = _audio_queue.get()
        if not TTS_AVAILABLE:
            _audio_queue.task_done()
            continue
        try:
            tts = gTTS(text=text, lang='en')
            mp3_buf = io.BytesIO()
            tts.write_to_fp(mp3_buf)

            # Save MP3 to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(mp3_buf.getvalue())
                mp3_path = f.name

            # Convert to mono WAV (eliminates L/R channel delay between speakers)
            wav_path = mp3_path.replace(".mp3", ".wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path,
                 "-ac", "1",           # mono — both speakers get same signal in sync
                 "-ar", "48000",       # match PipeWire sample rate
                 wav_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            # Play via paplay targeting the default PipeWire sink directly
            subprocess.run(
                ["paplay", "--device=auto_null", wav_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            os.unlink(mp3_path)
            os.unlink(wav_path)
        except Exception as e:
            print(f"  [AUDIO ERROR] {e}")
        finally:
            _audio_queue.task_done()

# Start the single audio worker thread (daemon so it exits with the script)
threading.Thread(target=_audio_worker, daemon=True).start()

def play_audio(text):
    """Queue text for TTS playback — non-blocking, plays in background."""
    if TTS_AVAILABLE and text:
        print(f"  [AUDIO] {text[:90]}{'...' if len(text) > 90 else ''}")
        _audio_queue.put(text)

# ── DB helpers ─────────────────────────────────────────────────────────────────

def get_all_passengers():
    """
    Read all passengers with an assigned device from the local SQLite DBs.
    Returns a dict keyed by device_id: {pnr, name, device_id, mac}
    """
    passenger_db = os.path.join(BASE_DIR, "db", "passenger.db")
    devices_db   = os.path.join(BASE_DIR, "db", "devices.db")

    try:
        conn = sqlite3.connect(passenger_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT passenger_id, name, device_id FROM passenger WHERE device_id IS NOT NULL"
        ).fetchall()
        conn.close()

        conn = sqlite3.connect(devices_db)
        conn.row_factory = sqlite3.Row
        device_rows = conn.execute("SELECT device_id, mac_address FROM devices").fetchall()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return {}

    mac_map = {r["device_id"]: r["mac_address"] for r in device_rows}

    result = {}
    for p in rows:
        mac = mac_map.get(p["device_id"])
        if mac:
            result[p["device_id"]] = {
                "pnr":       p["passenger_id"],
                "name":      p["name"],
                "device_id": p["device_id"],
                "mac":       mac,
            }
    return result


def sync_passenger(p):
    """POST /sync for a single passenger. Returns flight data dict or None."""
    try:
        res = requests.post(
            f"{SERVER}/sync",
            json={"device_id": p["mac"], "pnr": p["pnr"]},
            timeout=10,
        )
        if res.status_code == 200:
            return res.json()
        return None
    except requests.RequestException as e:
        print(f"  [SYNC] [{p['pnr']}] FAILED -> {e}")
        return None


# ── Boot: initial sync ─────────────────────────────────────────────────────────

known_devices = {}

print("\n[BOOT] Scanning DB for assigned passengers...\n")
current = get_all_passengers()

for dev_id, p in current.items():
    data = sync_passenger(p)
    if data:
        known_devices[dev_id] = p
        print(f"  [SYNC] [{p['pnr']}] {p['name']} -> {dev_id} ({p['mac']})")
        print(f"         Flight: {data.get('flight')} | Seat: {data.get('seat')} | "
              f"Boarding: {data.get('boarding_time')}")

print(f"\n[BOOT] Ready. Monitoring {len(known_devices)} device(s). "
      f"Auto-detecting new assignments every 5s.\n")

# ── Main loop ──────────────────────────────────────────────────────────────────

while True:
    # -- Detect newly assigned devices ----------------------------------------
    current = get_all_passengers()
    for dev_id, p in current.items():
        if dev_id not in known_devices:
            data = sync_passenger(p)
            if data:
                known_devices[dev_id] = p
                msg = (f"Welcome {p['name']}. Your PNR is {p['pnr']}. "
                       f"Flight {data.get('flight')}, Seat {data.get('seat')}. "
                       f"Boarding at {data.get('boarding_time')}.")
                print(f"\n[NEW] {dev_id} -> {p['pnr']} ({p['name']}) | {msg}")
                play_audio(msg)

    # -- Poll boarding alerts for all known devices ----------------------------
    for dev_id in known_devices:
        try:
            res = requests.get(f"{SERVER}/api/notifications/{dev_id}", timeout=10)
            alerts = res.json()
            for alert in alerts:
                print(f"[ALERT] [{dev_id}] {alert.get('message')}")
                play_audio(alert.get('message', ''))
        except requests.RequestException:
            pass

    time.sleep(5)
