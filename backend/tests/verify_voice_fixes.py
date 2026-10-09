import urllib.request
import json
import time
import struct
import subprocess

BASE_URL = 'http://127.0.0.1:8000/v1'

def api_get(endpoint):
    req = urllib.request.Request(f'{BASE_URL}{endpoint}')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def api_post(endpoint, data):
    req = urllib.request.Request(
        f'{BASE_URL}{endpoint}',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def measure_pitch(audio_bytes):
    cmd = ['ffmpeg', '-y', '-i', 'pipe:0', '-ar', '4000', '-ac', '1', '-f', 's16le', 'pipe:1']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    raw_pcm, _ = p.communicate(input=audio_bytes)
    num_samples = len(raw_pcm) // 2
    if num_samples < 400:
        return 0
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
        best_r, best_lag = 0, 0
        for lag in range(13, 51):
            r = sum(frame[i] * frame[i+lag] for i in range(window - lag))
            norm = r / energy
            if norm > best_r:
                best_r, best_lag = norm, lag
        if best_r > 0.4 and best_lag > 0:
            pitches.append(4000.0 / best_lag)

    return sorted(pitches)[len(pitches)//2] if pitches else 0

def test_all():
    print('=== 1. VERIFY /voices ENDPOINT ===')
    voices = api_get('/voices')
    print(f'Total voices returned: {len(voices)}')
    providers = set(v['provider'] for v in voices)
    print(f'Providers: {providers}')
    genders = set(v['gender'] for v in voices)
    print(f'Genders: {genders}')
    males = [v for v in voices if v['gender'] == 'male']
    females = [v for v in voices if v['gender'] == 'female']
    print(f'Male count: {len(males)}, Female count: {len(females)}')

    languages = set(v['language'] for v in voices)
    print(f'Unique languages count: {len(languages)}')

    # Check gender filter via API
    male_filtered = api_get('/voices?gender=male')
    female_filtered = api_get('/voices?gender=female')
    print(f'API gender=male filter returned: {len(male_filtered)}')
    print(f'API gender=female filter returned: {len(female_filtered)}')
    assert all(v['gender'] == 'male' for v in male_filtered)
    assert all(v['gender'] == 'female' for v in female_filtered)
    print('Gender filter verification: PASSED!')

    print('\n=== 2. VERIFY CLONED VOICE TTS GENERATION ===')
    clone_data = api_get('/voices/user-clone')
    clone_voice = clone_data['voice']
    print(f'Active clone: name="{clone_voice["name"]}", id={clone_voice["id"]}, gender={clone_voice["gender"]}, model={clone_voice["model"]}')
    assert clone_voice['gender'] == 'male'

    # Generate speech using this exact clone ID
    gen_res = api_post('/text-to-speech', {
        'text': 'This is a test of my custom uploaded male voice clone speaking on HK Speaks.',
        'voice_id': clone_voice['id'],
        'voice_type': 'cloned',
        'format': 'mp3'
    })
    gen_id = gen_res['id']
    print(f'Dispatched clone generation job: {gen_id}')

    # Poll until completed
    audio_url = None
    for _ in range(30):
        time.sleep(1)
        status_data = api_get(f'/generations/{gen_id}')
        status = status_data['status']
        if status == 'completed':
            audio_url = status_data['audio_url']
            print(f'Clone generation completed! Audio URL: {audio_url}')
            break
        elif status == 'failed':
            print(f'Clone generation FAILED: {status_data}')
            break

    assert audio_url is not None

    # Download generated audio and analyze pitch
    with urllib.request.urlopen(audio_url) as resp:
        audio_bytes = resp.read()

    med_pitch = measure_pitch(audio_bytes)
    gender_detected = "MALE" if med_pitch < 165 else "FEMALE"
    print(f'Generated audio median pitch: {med_pitch:.1f}Hz -> {gender_detected}')
    assert med_pitch < 165, 'Generated audio was NOT male!'
    print('Cloned voice male generation verification: PASSED!')

    print('\n=== 3. VERIFY LIBRARY VOICES UNIQUENESS & PREVIEWS ===')
    # Test 3 distinct voices: Sarah (female US), Marcus (male British), David (male US)
    test_voices = [
        v for v in voices if v['slug'] in ('sarah-natural', 'marcus-documentary', 'david-broadcaster')
    ]
    assert len(test_voices) == 3

    generated_audios = {}
    for tv in test_voices:
        print(f"Testing library voice: {tv['name']} (slug={tv['slug']}, model={tv['model']})")
        # 1. Test preview
        prev_req = urllib.request.Request(f"{BASE_URL}/voices/{tv['id']}/preview")
        with urllib.request.urlopen(prev_req) as resp:
            prev_bytes = resp.read()
        print(f"  Preview audio bytes received: {len(prev_bytes)} bytes")
        assert len(prev_bytes) > 5000

        # 2. Test generation
        t_gen = api_post('/text-to-speech', {
            'text': 'Testing authentic voice uniqueness on HK Speaks platform.',
            'voice_id': tv['id'],
            'voice_type': 'library',
            'format': 'mp3'
        })
        for _ in range(30):
            time.sleep(1)
            t_status = api_get(f"/generations/{t_gen['id']}")
            if t_status['status'] == 'completed':
                with urllib.request.urlopen(t_status['audio_url']) as resp:
                    gen_audio = resp.read()
                generated_audios[tv['slug']] = gen_audio
                pitch = measure_pitch(gen_audio)
                print(f"  Generation completed ({len(gen_audio)} bytes, pitch={pitch:.1f}Hz)")
                break

    # Verify uniqueness: Voice A != Voice B != Voice C
    sarah_audio = generated_audios['sarah-natural']
    marcus_audio = generated_audios['marcus-documentary']
    david_audio = generated_audios['david-broadcaster']

    assert sarah_audio != marcus_audio, "Sarah and Marcus produced identical audio!"
    assert sarah_audio != david_audio, "Sarah and David produced identical audio!"
    assert marcus_audio != david_audio, "Marcus and David produced identical audio!"

    sarah_pitch = measure_pitch(sarah_audio)
    marcus_pitch = measure_pitch(marcus_audio)
    david_pitch = measure_pitch(david_audio)

    print(f"\nSarah (Female) pitch: {sarah_pitch:.1f}Hz")
    print(f"Marcus (Male UK) pitch: {marcus_pitch:.1f}Hz")
    print(f"David (Male US) pitch: {david_pitch:.1f}Hz")

    assert sarah_pitch > 175, "Sarah pitch should be female range (>175Hz)"
    assert marcus_pitch < 175, "Marcus pitch should be male range (<175Hz)"
    assert david_pitch < 175, "David pitch should be male range (<175Hz)"

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_all()
