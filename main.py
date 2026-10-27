"""Crown Estate Shorts - FINAL free auto bot (GitHub Actions e chole).

Flow:
  content.py picks a non-repeating topic; writer: [optional API] -> local LLM -> template
  Pollinations (key lage na)                                  : 4 ta image
  Kokoro (fallback edge-tts)                                  : voiceover
  ffmpeg                                                      : Ken Burns + crossfade + grain + grade + caption
  output/short.mp4 + upload_text.txt  -> Telegram / Artifact / (optional) YouTube upload
"""
import asyncio
import json
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).parent
OUT = ROOT / "output"
USED = ROOT / "used_concepts.json"

W, H, FPS = 1080, 1920, 30
XFADE = 0.5  # scene transition (second)
VOICE = os.environ.get("TTS_VOICE", "en-US-GuyNeural")


# =====================================================================
# 1. Concept + script
#    Topic engine (content.py) pick kore -> writer script lekhe:
#    [optional API keys] -> local LLM (key lage na) -> template (sobshomoy kaj kore)
# =====================================================================
import content

_LLM = None
MODEL_PATH = ROOT / "models" / os.environ.get("LOCAL_MODEL_FILE", "qwen2.5-3b-instruct-q4_k_m.gguf")


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))


def call_gemini(prompt):
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0}}
    r = requests.post(url, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                      json=body, timeout=120)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_openai_compat(url, key, model, prompt, json_mode=True):
    body = {"model": model, "temperature": 0.9,
            "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_local(prompt):
    """Runner er CPU te chhoto open-source model (llama.cpp). Kono key/limit nai."""
    from llama_cpp import Llama
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"local model nai: {MODEL_PATH}")
    global _LLM
    if _LLM is None:
        _LLM = Llama(model_path=str(MODEL_PATH), n_ctx=2048,
                     n_threads=os.cpu_count() or 2, verbose=False)
    llm = _LLM
    out = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0.8, max_tokens=450)
    return out["choices"][0]["message"]["content"]


def callers():
    env = os.environ.get
    return {
        "gemini": call_gemini,
        "github": lambda pr: call_openai_compat(
            "https://models.github.ai/inference/chat/completions", env("GITHUB_TOKEN"),
            env("GITHUB_MODEL", "openai/gpt-4.1-mini"), pr),
        "groq": lambda pr: call_openai_compat(
            "https://api.groq.com/openai/v1/chat/completions", env("GROQ_API_KEY"),
            env("GROQ_MODEL", "llama-3.3-70b-versatile"), pr),
        "openrouter": lambda pr: call_openai_compat(
            "https://openrouter.ai/api/v1/chat/completions", env("OPENROUTER_API_KEY"),
            env("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"), pr, json_mode=False),
        "local": call_local,
    }


def writer_order():
    env = os.environ.get
    if env("LLM_ORDER"):
        order = [x.strip() for x in env("LLM_ORDER").split(",") if x.strip()]
    else:
        order = []
        if env("GEMINI_API_KEY"):
            order.append("gemini")
        if env("GROQ_API_KEY"):
            order.append("groq")
        if env("OPENROUTER_API_KEY"):
            order.append("openrouter")
        if env("USE_GITHUB_MODELS") == "1":
            order.append("github")
        order.append("local")
    if "template" not in order:
        order.append("template")
    return order


def make_concept(history):
    brief = content.pick_brief(history)
    fns = callers()
    for name in writer_order():
        if name == "template":
            break
        fn = fns.get(name)
        if not fn:
            continue
        for attempt in range(2):
            try:
                c = content.from_llm(brief, parse_json(fn(content.llm_prompt(brief))), history)
                if c:
                    print("Writer:", name)
                    return c
                print(f"[{name}] output validation fail, retry")
            except Exception as e:
                print(f"[{name}] fail: {e}")
                break  # provider kharap/unavailable -> porerta
    print("Writer: template")
    return content.write_template(brief)


# =====================================================================
# 2. Images: Pollinations (key lage na) -> Pollinations key -> AI Horde (anonymous)
#    Prottek image validate kora hoy (decode hoy kina, size thik kina)
# =====================================================================
def valid_image(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height", "-of", "csv=p=0", str(path)], stderr=subprocess.DEVNULL)
        w, h = [int(x) for x in out.decode().strip().split(",")[:2]]
        return w >= 512 and h >= 512 and Path(path).stat().st_size > 20_000
    except Exception:
        return False


def _save_if_image(r, path):
    if r.ok and r.headers.get("content-type", "").startswith("image"):
        path.write_bytes(r.content)
        if valid_image(path):
            return True
        path.unlink(missing_ok=True)
    return False


def img_pollinations(prompt, path, seed):
    q = urllib.parse.quote(prompt[:700])
    base = f"https://image.pollinations.ai/prompt/{q}?width={W}&height={H}&nologo=true&seed={seed}"
    for variant in ("&model=flux", "&model=turbo", ""):
        for attempt in range(3):
            try:
                if _save_if_image(requests.get(base + variant, timeout=180), path):
                    return True
            except requests.RequestException:
                pass
            time.sleep(8 * (attempt + 1))
    return False


def img_pollinations_key(prompt, path, seed):
    key = os.environ.get("POLLINATIONS_API_KEY")
    if not key:
        return False
    q = urllib.parse.quote(prompt[:700])
    url = f"https://gen.pollinations.ai/image/{q}?width={W}&height={H}&model=flux&seed={seed}"
    for attempt in range(2):
        try:
            if _save_if_image(requests.get(url, headers={"Authorization": f"Bearer {key}"},
                                           timeout=180), path):
                return True
        except requests.RequestException:
            pass
        time.sleep(8)
    return False


def img_horde(prompt, path, seed):
    """AI Horde: free, anonymous key (queue-r jonno dheere). 576x1024, pore ffmpeg scale kore."""
    key = os.environ.get("HORDE_API_KEY", "0000000000")
    hd = {"apikey": key, "Client-Agent": "crown-bot:1:none"}
    try:
        r = requests.post("https://aihorde.net/api/v2/generate/async", headers=hd, timeout=60, json={
            "prompt": prompt[:900] + " ### text, watermark, people, faces, blurry",
            "params": {"width": 576, "height": 1024, "steps": 25, "n": 1, "seed": str(seed)},
            "nsfw": False, "r2": True})
        r.raise_for_status()
        rid = r.json()["id"]
        for _ in range(100):                      # max ~17 minute
            time.sleep(10)
            st = requests.get(f"https://aihorde.net/api/v2/generate/status/{rid}", timeout=60).json()
            if st.get("faulted"):
                return False
            if st.get("done") and st.get("generations"):
                url = st["generations"][0]["img"]
                return _save_if_image(requests.get(url, timeout=120), path)
    except Exception as e:
        print("Horde fail:", e)
    return False


def make_image(prompt, path, seed):
    for name, fn in (("pollinations", img_pollinations), ("pollinations-key", img_pollinations_key),
                     ("horde", img_horde)):
        if fn(prompt, path, seed):
            print(f"Image {path.name}: {name}")
            return
        print(f"Image provider fail: {name}")
    raise RuntimeError(f"Image generation failed: {path.name}")


# =====================================================================
# 3. Voiceover (Kokoro = free ElevenLabs alternative, fallback edge-tts)
# =====================================================================
def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


async def make_voice_edge(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="+5%").save(str(path))


def make_voice_kokoro(text, path):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(str(ROOT / "models" / "kokoro-v1.0.onnx"), str(ROOT / "models" / "voices-v1.0.bin"))
    samples, sr = k.create(text, voice=os.environ.get("KOKORO_VOICE", "am_michael"),
                           speed=1.0, lang="en-us")
    wav = path.with_suffix(".wav")
    sf.write(str(wav), samples, sr)
    run(["ffmpeg", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-q:a", "2", str(path)])


def make_voice(text, path):
    try:
        make_voice_kokoro(text, path)
        print("Voice: Kokoro")
        return
    except Exception as e:
        print("Kokoro fail, edge-tts use hocche:", e)
    asyncio.run(make_voice_edge(text, path))
    print("Voice: edge-tts")


# =====================================================================
# 4. Video (ffmpeg)
# =====================================================================
def duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)])
    return float(out)


def ass_time(t):
    cs = int(round(max(t, 0) * 100))
    return f"{cs // 360000}:{cs % 360000 // 6000:02d}:{cs % 6000 // 100:02d}.{cs % 100:02d}"


def make_captions(text, total, path, words_per=4):
    """Voiceover text ke chunk kore audio length onujayi time bhag kore .ass caption banay."""
    words = re.sub(r"[{}\\\n]", " ", text).split()
    chunks = [" ".join(words[i:i + words_per]) for i in range(0, len(words), words_per)]
    weights = [max(len(c), 1) for c in chunks]
    start, span = 0.15, max(total - 0.5, 1.0)
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
            "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, "
            "Encoding\nStyle: Default,DejaVu Sans,76,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
            "-1,0,0,0,100,100,0,0,1,6,2,2,60,60,430,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
            "Effect, Text\n")
    lines, t, wsum = [], start, sum(weights)
    for c, w in zip(chunks, weights):
        d = span * w / wsum
        lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + d)},Default,,0,0,0,,{c.upper()}")
        t += d
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


MAX_MB = float(os.environ.get("MAX_VIDEO_MB", "45"))   # Telegram bot limit 50MB


def shrink_if_big(path, secs):
    """Video MAX_MB er beshi hole bitrate hishab kore abar encode kore (Telegram 50MB limit)."""
    if path.stat().st_size <= MAX_MB * 1e6:
        return
    vbr = int((MAX_MB * 0.92 * 8e6) / secs) - 192_000
    tmp = path.with_name("small.mp4")
    run(["ffmpeg", "-y", "-i", str(path), "-c:v", "libx264", "-preset", "medium", "-b:v", str(vbr),
         "-maxrate", str(int(vbr * 1.3)), "-bufsize", str(vbr * 2), "-c:a", "copy",
         "-movflags", "+faststart", str(tmp)])
    tmp.replace(path)
    print(f"Video shrunk to {path.stat().st_size / 1e6:.1f} MB")


def build_video(images, audio, out_path, caption_text=None):
    tmp = out_path.parent / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    n = len(images)
    total = duration(audio) + 0.6
    per = (total + (n - 1) * XFADE) / n          # crossfade er jonno clip ektu lomba
    frames = int(round(per * FPS))
    clip_len = frames / FPS

    clips = []
    for i, img in enumerate(images):
        clip = tmp / f"clip{i}.mp4"
        z = "min(zoom+0.0009,1.25)" if i % 2 == 0 else "if(eq(on,0),1.25,max(zoom-0.0009,1.0))"
        shake_x, shake_y = "sin(on/17)*8", "cos(on/23)*8"   # halka handheld feel
        vf = (f"scale=1620:2880:force_original_aspect_ratio=increase,crop=1620:2880,"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)+{shake_x}':y='ih/2-(ih/zoom/2)+{shake_y}':"
              f"d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf, "-frames:v", str(frames),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(clip)])
        clips.append(clip)

    # crossfade chain
    fc, cur = [], "[0:v]"
    for i in range(1, n):
        nxt = f"[x{i}]"
        fc.append(f"{cur}[{i}:v]xfade=transition=fade:duration={XFADE}:"
                  f"offset={i * (clip_len - XFADE):.3f}{nxt}")
        cur = nxt

    grade = "eq=contrast=1.08:saturation=0.9:gamma=0.97,vignette=PI/5,noise=alls=6:allf=t"
    luts = sorted((ROOT / "lut").glob("*.cube"))
    if luts:
        grade = f"lut3d=file='{luts[0].resolve()}'," + grade
    if caption_text:
        ass = tmp / "captions.ass"
        make_captions(caption_text, duration(audio), ass)
        grade += f",subtitles=filename='{ass.resolve()}'"
    fc.append(f"{cur}{grade},format=yuv420p[vout]")

    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", str(c)]
    cmd += ["-i", str(audio), "-filter_complex", ";".join(fc),
            "-map", "[vout]", "-map", f"{n}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-maxrate", "8M", "-bufsize", "16M",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_path)]
    run(cmd)
    shrink_if_big(out_path, duration(audio) + 0.6)


# =====================================================================
# 5. Delivery
# =====================================================================
def send_telegram(video, text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return
    try:
        with open(video, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{tok}/sendVideo",
                              data={"chat_id": chat, "caption": text[:1000]},
                              files={"video": f}, timeout=300)
        print("Telegram:", "sent" if r.ok else f"FAIL {r.status_code} {r.text[:150]}")
    except Exception as e:
        print("Telegram fail:", e)


def main():
    OUT.mkdir(exist_ok=True)
    used = json.loads(USED.read_text()) if USED.exists() else []

    c = make_concept(used)
    print("Concept:", c["concept"])

    # 4 ta scene e EK-i seed: building er chehara kache-kachi thake (alada seed dile 4 ta alada building ashe)
    images, seed = [], int(time.time()) % 1_000_000
    for i, s in enumerate(c["scenes"][:4]):
        p = OUT / f"scene{i + 1}.jpg"
        make_image(s["image_prompt"], p, seed)
        images.append(p)

    audio = OUT / "voice.mp3"
    make_voice(c["voiceover"], audio)

    video = OUT / "short.mp4"
    build_video(images, audio, video, caption_text=c["voiceover"])

    (OUT / "metadata.json").write_text(json.dumps(c, indent=2, ensure_ascii=False))
    text = f"{c['title']}\n\n{c['description']}\n\nTags: {', '.join(c['tags'])}"
    (OUT / "upload_text.txt").write_text(text)
    send_telegram(video, text)

    used.append(c["history"])
    USED.write_text(json.dumps(used, indent=2, ensure_ascii=False))
    print("Done:", video)


if __name__ == "__main__":
    main()
