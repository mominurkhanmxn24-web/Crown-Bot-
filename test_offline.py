"""Offline test suite (network lage na): python test_offline.py [fast|video|e2e|all]

Asol network call (Pollinations, Kokoro, Telegram, YouTube) mock kora hoy.
Asol test = GitHub e prothom 'Run workflow'.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import content  # noqa: E402
import main  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))


def make_jpg(path, w=1080, h=1920, seed=0):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    f"gradients=s={w}x{h}:c0=0x3b2f2f:c1=0xd8c9a0:seed={seed}:d=1",
                    "-vf", "noise=alls=10:allf=t", "-frames:v", "1", str(path)],
                   check=True, capture_output=True)


def make_tone(path, secs):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=f=220:d={secs:.1f}",
                    "-c:a", "libmp3lame", str(path)], check=True, capture_output=True)


class Resp:
    def __init__(self, ok=True, ctype="image/jpeg", content=b"", status=200, js=None):
        self.ok, self.headers, self.content, self.status_code = ok, {"content-type": ctype}, content, status
        self._js, self.text = js, ""

    def json(self):
        return self._js

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


# ------------------------------------------------------------------ FAST
def test_content():
    hist, rnd = [], random.Random(11)
    pairs, dup, viol, glitch, lens, wc = set(), 0, 0, 0, 0, []
    cheap_castle = 0
    for _ in range(300):
        b = content.pick_brief(hist, rnd)
        c = content.write_template(b)
        pk = c["history"]["pick"]
        if (pk["loc"], pk["prop"]) in pairs:
            dup += 1
        pairs.add((pk["loc"], pk["prop"]))
        st = content.LOCATIONS[pk["loc"]][1]
        if any(content.LOCATIONS[h["pick"]["loc"]][1] == st for h in hist[-5:]):
            viol += 1
        if any(h["pick"]["prop"] == pk["prop"] for h in hist[-8:]):
            viol += 1
        if any(h["pick"]["loc"] == pk["loc"] for h in hist[-20:]):
            viol += 1
        vo = c["voiceover"]
        if ("? " in vo and any(x in vo for x in ("? a ", "? an ", "? the "))) or "  " in vo:
            glitch += 1
        if len(c["title"]) > 70:
            lens += 1
        city = b["f"]["city"]
        low = int(b["f"]["low"].strip("$K")) * 1000
        if city in content.EXPENSIVE and low < 120000:
            cheap_castle += 1
        wc.append(len(vo.split()))
        assert content.DISCLOSURE in c["description"]
        hist.append(c["history"])
    check("300 runs: zero duplicate (loc,prop)", dup == 0, f"dup={dup}")
    check("300 runs: zero cooldown violations", viol == 0, f"viol={viol}")
    check("no text glitches ('? a', double space)", glitch == 0)
    check("titles <= 70 chars", lens == 0)
    check("expensive towns never cheap price", cheap_castle == 0)
    check("script length 60-125 words", 60 <= min(wc) and max(wc) <= 125, f"{min(wc)}-{max(wc)}")
    check("AI disclosure in every description", True)
    t = content.write_template(content.pick_brief([], random.Random(2)))["title"]
    check("title sample", True, t)
    scenes = content.write_template(content.pick_brief([], random.Random(2)))["scenes"]
    anchors = {s["image_prompt"].split(".")[0] for s in scenes}
    check("4 scene prompts share same anchor sentence", len(anchors) == 1 and len(scenes) == 4)
    check("no faces/text in prompts", all("no faces" in s["image_prompt"] for s in scenes))


def test_helpers():
    check("ass_time(59.996) no '60.00'", main.ass_time(59.996) == "0:01:00.00", main.ass_time(59.996))
    check("ass_time(3725.5)", main.ass_time(3725.5) == "1:02:05.50", main.ass_time(3725.5))
    check("ass_time(0)", main.ass_time(0) == "0:00:00.00")
    check("parse_json fenced", main.parse_json('```json\n{"a":1}\n```') == {"a": 1})
    check("parse_json with chatter", main.parse_json('Sure! {"a": 2} hope it helps') == {"a": 2})
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "USE_GITHUB_MODELS", "LLM_ORDER"):
        os.environ.pop(k, None)
    check("writer order default", main.writer_order() == ["local", "template"])
    os.environ["LLM_ORDER"] = "template"
    check("LLM_ORDER=template", main.writer_order() == ["template"])
    os.environ.pop("LLM_ORDER")
    c = main.make_concept([])
    check("no llama -> template concept", bool(c["voiceover"]) and "scenes" in c)
    b = content.pick_brief([], random.Random(5))
    v = b["f"]["value"]
    good = " ".join(["word"] * 80) + f" worth {v}."
    check("LLM good accepted", bool(content.from_llm(b, {"title": "T", "voiceover": good}, [])))
    check("LLM no price rejected", content.from_llm(b, {"title": "T", "voiceover": "w " * 80}, []) is None)
    check("LLM too short rejected", content.from_llm(b, {"title": "T", "voiceover": f"hi {v}"}, []) is None)
    check("LLM repeat opener rejected",
          content.from_llm(b, {"title": "T", "voiceover": good}, [{"opener": content.opener(good)}]) is None)
    check("LLM non-str fields safe", content.from_llm(b, {"title": None, "voiceover": None}, []) is None)


def test_images():
    tmp = Path(tempfile.mkdtemp())
    good = tmp / "good.jpg"
    make_jpg(good)
    gb = good.read_bytes()
    small = tmp / "small.jpg"
    make_jpg(small, 576, 1024)
    sb = small.read_bytes()
    check("test jpg > 20KB", len(gb) > 20000 and len(sb) > 20000, f"{len(gb)}/{len(sb)}")
    real_get, real_post, real_sleep = main.requests.get, main.requests.post, main.time.sleep
    main.time.sleep = lambda s: None
    out = tmp / "o.jpg"
    try:
        # 1. pollinations ok first try
        calls = []
        main.requests.get = lambda url, **k: (calls.append(url), Resp(content=gb))[1]
        main.make_image("a house", out, 5)
        check("pollinations success", out.exists() and len(calls) == 1 and "seed=5" in calls[0])
        out.unlink()
        # 2. pollinations 429 x all -> key provider
        os.environ["POLLINATIONS_API_KEY"] = "sk_test"
        seen = []

        def g2(url, **k):
            seen.append(url)
            if "image.pollinations.ai" in url:
                return Resp(ok=False, ctype="text/html", status=429)
            return Resp(content=gb)
        main.requests.get = g2
        main.make_image("a house", out, 5)
        check("pollinations 429 -> key provider", out.exists() and any("gen.pollinations.ai" in u for u in seen))
        out.unlink()
        # 3. HTML-with-image-ctype / tiny image rejected, then fallback to horde
        os.environ.pop("POLLINATIONS_API_KEY")

        def g3(url, **k):
            if "image.pollinations.ai" in url:
                return Resp(content=b"not an image at all")          # content-type lies
            if "generate/status" in url:
                return Resp(js={"done": True, "generations": [{"img": "https://r2/img.jpg"}]})
            if "r2/img" in url:
                return Resp(content=sb)
            return Resp(ok=False, status=500)
        main.requests.get = g3
        main.requests.post = lambda url, **k: Resp(js={"id": "abc"})
        main.make_image("a house", out, 5)
        check("fake image rejected -> horde fallback works", out.exists() and main.valid_image(out))
        out.unlink()
        # 4. everything dead -> raises
        main.requests.get = lambda url, **k: Resp(ok=False, ctype="text/html", status=500)
        main.requests.post = lambda url, **k: Resp(ok=False, status=500)
        try:
            main.make_image("a house", out, 5)
            raised = False
        except RuntimeError:
            raised = True
        check("all providers dead -> clear RuntimeError", raised)
        # 5. network exceptions
        def boom(*a, **k):
            raise main.requests.ConnectionError("down")
        main.requests.get, main.requests.post = boom, boom
        try:
            main.make_image("a house", out, 5)
            raised = False
        except RuntimeError:
            raised = True
        check("network exceptions handled", raised)
    finally:
        main.requests.get, main.requests.post, main.time.sleep = real_get, real_post, real_sleep
    shutil.rmtree(tmp)


def test_voice_and_telegram():
    tmp = Path(tempfile.mkdtemp())
    # Kokoro fail -> edge-tts fallback (stub edge_tts)
    called = {}
    edge = types.ModuleType("edge_tts")

    class Comm:
        def __init__(self, text, voice, rate=None):
            called["voice"] = voice

        async def save(self, p):
            Path(p).write_bytes(b"mp3")
    edge.Communicate = Comm
    sys.modules["edge_tts"] = edge
    main.make_voice("hello", tmp / "v.mp3")
    check("kokoro missing -> edge-tts fallback", (tmp / "v.mp3").exists() and called.get("voice"))
    # Telegram
    vid = tmp / "x.mp4"
    vid.write_bytes(b"x" * 1000)
    real_post = main.requests.post
    sent = []
    main.requests.post = lambda url, **k: (sent.append((url, k["data"])), Resp(status=200))[1]
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    main.send_telegram(vid, "cap")
    check("telegram skipped without secrets", sent == [])
    os.environ.update(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_CHAT_ID="42")
    main.send_telegram(vid, "cap" * 1000)
    check("telegram sendVideo called, caption <=1000",
          len(sent) == 1 and "sendVideo" in sent[0][0] and len(sent[0][1]["caption"]) <= 1000)
    main.requests.post = lambda url, **k: (_ for _ in ()).throw(main.requests.ConnectionError("x"))
    try:
        main.send_telegram(vid, "cap")
        ok = True
    except Exception:
        ok = False
    check("telegram error never crashes the run", ok)
    main.requests.post = real_post
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        os.environ.pop(k)
    shutil.rmtree(tmp)


def test_youtube_upload():
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(HERE / "upload_youtube.py", tmp)
    (tmp / "output").mkdir()
    (tmp / "output" / "short.mp4").write_bytes(b"v")
    (tmp / "output" / "metadata.json").write_text(json.dumps(
        {"title": "T" * 120, "description": "d", "tags": ["a"]}))
    log = {"bodies": []}

    class HttpError(Exception):
        def __init__(self, status):
            self.resp = types.SimpleNamespace(status=status)

    class Req:
        def __init__(self, body):
            self.body = body

        def next_chunk(self):
            if self.body["status"].get("containsSyntheticMedia") and log["fail_synth"]:
                raise HttpError(400)
            return None, {"id": "VID123"}

    class Videos:
        def insert(self, part, body, media_body):
            log["bodies"].append(body)
            return Req(body)
    mods = {
        "google": types.ModuleType("google"), "google.oauth2": types.ModuleType("google.oauth2"),
        "google.oauth2.credentials": types.SimpleNamespace(Credentials=lambda *a, **k: object()),
        "googleapiclient": types.ModuleType("googleapiclient"),
        "googleapiclient.discovery": types.SimpleNamespace(build=lambda *a, **k: types.SimpleNamespace(videos=lambda: Videos())),
        "googleapiclient.errors": types.SimpleNamespace(HttpError=HttpError),
        "googleapiclient.http": types.SimpleNamespace(MediaFileUpload=lambda *a, **k: object()),
    }
    sys.modules.update(mods)
    os.environ.update(YT_REFRESH_TOKEN="r", YT_CLIENT_ID="i", YT_CLIENT_SECRET="s")
    spec = __import__("importlib.util").util.spec_from_file_location("upl", tmp / "upload_youtube.py")
    m = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(m)
    log["fail_synth"] = False
    m.main()
    b = log["bodies"][0]
    check("upload: title cut to 100, private default, AI flag set",
          len(b["snippet"]["title"]) == 100 and b["status"]["privacyStatus"] == "private"
          and b["status"]["containsSyntheticMedia"] is True)
    log["bodies"].clear()
    log["fail_synth"] = True
    m.main()
    check("upload: 400 on AI flag -> retry without it",
          len(log["bodies"]) == 2 and "containsSyntheticMedia" not in log["bodies"][1]["status"])
    for k in ("YT_REFRESH_TOKEN", "YT_CLIENT_ID", "YT_CLIENT_SECRET"):
        os.environ.pop(k)
    shutil.rmtree(tmp)


def test_workflow():
    import yaml
    d = yaml.safe_load((HERE / ".github/workflows/make-short.yml").read_text())
    steps = d["jobs"]["build"]["steps"]
    names = [s.get("name") or s.get("uses") or s.get("run") for s in steps]
    check("workflow YAML valid, triggers present", set(d[True]) >= {"schedule", "workflow_dispatch"})
    check("workflow has concurrency + write permission", "concurrency" in d and d["permissions"]["contents"] == "write")
    check("workflow step order: generate before upload before commit",
          names.index("Generate Short") < names.index("Upload to YouTube (optional - shudhu YT_REFRESH_TOKEN thakle)")
          < names.index("Save used concepts"))
    check("pollinations key secret wired",
          any("POLLINATIONS_API_KEY" in json.dumps(s.get("env", {})) for s in steps))
    for f in ("main.py", "content.py", "upload_youtube.py", "get_refresh_token.py"):
        subprocess.run([sys.executable, "-m", "py_compile", str(HERE / f)], check=True)
    check("all python files compile", True)


# ------------------------------------------------------------------ VIDEO
def test_video():
    tmp = Path(tempfile.mkdtemp())
    imgs = []
    for i in range(4):
        p = tmp / f"s{i}.jpg"
        make_jpg(p, seed=i)
        imgs.append(p)
    b = content.pick_brief([], random.Random(3))
    c = content.write_template(b)
    c["voiceover"] = " ".join(c["voiceover"].split()[:40])   # test chhoto rakhi (~15s), asol run e puro 30s
    secs = len(c["voiceover"].split()) / 2.6
    audio = tmp / "v.mp3"
    make_tone(audio, secs)
    out = tmp / "short.mp4"
    t = time.time()
    main.build_video(imgs, audio, out, caption_text=c["voiceover"])
    el = time.time() - t
    pr = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,duration",
         "-of", "json", str(out)]))["streams"]
    v = [s for s in pr if s["codec_name"] == "h264"][0]
    a = [s for s in pr if s["codec_name"] == "aac"][0]
    mb = out.stat().st_size / 1e6
    check("video 1080x1920 h264", (v["width"], v["height"]) == (1080, 1920))
    check("audio/video length match (<0.2s)", abs(float(v["duration"]) - float(a["duration"])) < 0.2,
          f"{v['duration']} vs {a['duration']}")
    check("video <= 45MB (Telegram ok)", mb <= 45, f"{mb:.1f} MB, build {el:.0f}s")
    # shrink guard
    main.MAX_MB = 3
    shutil.copy(out, tmp / "big.mp4")
    main.shrink_if_big(tmp / "big.mp4", float(a["duration"]))
    smb = (tmp / "big.mp4").stat().st_size / 1e6
    check("shrink_if_big enforces limit", smb <= 3.2 and subprocess.run(
        ["ffprobe", "-v", "error", str(tmp / "big.mp4")]).returncode == 0, f"{smb:.1f} MB")
    main.MAX_MB = 45
    # caption frame sanity: pixels differ with caption region
    subprocess.run(["ffmpeg", "-y", "-ss", "8", "-i", str(out), "-frames:v", "1", str(tmp / "f.png")],
                   check=True, capture_output=True)
    check("frame extractable at 8s", (tmp / "f.png").stat().st_size > 10000)
    shutil.copy(tmp / "f.png", "/tmp/frame_check.png")
    shutil.rmtree(tmp)


# ------------------------------------------------------------------ E2E
def test_e2e():
    """main.main() puro: temp copy te (used_concepts.json noshto hoy na). Image/voice mock, video asol."""
    tmp = Path(tempfile.mkdtemp())
    for f in ("main.py", "content.py"):
        shutil.copy(HERE / f, tmp / f)
    (tmp / "lut").mkdir()
    (tmp / "used_concepts.json").write_text("[]")
    sys.modules.pop("main", None)
    sys.modules.pop("content", None)
    sys.path.insert(0, str(tmp))
    import importlib
    m = importlib.import_module("main")
    assert Path(m.__file__).parent == tmp
    base = tmp / "base.jpg"
    make_jpg(base)
    seeds = []
    m.make_image = lambda prompt, path, seed: (shutil.copy(base, path), seeds.append(seed))
    m.make_voice = lambda text, path: make_tone(path, 12)   # e2e te chhoto audio (speed er jonno)
    tg = []
    m.send_telegram = lambda v, t: tg.append((Path(v).exists(), t))
    m.main()
    out = tmp / "output"
    meta = json.loads((out / "metadata.json").read_text())
    used = json.loads((tmp / "used_concepts.json").read_text())
    check("e2e: short.mp4 + metadata + upload_text exist",
          all((out / f).exists() for f in ("short.mp4", "metadata.json", "upload_text.txt")))
    check("e2e: all 4 images used same seed", len(seeds) == 4 and len(set(seeds)) == 1)
    check("e2e: history appended once", len(used) == 1 and used[0]["concept"] == meta["concept"])
    check("e2e: telegram got existing video", tg and tg[0][0])
    up = (out / "upload_text.txt").read_text()
    check("e2e: upload_text has title+desc+tags+AI disclosure", "Tags:" in up and "AI-generated" in up)
    # 2nd and 3rd run: history grows, no repeated (loc,prop)  (video stubbed for speed)
    m.build_video = lambda *a, **k: (out / "short.mp4").write_bytes(b"x")
    for _ in range(25):
        m.main()
    used = json.loads((tmp / "used_concepts.json").read_text())
    pairs = [(h["pick"]["loc"], h["pick"]["prop"]) for h in used]
    check("e2e: 26 consecutive runs, no repeated concept", len(used) == 26 and len(set(pairs)) == 26)
    shutil.rmtree(tmp)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "fast"
    if which in ("fast", "all"):
        for t in (test_content, test_helpers, test_images, test_voice_and_telegram,
                  test_youtube_upload, test_workflow):
            print(f"\n== {t.__name__}")
            t()
    if which in ("video", "all"):
        print("\n== test_video")
        test_video()
    if which in ("e2e", "all"):
        print("\n== test_e2e")
        test_e2e()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    sys.exit(1 if FAIL else 0)
