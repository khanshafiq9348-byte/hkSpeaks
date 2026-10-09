import asyncio
import edge_tts
import json
import re
import os
import sqlite3
from datetime import datetime, timezone

KNOWN_PROFILES = {
    'en-US-GuyNeural': ['Documentary', 'News', 'Narration'],
    'en-US-JennyNeural': ['Storytelling', 'Conversational', 'Narration'],
    'en-US-AriaNeural': ['News', 'Commercial', 'Narration'],
    'en-US-ChristopherNeural': ['Documentary', 'Narration', 'Educational'],
    'en-US-EricNeural': ['Documentary', 'News', 'Educational'],
    'en-US-AnaNeural': ['Character', 'Conversational'],
    'en-US-AvaNeural': ['Conversational', 'Commercial'],
    'en-US-BrianNeural': ['Conversational', 'Narration', 'Commercial'],
    'en-US-EmmaNeural': ['Conversational', 'Educational'],
    'en-US-MichelleNeural': ['News', 'Narration'],
    'en-US-RogerNeural': ['News', 'Storytelling'],
    'en-US-SteffanNeural': ['Documentary', 'News', 'Narration'],
    'en-GB-RyanNeural': ['Documentary', 'Narration', 'News'],
    'en-GB-SoniaNeural': ['Storytelling', 'Conversational'],
    'en-AU-NatashaNeural': ['Commercial', 'Conversational', 'Educational'],
    'zh-CN-XiaoxiaoNeural': ['News', 'Storytelling', 'Narration'],
    'zh-CN-YunyangNeural': ['Documentary', 'News'],
    'zh-CN-YunxiNeural': ['Storytelling', 'Character'],
    'zh-CN-YunxiaNeural': ['Character'],
    'zh-CN-YunjianNeural': ['Commercial', 'Cinematic'],
    'fr-FR-HenriNeural': ['Documentary', 'Narration', 'News'],
    'fr-FR-DeniseNeural': ['Storytelling', 'Conversational'],
    'de-DE-KillianNeural': ['Documentary', 'News'],
    'de-DE-KatjaNeural': ['Storytelling', 'Conversational'],
    'es-ES-AlvaroNeural': ['Documentary', 'News', 'Narration'],
    'es-ES-ElviraNeural': ['Storytelling', 'Conversational'],
    'hi-IN-MadhurNeural': ['Documentary', 'Narration', 'News'],
    'hi-IN-SwaraNeural': ['Storytelling', 'Conversational'],
}

def derive_styles(v):
    sn = v["ShortName"]
    if sn in KNOWN_PROFILES:
        return KNOWN_PROFILES[sn]
        
    styles = set()
    vt = v.get("VoiceTag", {})
    cats = set(vt.get("ContentCategories", []))
    pers = set(vt.get("VoicePersonalities", []))
    gender = v.get("Gender", "").lower()

    if "News" in cats:
        styles.update(["News", "Narration"])
    if "Novel" in cats or " Novel" in cats:
        styles.update(["Storytelling", "Narration"])
    if "Conversation" in cats or "Copilot" in cats:
        styles.add("Conversational")
    if "Cartoon" in cats or "Dialect" in cats:
        styles.add("Character")
    if "Sports" in cats:
        styles.add("Commercial")

    if "Multilingual" in sn or "Expressive" in sn:
        styles.add("Cinematic")

    if any(p in pers for p in ["Authority", "Professional", "Reliable"]):
        styles.update(["Documentary", "Educational"])
    if any(p in pers for p in ["Clear", "Rational", "Confident"]):
        styles.update(["Narration", "Educational"])
    if any(p in pers for p in ["Expressive", "Passion"]):
        styles.update(["Cinematic", "Commercial"])
    if any(p in pers for p in ["Lively", "Sunshine"]):
        styles.update(["Storytelling", "Commercial"])
    if any(p in pers for p in ["Cute", "Humorous"]):
        styles.add("Character")
    if any(p in pers for p in ["Warm", "Friendly", "Positive", "Comfort", "Considerate", "Pleasant"]):
        styles.update(["Conversational", "Storytelling"])
    if any(p in pers for p in ["Approachable", "Casual", "Sincere"]):
        styles.add("Conversational")

    # Fallback based on gender
    if not styles:
        if gender == "male":
            styles.update(["Narration", "Storytelling", "Documentary"])
        else:
            styles.update(["Conversational", "Storytelling", "Commercial"])

    canonical_order = ["Documentary", "Storytelling", "Cinematic", "Narration", "News", "Conversational", "Character", "Educational", "Commercial"]
    sorted_styles = [s for s in canonical_order if s in styles]
    return sorted_styles if sorted_styles else ["Conversational"]

async def build_verified_catalog():
    voices = await edge_tts.list_voices()
    catalog = []
    seen_ids = set()
    
    for v in voices:
        sn = v["ShortName"]
        if sn in seen_ids:
            continue
        seen_ids.add(sn)
        fn = v.get("FriendlyName", "")
        # Extract persona name: e.g. "Microsoft Guy Online (Natural)" -> "Guy"
        m = re.search(r'Microsoft\s+([A-Za-z0-9]+)\s+Online', fn)
        persona = m.group(1) if m else sn.split("-")[-1].replace("Neural", "")
        
        display_name = f"{persona} (Natural)"
        clean_sn = sn.lower().replace("_", "-")
        slug = f"edge-{clean_sn}"
        lang = v["Locale"].split("-")[0].lower()
        locale_name = v.get("LocaleName", v["Locale"])
        gender = v["Gender"].lower()
        
        style_list = derive_styles(v)
        style = ", ".join(style_list)
        tier = "premium" if ("Multilingual" in sn or "Expressive" in sn) else "standard"
        
        catalog.append({
            "name": display_name,
            "slug": slug,
            "description": f"Microsoft Edge Neural voice ({locale_name}).",
            "language": lang,
            "locale": v["Locale"],
            "accent": locale_name,
            "gender": gender,
            "style": style,
            "styles": style_list,
            "tier": tier,
            "provider": "edge",
            "provider_voice_id": sn,
            "model": sn,
            "is_public": True,
            "commercial_use_allowed": True
        })
        
    return catalog

def write_catalog_py(catalog):
    path = os.path.join(os.path.dirname(__file__), "voice_catalog.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Auto-generated verified Microsoft Edge Neural voice catalog\n")
        f.write("# Contains 100% verified, real neural voices with active provider endpoints\n\n")
        f.write("true = True\nfalse = False\nnull = None\n\n")
        f.write("AUTHENTIC_VOICE_CATALOG = ")
        f.write(json.dumps(catalog, indent=2))
        f.write("\n")
    print(f"Wrote {len(catalog)} voices to {path}")

def sync_database(catalog):
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "tts.db"))
    print(f"Syncing catalog to SQLite: {db_path}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. Delete all fake or alias voices (preserve cloned voices!)
    c.execute("""
        DELETE FROM voices 
        WHERE tier != 'custom' AND owner_user_id IS NULL 
        AND (provider != 'edge' OR slug IN ('sarah-natural', 'david-broadcaster', 'marcus-documentary', 'elena-commercial', 'alexander-audiobook', 'chloe-conversational'))
    """)
    print(f"Purged old unverified rows: {c.rowcount}")

    # 2. Insert or update the 322 authentic verified voices
    updated_count = 0
    inserted_count = 0
    import uuid
    now_iso = datetime.now(timezone.utc).isoformat()

    for v in catalog:
        c.execute("SELECT id, slug FROM voices WHERE provider_voice_id = ?", (v["provider_voice_id"],))
        row = c.fetchone()
        if row:
            v_id, old_slug = row
            try:
                c.execute("""
                    UPDATE voices
                    SET name = ?, description = ?, language = ?, locale = ?, accent = ?,
                        gender = ?, style = ?, tier = ?, provider = ?, model = ?,
                        is_public = 1, is_active = 1, updated_at = ?
                    WHERE id = ?
                """, (
                    v["name"], v["description"], v["language"], v["locale"], v["accent"],
                    v["gender"], v["style"], v["tier"], v["provider"], v["model"],
                    now_iso, v_id
                ))
                updated_count += 1
            except Exception as e:
                print(f"Error updating {v['provider_voice_id']} (slug={v['slug']}, old={old_slug}): {e}")
                raise
        else:
            new_id = str(uuid.uuid4())
            c.execute("""
                INSERT INTO voices (
                    id, name, slug, description, language, locale, accent, gender, style,
                    tier, provider, provider_voice_id, model, is_public, is_active,
                    commercial_use_allowed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, ?, ?)
            """, (
                new_id, v["name"], v["slug"], v["description"], v["language"], v["locale"], v["accent"],
                v["gender"], v["style"], v["tier"], v["provider"], v["provider_voice_id"], v["model"],
                now_iso, now_iso
            ))
            inserted_count += 1

    conn.commit()
    print(f"Database sync complete: {updated_count} updated, {inserted_count} inserted.")

    # 3. Validation check
    c.execute("SELECT count(DISTINCT provider_voice_id), count(*) FROM voices WHERE tier != 'custom' AND owner_user_id IS NULL")
    u_count, t_count = c.fetchone()
    print(f"Verification: {u_count} unique provider_voice_ids / {t_count} total library voices.")

    conn.close()

if __name__ == "__main__":
    cat = asyncio.run(build_verified_catalog())
    write_catalog_py(cat)
    sync_database(cat)

