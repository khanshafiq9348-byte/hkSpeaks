import sqlite3
import json
import os
import shutil
import struct
import subprocess
from app.db.voice_catalog import AUTHENTIC_VOICE_CATALOG

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_PATH = os.path.join(ROOT_DIR, "data", "tts.db")
STORAGE_DIR = os.path.join(ROOT_DIR, "data", "storage")
PREVIEWS_DIR = os.path.join(STORAGE_DIR, "previews")

def detect_audio_pitch(fpath: str):
    """Returns detected median pitch (Hz) and gender ('male' | 'female')"""
    if not os.path.exists(fpath):
        return None, "male"
    try:
        cmd = ['ffmpeg', '-y', '-i', fpath, '-ar', '4000', '-ac', '1', '-f', 's16le', 'pipe:1']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_pcm, _ = p.communicate()
        num_samples = len(raw_pcm) // 2
        if num_samples < 400:
            return None, "male"
        samples = struct.unpack(f'<{num_samples}h', raw_pcm[:num_samples*2])
        window = 400
        pitches = []
        for start in range(0, min(len(samples)-window, 4000*3), 400):
            frame = samples[start:start+window]
            mean = sum(frame) // window
            frame = [x - mean for x in frame]
            energy = sum(x*x for x in frame)
            if energy < 100000:
                continue
            best_r = 0
            best_lag = 0
            for lag in range(13, 51):
                r = sum(frame[i] * frame[i+lag] for i in range(window - lag))
                norm = r / energy
                if norm > best_r:
                    best_r = norm
                    best_lag = lag
            if best_r > 0.4 and best_lag > 0:
                pitches.append(4000.0 / best_lag)
        if pitches:
            med = sorted(pitches)[len(pitches)//2]
            return med, ('male' if med < 165 else 'female')
    except Exception as e:
        print(f"Error analyzing pitch for {fpath}: {e}")
    return None, "male"

def migrate_database():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Delete all fake/unverified library voices (amazon, google, elevenlabs, openai, old mock)
    # Preserve custom/cloned voices!
    cursor.execute("""
        DELETE FROM voices 
        WHERE tier != 'custom' AND owner_user_id IS NULL 
        AND provider IN ('amazon', 'google', 'elevenlabs', 'openai', 'azure', 'mock')
        AND slug NOT IN ('sarah-natural', 'david-broadcaster', 'marcus-documentary', 'elena-commercial', 'alexander-audiobook', 'chloe-conversational')
    """)
    deleted_count = cursor.rowcount
    print(f"Deleted {deleted_count} fake/unverified voice records.")

    # 2. Update the 6 core showcase voices to real Edge provider_voice_ids
    showcase_map = {
        'sarah-natural': ('en-US-JennyNeural', 'female', 'edge'),
        'david-broadcaster': ('en-US-GuyNeural', 'male', 'edge'),
        'marcus-documentary': ('en-GB-RyanNeural', 'male', 'edge'),
        'elena-commercial': ('en-US-AriaNeural', 'female', 'edge'),
        'alexander-audiobook': ('en-US-ChristopherNeural', 'male', 'edge'),
        'chloe-conversational': ('en-AU-NatashaNeural', 'female', 'edge')
    }
    for slug, (pvid, gender, prov) in showcase_map.items():
        cursor.execute("""
            UPDATE voices 
            SET provider = ?, provider_voice_id = ?, model = ?, gender = ?, preview_audio_url = NULL 
            WHERE slug = ?
        """, (prov, pvid, pvid, gender, slug))

    # 3. Insert or update all verified Edge voices from AUTHENTIC_VOICE_CATALOG
    import uuid
    from datetime import datetime, timezone

    inserted = 0
    updated = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for v in AUTHENTIC_VOICE_CATALOG:
        cursor.execute("SELECT id FROM voices WHERE slug = ?", (v["slug"],))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE voices
                SET name = ?, description = ?, language = ?, locale = ?, accent = ?,
                    gender = ?, style = ?, tier = ?, provider = ?, provider_voice_id = ?,
                    model = ?, is_public = 1, is_active = 1, preview_audio_url = NULL
                WHERE slug = ?
            """, (
                v["name"], v["description"], v["language"], v["locale"], v["accent"],
                v["gender"], v["style"], v["tier"], v["provider"], v["provider_voice_id"],
                v["model"], v["slug"]
            ))
            updated += 1
        else:
            voice_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO voices (
                    id, name, slug, description, language, locale, accent,
                    gender, style, tier, provider, provider_voice_id, model,
                    preview_audio_url, is_public, is_active, is_clonable,
                    commercial_use_allowed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 1, 1, 0, 1, ?, ?)
            """, (
                voice_id, v["name"], v["slug"], v["description"], v["language"],
                v["locale"], v["accent"], v["gender"], v["style"], v["tier"],
                v["provider"], v["provider_voice_id"], v["model"], now_iso, now_iso
            ))
            inserted += 1

    print(f"Catalog sync: {inserted} inserted, {updated} updated.")

    # 4. Fix existing cloned voices
    cursor.execute("SELECT id, name, preview_audio_url, owner_user_id FROM voices WHERE tier = 'custom' OR owner_user_id IS NOT NULL")
    clones = cursor.fetchall()
    print(f"Inspecting {len(clones)} custom cloned voices...")
    for vid, vname, prev_url, owner_id in clones:
        # Determine audio file on disk
        detected_gender = "male"
        if prev_url and "clones/" in prev_url:
            clone_fname = prev_url.split("clones/")[-1]
            fpath = os.path.join(STORAGE_DIR, "users", owner_id, "clones", clone_fname)
            _, detected_gender = detect_audio_pitch(fpath)

        if detected_gender == "male":
            model = "en-US-GuyNeural"
        else:
            model = "en-US-JennyNeural"

        cursor.execute("""
            UPDATE voices
            SET gender = ?, model = ?, provider = 'edge', provider_voice_id = ?
            WHERE id = ?
        """, (detected_gender, model, model, vid))
        print(f"  Clone '{vname}' ({vid}): gender={detected_gender}, model={model}")

    conn.commit()

    # 5. Clear stale previews directory
    if os.path.exists(PREVIEWS_DIR):
        for f in os.listdir(PREVIEWS_DIR):
            try:
                os.remove(os.path.join(PREVIEWS_DIR, f))
            except Exception:
                pass
        print(f"Cleared all stale audio previews in {PREVIEWS_DIR}")

    # Summary verification
    cursor.execute("SELECT count(*), provider FROM voices GROUP BY provider")
    print("Database voices count by provider:")
    for r in cursor.fetchall():
        print(" ", r)

    cursor.execute("SELECT count(*), gender FROM voices GROUP BY gender")
    print("Database voices count by gender:")
    for r in cursor.fetchall():
        print(" ", r)

    cursor.execute("SELECT count(DISTINCT language) FROM voices")
    print(f"Distinct languages in DB: {cursor.fetchone()[0]}")

    conn.close()

if __name__ == "__main__":
    migrate_database()
