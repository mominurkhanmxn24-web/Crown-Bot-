# Crown Estate Bot - FINAL v2 (free, KEY CHARA, GitHub Actions)

Prottek run e auto: topic pick -> script -> 4 ta image -> voiceover -> **9:16 Short (mp4)**
(Ken Burns + crossfade + grain + camera shake + cinematic grade + burned-in caption).
Laptop lage na. Sob GitHub er server e chole. **Kono AI API key lage na.**

## Kibhabe kaj kore (repetition kibhabe bondho hoy)
1. `content.py` **topic engine** prottek bar ekta notun "brief" pick kore: location (40) x property (16) +
   backstory, buyer, hook style, ending, dam. Ager video gulor sathe mile gele bad:
   - same property: kom-pokkhe 8 video por abar
   - same state: 5 video por, same city: 20 video por
   - same hook/ending: 4 video por
   - same (location, property) joRa **kokhono repeat hoy na** (640 joRa; 3 video/week hole ~4 bochor)
2. **Writer** script lekhe:
   - Local AI (Qwen2.5-3B, GitHub server er CPU te, key lage na), ar
   - jodi seta fail kore/khrap output dey -> **template writer** (sobshomoy kaj kore)
   - Local AI ke topic bechhe nite deya hoy na, tai o repeat korte pare na. Se shudhu golpo ta nijer bhashay lekhe.
3. Image prompt sobshomoy data theke toiri hoy (4 scene e ek-i building, no faces, no text).

## One-time setup (phone e o hoy)
1. GitHub e notun repo banan, ei folder er sob file upload korun (`.github` folder shoho).
2. Repo -> Settings -> Actions -> General -> Workflow permissions -> **Read and write**
3. **Actions tab -> make-short -> Run workflow**. Prothom run e ~2GB model download hobe (pore cache theke), tai ektu beshi somoy lagbe.
4. Log e dekhun: `Writer: local` (local AI) ba `Writer: template`, ar `Voice: Kokoro`.

Kono secret na dileo cholbe. Video paben: Actions run page -> **Artifacts** -> `short.mp4` + `upload_text.txt`.

### Phone e video pete (optional, recommended)
Telegram bot (AI key na): @BotFather diye bot banan -> secret `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
Video + title/description sorasori Telegram e chole ashbe.

## Optional extras (key thakle quality barbe, na thakleo cholbe)
| Secret/Variable | Kaj |
|---|---|
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` | Thakle local AI er age oigulo try kore |
| variable `USE_GITHUB_MODELS` = `1` | GitHub Models (GITHUB_TOKEN diye) try kore |
| `LLM_ORDER` (env) | jemon `template` -> sudhu template, `local,template` -> custom order |
| `YT_REFRESH_TOKEN`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_PRIVACY` | Auto YouTube upload (Google audit pass na hole video private e lock hoy) |

## Customize
- Schedule: `.github/workflows/make-short.yml` er `cron`
- Topic/script variety barate: `content.py` e list (LOCATIONS, PROPS, HOOKS, BACKSTORIES...) e entry add korun
- Voice: `KOKORO_VOICE`; fallback edge-tts (`TTS_VOICE`). Grade: `lut/` e `.cube` file
- Local model bodlate: `LOCAL_MODEL_FILE` + workflow er URL

## v2.1 e ki bodlechhe
- Video size 80MB -> ~10-30MB (crf 24 + maxrate 8M). 45MB er beshi hole auto abar encode (Telegram 50MB limit).
- 4 scene e ek-i seed + ek-i anchor sentence -> building er chehara kache-kachi (guarantee na, nicher note dekhun).
- Image fail hole fallback: Pollinations -> Pollinations key (`POLLINATIONS_API_KEY`, optional) -> AI Horde (anonymous, dheere). Fake/chhoto image reject kore.
- Bug fix: caption time `60.00`, "The crown jewel? A ...", awkward line, title e property naam, mehengha shohor e $15K castle.
- Description e "AI-generated fictional story and visuals." line (YouTube disclosure).
- `python test_offline.py all` -> offline test suite (51 check).

## Jeta jante hobe
- Image consistency: text-to-image e 100% same building guarantee kora jay na (ek-i seed + ek-i prompt prefix shudhu kache-kachi ane, exterior vs interior scene e ektu alada hote pare). Pura guarantee chaile image-edit/reference model lagbe (key lagbe).
- Real network (Pollinations, Kokoro, llama-cpp, Telegram, YouTube) offline test e jachai hoyni, mock diye logic test hoyechhe. Prothom GitHub run ei asol test.
- Local AI (llama-cpp wheel + model download) ami nijer sandbox e cholate parini; test korechi shudhu fallback/validation logic.
  Kono karone fail korle bot auto template e jabe, kaj bondho hobe na.
- Template er golpo structure ek-i dhoroner (hook -> backstory -> buyer -> renovation -> reveal -> price -> CTA). Shabdo/topic bodlay,
  kintu bohu video dekhle structure ta chena lagte pare. Eta bhangte `content.py` e notun structure add korte hobe.
- Pollinations er endpoint kokhono slow/change hoy. Veo-r moto asol video motion free te possible na (image + animation).
