"""Content engine: repetition-proof topic picker + template script writer + image prompts.

Idea: LLM (ba template) KOKHONO nije topic bechhe na. Engine age ekta "brief" pick kore
(location, property, backstory, buyer, hook style, ending, dam...) cooldown diye, jate
ager video gulor sathe mile na. Tarpor sei brief theke script lekha hoy.
Image prompt sobshomoy data theke bane, tai 4 scene er building ek-i thake ar kokhono face ashe na.
"""
import random
import re
import time

# ---------------------------------------------------------------- DATA
LOCATIONS = [  # (city, state, setting)
    ("Savannah", "Georgia", "live oaks and Spanish moss"),
    ("Charleston", "South Carolina", "salt marsh and palmetto trees"),
    ("New Orleans", "Louisiana", "bayou humidity and iron balconies"),
    ("Asheville", "North Carolina", "Blue Ridge mountain forest"),
    ("Hudson", "New York", "Hudson Valley river light"),
    ("Cape May", "New Jersey", "Atlantic seaside fog"),
    ("Galveston", "Texas", "Gulf Coast storm skies"),
    ("Fredericksburg", "Texas", "Hill Country limestone and wildflowers"),
    ("Santa Fe", "New Mexico", "high desert adobe light"),
    ("Sedona", "Arizona", "red rock desert"),
    ("Napa", "California", "vineyard hills at golden hour"),
    ("Carmel", "California", "Pacific cypress coastline"),
    ("Bend", "Oregon", "pine forest and volcanic peaks"),
    ("Port Townsend", "Washington", "misty Puget Sound"),
    ("Jackson", "Wyoming", "Teton mountain backdrop"),
    ("Telluride", "Colorado", "alpine valley and aspens"),
    ("Burlington", "Vermont", "autumn maple hills"),
    ("Portland", "Maine", "rocky Atlantic coast"),
    ("Newport", "Rhode Island", "Gilded Age coastline"),
    ("Nantucket", "Massachusetts", "grey shingle dunes"),
    ("Lexington", "Kentucky", "horse-country green fields"),
    ("Nashville", "Tennessee", "rolling southern hills"),
    ("Natchez", "Mississippi", "bluffs over the Mississippi"),
    ("Mobile", "Alabama", "gulf oaks and azaleas"),
    ("Key West", "Florida", "tropical palms and turquoise light"),
    ("St. Augustine", "Florida", "coquina stone and old Spanish streets"),
    ("Madison", "Wisconsin", "lakeside prairie"),
    ("Door County", "Wisconsin", "limestone bluffs on Lake Michigan"),
    ("Traverse City", "Michigan", "cherry orchards and lake light"),
    ("Galena", "Illinois", "river bluffs and brick Main Street"),
    ("Cooperstown", "New York", "quiet lakeside village"),
    ("Harpers Ferry", "West Virginia", "misty river gorge"),
    ("Lancaster", "Pennsylvania", "amber farmland"),
    ("Annapolis", "Maryland", "Chesapeake harbor"),
    ("Marfa", "Texas", "open West Texas desert"),
    ("Park City", "Utah", "snowy mountain ridge"),
    ("Sun Valley", "Idaho", "high sagebrush valley"),
    ("Whitefish", "Montana", "big-sky pine lakes"),
    ("Kauai", "Hawaii", "lush tropical cliffs"),
    ("Sitka", "Alaska", "moody coastal rainforest"),
]

PROPS = [
    dict(name="Victorian mansion",
         decay="peeling paint, a sagging wraparound porch and broken turret windows",
         gut="stripped plaster, bare studs and exposed oak beams",
         polish="fresh plaster, refinished heart-pine floors and tall arched windows",
         hero="a restored grand staircase under a glowing brass chandelier"),
    dict(name="stone castle",
         decay="crumbling battlements and ivy-choked walls",
         gut="a scaffolded great hall with bare stone and open roof trusses",
         polish="new oak roof beams, re-pointed stonework and tall leaded windows",
         hero="the great hall with a roaring stone fireplace and candlelit iron chandeliers"),
    dict(name="barn",
         decay="a collapsed roof and rusted tin siding",
         gut="an open timber frame under scaffolding",
         polish="new cedar siding and huge glass doors",
         hero="a soaring great room with exposed beams and a stone fireplace"),
    dict(name="lighthouse keeper's house",
         decay="a rotting porch and salt-bleached shingles",
         gut="bare stone walls and a stripped spiral stair",
         polish="whitewashed walls, new brass fittings and ocean-facing windows",
         hero="a glass lantern room glowing above the sea"),
    dict(name="grand hotel",
         decay="boarded windows and a collapsed marquee",
         gut="a gutted lobby with bare marble and exposed columns",
         polish="restored marble floors, gilded trim and velvet seating",
         hero="a sweeping marble staircase under a crystal chandelier"),
    dict(name="plantation house",
         decay="sagging columns and a vine-covered veranda",
         gut="stripped floors and bare brick fireplaces",
         polish="repainted white columns, polished floors and new shutters",
         hero="a candlelit dining hall with a long mahogany table"),
    dict(name="Art Deco theater",
         decay="a shattered marquee and peeling gold leaf",
         gut="a stripped auditorium with exposed steel and plaster",
         polish="restored gold-leaf ceilings and deep red velvet seats",
         hero="a glowing neon marquee over a restored lobby"),
    dict(name="stone church",
         decay="a caved-in roof and broken stained glass",
         gut="an open nave with bare stone and new roof trusses",
         polish="restored stained glass and warm oak floors",
         hero="a vaulted living space lit by tall stained-glass windows"),
    dict(name="water tower",
         decay="rusted steel legs and a peeling tank",
         gut="a bare steel shell with an open spiral stair",
         polish="warm wood floors and new panoramic windows",
         hero="a round living room with panoramic views at sunset"),
    dict(name="grain silo",
         decay="rust streaks and a broken hatch",
         gut="a hollow concrete shell with raw walls",
         polish="polished concrete, steel stairs and tall slot windows",
         hero="a glowing round living space with a steel spiral stair"),
    dict(name="mountain cabin",
         decay="a sunken roof and moss-covered logs",
         gut="bare logs and open rafters",
         polish="chinked logs, a new stone chimney and warm lighting",
         hero="a huge stone fireplace beside a wall of mountain-view glass"),
    dict(name="stone mill",
         decay="broken windows and a seized waterwheel",
         gut="bare stone floors and heavy timber beams",
         polish="restored beams, new glass and a repaired waterwheel",
         hero="a glass-walled living room over the rushing millrace"),
    dict(name="train depot",
         decay="a rotting platform and faded paint",
         gut="a stripped waiting hall with exposed rafters",
         polish="restored plank floors, brass lamps and arched windows",
         hero="a grand hall lit by tall arched windows and iron lanterns"),
    dict(name="backyard pool estate",
         decay="a cracked empty pool full of leaves and green water",
         gut="a drained pool shell, raw concrete and fresh tile going in",
         polish="fresh plaster, stone coping and sun loungers",
         hero="a glowing infinity-edge pool at dusk beside a fire pit"),
    dict(name="schoolhouse",
         decay="a leaning bell tower and broken windows",
         gut="bare plank floors and open rafters",
         polish="refinished floors, tall new windows and fresh white paint",
         hero="a restored bell tower glowing at sunset"),
    dict(name="firehouse",
         decay="a rusted garage door and peeling red brick",
         gut="a bare brick hall with exposed steel beams",
         polish="polished concrete floors, arched glass doors and brass poles",
         hero="a double-height great room behind restored red arched doors"),
]

BACKSTORIES = [
    "Its last owner vanished, and the bank forgot it existed.",
    "A family feud kept it locked up in court for decades.",
    "After a storm took the roof, nobody wanted to pay for repairs.",
    "The town wanted it torn down.",
    "Squatters and raccoons were its only residents.",
    "A rumor of fire scared off every buyer.",
    "The heirs lived overseas and stopped paying the taxes.",
    "It sat on the market for years without a single offer.",
    "Inspectors called it unsafe and walked away.",
    "Vines swallowed the front doors long ago.",
    "The owner went bankrupt and left everything behind.",
    "Local kids swore it was haunted.",
]

BUYERS = [
    "a retired contractor", "a young couple with a tiny budget", "a former set designer",
    "a stubborn local carpenter", "a mother and daughter team", "a woman who had driven past it for years",
    "an out-of-state investor", "two brothers who were builders", "a retired Navy veteran",
    "a first-time buyer",
]

HOOKS = [  # (template, instruction for LLM)
    ("This {prop} in {place} sat abandoned for {years} years.",
     "Start with how many years it sat abandoned"),
    ("Nobody wanted this {prop} in {place}, not even for {low}.",
     "Start with the fact that nobody wanted it even for the low price"),
    ("{low}. That's all this {prop} in {place} cost.",
     "Start with the price alone as a shock, then explain"),
    ("Locals in {place} wanted this {prop} torn down.",
     "Start with locals wanting it demolished"),
    ("They bought this ruined {prop} in {place} for just {low}.",
     "Start with the buyer purchasing the ruin for the low price"),
    ("Everyone in {place} said this {prop} was a lost cause.",
     "Start with everyone calling it a lost cause"),
    ("Would you pay {low} for {a_prop} in {place}? Wait for the ending.",
     "Start with a direct question to the viewer about paying the low price"),
    ("This {prop} in {place} was left to rot for {years} years. Then everything changed.",
     "Start with years of rot, then a turning point"),
]

TURNS = [
    "Then {buyer} walked in and saw what everyone else missed.",
    "Then {buyer} made an offer, and people laughed.",
    "Then {buyer} saw potential where everyone else saw problems.",
    "Then {buyer} bought it and started working.",
    "That is when {buyer} stepped in with a wild plan.",
    "{Buyer} took one look and refused to walk away.",
    "Then {buyer} decided to bet everything on it.",
    "Only {buyer} could picture what it could become.",
]

WORKS = [
    "Months of brutal work left {gut}.",
    "Demolition revealed {gut}.",
    "The crew worked for months and uncovered {gut}.",
    "Strip-out day left behind {gut}.",
    "After the teardown, all that remained was {gut}.",
    "Week after week, the crew exposed {gut}.",
    "The first big milestone: {gut}.",
    "Only {gut} survived the demolition.",
]

POLISHES = [
    "Then came the finishing touches: {polish}.",
    "Slowly it filled with {polish}.",
    "Next, the crew added {polish}.",
    "The transformation continued with {polish}.",
    "Piece by piece, it gained {polish}.",
    "Soon the place showed {polish}.",
    "The details started to shine: {polish}.",
    "Finally, they installed {polish}.",
]

HEROES = [
    "The showpiece: {hero}.",
    "And the final reveal was {hero}.",
    "The jaw-dropping centerpiece is {hero}.",
    "At the heart of it all: {hero}.",
    "The last thing you notice is {hero}.",
    "The crown jewel? {Hero}.",
    "Everything builds toward {hero}.",
    "Then comes the moment you see {hero}.",
]

PAYOFFS = [
    "Today it's worth {value}.",
    "It's now valued at {value}.",
    "Appraisers now put it at {value}.",
    "Final value? {value}.",
    "Bought for {low}. Worth {value} today.",
    "From {low} to {value}.",
    "The new value: {value}.",
    "Today, it's a {value} property.",
]

ENDINGS = [
    "Would you have bought it?", "Follow for the next transformation.",
    "Comment the next ruin you want to see.", "Which stage was your favorite?",
    "Would you live here?", "Tell me where to look next.",
    "Follow, there's a new ruin coming soon.", "Would you have taken that risk?",
    "Which one should we restore next?", "Drop your dream property below.",
]

TITLES = [
    "This Abandoned {Prop} in {state} Is Now Worth {value}",
    "{low} Ruin to {value} Dream: {Prop} in {city}",
    "Nobody Believed in This {city} {Prop}, Now It's {value}",
    "{Prop} Abandoned {years} Years: {low} to {value}",
    "They Bought This {Prop} in {city} for {low}",
    "{city} Said Tear It Down. It's Now Worth {value}",
    "From {low} Ruin to {value} {Prop}",
    "The {low} {Prop} in {city} That Became {value}",
]

DESCS = [
    "Abandoned for {years} years, this {prop} in {place} was bought for {low} and rebuilt into a {value} showpiece.\n\nFollow for more abandoned-to-luxury transformations.\n\n#Shorts #AbandonedPlaces #Transformation #{tag}",
    "From {low} ruin to {value} dream. Watch this {prop} in {place} come back to life.\n\nWhich stage was your favorite?\n\n#Shorts #BeforeAndAfter #HomeRenovation #{tag}",
    "Nobody wanted it. {Buyer} bought this {prop} in {place} for {low}. Today it's worth {value}.\n\n#Shorts #AbandonedHouse #LuxuryHomes #{tag}",
]

BASE_TAGS = ["abandoned places", "home transformation", "before and after", "luxury homes",
             "house flip", "restoration", "abandoned house", "real estate", "dream home", "shorts"]

LOW_PRICES = [15000, 25000, 40000, 60000, 85000, 120000, 175000, 250000]
# mehengha shohor e $15K er castle oshomvob lage -> sekhane minimum $120K
EXPENSIVE = {"Newport", "Nantucket", "Napa", "Carmel", "Jackson", "Telluride", "Park City",
             "Sun Valley", "Key West", "Sedona", "Santa Fe", "Kauai", "Cape May", "Hudson",
             "Charleston", "Savannah", "Annapolis", "Whitefish"}
DISCLOSURE = "AI-generated fictional story and visuals."
MULTS = [6, 8, 10, 12, 15, 20, 25]

# cooldown windows: koyta video porjonto ek-i jinish abar ashbe na
DESCS = [d.replace("\n\n#Shorts", "\n\n" + DISCLOSURE + "\n\n#Shorts", 1) for d in DESCS]

WINDOWS = dict(loc=20, state=5, prop=8, backstory=5, buyer=4, hook=4, turn=3, work=3,
               polish=3, hero=3, payoff=3, ending=4, title=4, desc=2)


# ---------------------------------------------------------------- HELPERS
def a(x):
    return ("an " if x[:1].lower() in "aeiou" else "a ") + x


def cap(s):
    return s[:1].upper() + s[1:]


def titlecase(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


def money(n):
    if n >= 1_000_000:
        s = f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"${s}M"
    return f"${n // 1000}K"


def _recent(history, name, window):
    out = []
    for h in history[-window:] if window > 0 else []:
        if isinstance(h, dict) and name in h.get("pick", {}):
            out.append(h["pick"][name])
    return set(out)


def choose(name, n, history, rnd):
    window = min(WINDOWS[name], n - 1)
    recent = _recent(history, name, window)
    pool = [i for i in range(n) if i not in recent] or list(range(n))
    return rnd.choice(pool)


# ---------------------------------------------------------------- BRIEF
def pick_brief(history, rnd=None):
    rnd = rnd or random.Random()
    used_pairs = {(h["pick"].get("loc"), h["pick"].get("prop"))
                  for h in history if isinstance(h, dict) and "pick" in h}

    pick = {}
    for _ in range(40):
        recent_loc = _recent(history, "loc", WINDOWS["loc"])
        recent_states = {LOCATIONS[i][1] for i in _recent(history, "loc", WINDOWS["state"])
                         if i < len(LOCATIONS)}
        pool = [i for i in range(len(LOCATIONS))
                if i not in recent_loc and LOCATIONS[i][1] not in recent_states]
        loc = rnd.choice(pool or [i for i in range(len(LOCATIONS)) if i not in recent_loc]
                         or list(range(len(LOCATIONS))))
        prop = choose("prop", len(PROPS), history, rnd)
        if (loc, prop) not in used_pairs:
            break
    pick["loc"], pick["prop"] = loc, prop
    for name, items in (("backstory", BACKSTORIES), ("buyer", BUYERS), ("hook", HOOKS),
                        ("turn", TURNS), ("work", WORKS), ("polish", POLISHES),
                        ("hero", HEROES), ("payoff", PAYOFFS), ("ending", ENDINGS),
                        ("title", TITLES), ("desc", DESCS)):
        pick[name] = choose(name, len(items), history, rnd)

    city, state, setting = LOCATIONS[loc]
    p = PROPS[prop]
    low = rnd.choice([x for x in LOW_PRICES if x >= 120000] if city in EXPENSIVE else LOW_PRICES)
    value = low * rnd.choice(MULTS)
    f = dict(
        city=city, state=state, place=f"{city}, {state}", setting=setting,
        prop=p["name"], a_prop=a(p["name"]), Prop=titlecase(p["name"]),
        years=rnd.randint(8, 60), low=money(low), value=money(value),
        buyer=BUYERS[pick["buyer"]], Buyer=cap(BUYERS[pick["buyer"]]),
        decay=p["decay"], gut=p["gut"], polish=p["polish"], hero=p["hero"], Hero=cap(p["hero"]),
        tag=re.sub(r"[^A-Za-z]", "", city),
    )
    return dict(pick=pick, f=f)


# ---------------------------------------------------------------- OUTPUT PIECES
def image_scenes(b):
    f = b["f"]
    anchor = f"{cap(f['prop'])} in {f['place']}, {f['setting']}"
    common = (f"photorealistic, vertical 9:16, anamorphic lens, Arri Alexa color science, "
              f"cinematic restraint, {f['setting']}, the same {f['prop']} in {f['place']} in every scene, "
              f"no people, no faces, no text, no watermark")
    return [
        {"name": "Decay", "image_prompt": f"{anchor}. Exterior of the abandoned {f['prop']}, "
                                          f"{f['decay']}, overgrown, overcast moody light, {common}"},
        {"name": "Gut", "image_prompt": f"{anchor}. Interior of the same {f['prop']} mid-renovation, {f['gut']}, "
                                        f"work lights and dust in the air, {common}"},
        {"name": "Polish", "image_prompt": f"{anchor}. Interior of the same {f['prop']} nearly finished, "
                                           f"{f['polish']}, soft warm light, {common}"},
        {"name": "Hero", "image_prompt": f"{anchor}. Final reveal of the same {f['prop']} fully restored, "
                                         f"{f['hero']}, golden hour, luxurious, {common}"},
    ]


def make_title(b):
    f = b["f"]
    first = b["pick"]["title"]
    for k in range(len(TITLES)):
        t = TITLES[(first + k) % len(TITLES)].format(**f)
        if len(t) <= 70:
            b["pick"]["title"] = (first + k) % len(TITLES)
            return t
    return TITLES[0].format(**f)[:70]


def make_description_and_tags(b):
    f = b["f"]
    desc = DESCS[b["pick"]["desc"]].format(**f)
    tags = BASE_TAGS + [f["city"].lower(), f["state"].lower(), f["prop"]]
    return desc, tags


def template_voiceover(b):
    f, p = b["f"], b["pick"]
    parts = [HOOKS[p["hook"]][0], BACKSTORIES[p["backstory"]], TURNS[p["turn"]],
             WORKS[p["work"]], POLISHES[p["polish"]], HEROES[p["hero"]],
             PAYOFFS[p["payoff"]], ENDINGS[p["ending"]]]
    return " ".join(x.format(**f) for x in parts)


def opener(text, n=6):
    return " ".join(re.findall(r"[a-z0-9$']+", text.lower())[:n])


def finalize(b, title, voiceover):
    f = b["f"]
    desc, tags = make_description_and_tags(b)
    return {
        "concept": f"{f['prop']} | {f['place']}",
        "title": title, "description": desc, "tags": tags, "voiceover": voiceover,
        "scenes": image_scenes(b),
        "history": {"concept": f"{f['prop']} | {f['place']}", "pick": b["pick"],
                    "opener": opener(voiceover), "date": time.strftime("%Y-%m-%d")},
    }


def write_template(b):
    return finalize(b, make_title(b), template_voiceover(b))


# ---------------------------------------------------------------- LLM SIDE
def llm_prompt(b):
    f, p = b["f"], b["pick"]
    return f"""Write a YouTube Shorts voiceover script (85-100 words) and a title (max 70 characters) for a faceless channel about abandoned properties turned into luxury.

Facts you MUST use exactly, do not invent others:
- Property: {f['a_prop']} in {f['place']}, abandoned for {f['years']} years
- Why it was abandoned: {BACKSTORIES[p['backstory']]}
- Bought for {f['low']}. Worth today: {f['value']}
- Buyer: {f['buyer']}
- Before: {f['decay']}
- During renovation: {f['gut']}
- Finished: {f['polish']}
- Showpiece: {f['hero']}

Style: the first sentence is a hook. {HOOKS[p['hook']][1]}. Short punchy sentences, plain spoken English, no emojis, no stage directions. End with a short call to action similar to: "{ENDINGS[p['ending']]}"
Return ONLY JSON: {{"title": "...", "voiceover": "..."}}"""


def from_llm(b, data, history):
    """LLM output validate kore. Thik na hole None (caller fallback korbe)."""
    vo = str(data.get("voiceover", "")).strip()
    title = str(data.get("title", "")).strip().strip('"')
    words = len(vo.split())
    if not (65 <= words <= 125) or b["f"]["value"] not in vo:
        return None
    if not title or len(title) > 75:
        title = make_title(b)
    recent_openers = {h.get("opener") for h in history[-15:] if isinstance(h, dict)}
    if opener(vo) in recent_openers:
        return None
    return finalize(b, title, vo)
