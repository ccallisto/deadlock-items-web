"""Build items.json for Deadlock items: name, category, tier, cost, description, stats, icon."""
import json, os, re, sys

KV3, LOCDIR, ICONDIR, OUT = sys.argv[1:5]
PRICES = [0, 800, 1600, 3200, 6400, 9999]
CATEGORY = {"EItemSlotType_WeaponMod": "weapon", "EItemSlotType_Armor": "vitality", "EItemSlotType_Tech": "spirit"}

# ---------- KV3 text parser ----------
TOK = re.compile(r'\s+|//[^\n]*|"(?:[^"\\]|\\.)*"|[{}\[\]=,]|[A-Za-z_][\w.]*:(?=\s*["{\[])|[^\s{}\[\]=,"]+')

def tokenize(text):
    for m in TOK.finditer(text):
        t = m.group(0)
        if t.isspace() or t.startswith("//"):
            continue
        yield t

def parse(tokens):
    tokens = list(tokens); pos = 0
    def value():
        nonlocal pos
        t = tokens[pos]; pos += 1
        if t.endswith(":") and not t.startswith('"'):  # typed prefix: panorama:"..", subclass:{..}
            return value()
        if t == "{":
            obj = {}
            while tokens[pos] != "}":
                k = tokens[pos].strip('"'); pos += 2  # key, '='
                obj[k] = value()
            pos += 1
            return obj
        if t == "[":
            arr = []
            while tokens[pos] != "]":
                if tokens[pos] == ",": pos += 1; continue
                arr.append(value())
            pos += 1
            return arr
        if t.startswith('"'):
            return t[1:-1].replace('\\"', '"')
        return t
    return value()

text = open(KV3, encoding="utf-8", errors="replace").read()
text = text[text.index("<!-- kv3"):]
text = text[text.index("\n") + 1:]
data = parse(tokenize(text))

# ---------- localization ----------
def load_loc(path):
    out = {}
    for m in re.finditer(r'^\s*"([^"]+)"\s+"((?:[^"\\]|\\.)*)"', open(path, encoding="utf-8-sig").read(), re.M):
        out.setdefault(m.group(1), m.group(2).replace('\\"', '"').replace("\\n", "\n"))
    return out

loc = {}
for sub in ("citadel_gc_mod_names", "citadel_mods", "citadel_attributes", "citadel_gc"):
    p = os.path.join(LOCDIR, sub, f"{sub}_english.txt")
    if os.path.exists(p):
        for k, v in load_loc(p).items():
            loc.setdefault(k, v)

def fmt_num(s):
    try:
        f = float(str(s).rstrip("m"))
        return str(int(f)) if f == int(f) else str(round(f, 2))
    except ValueError:
        return str(s)

def humanize(name):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)

def render(s, props):
    def sub(m):
        kind, arg = m.group(1), m.group(2)
        if kind == "s":
            p = props.get(arg)
            return fmt_num(p["m_strValue"]) if isinstance(p, dict) and "m_strValue" in p else arg
        arg = arg.split(":", 1)[-1].strip("'")
        if m.group(0).startswith("{g:citadel_binding"):
            return f"[{arg}]"
        return loc.get(f"{arg}_label") or humanize(arg)
    s = re.sub(r"\{([sgi]):([^}]*)\}", sub, s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    return s

def strip_html(s):
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"<[^>]+>", "", s)).strip()

def find_loc_strings(node, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "m_strLocString" and isinstance(v, str) and v.startswith("#"):
                acc.append(v[1:])
            else:
                find_loc_strings(v, acc)
    elif isinstance(node, list):
        for v in node:
            find_loc_strings(v, acc)
    return acc

def important_props(node, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "m_strImportantProperty":
                acc.append(v)
            elif k in ("m_vecAbilityProperties", "m_vecElevatedAbilityProperties") and isinstance(v, list):
                acc.extend(x for x in v if isinstance(x, str))
            else:
                important_props(v, acc)
    elif isinstance(node, list):
        for v in node:
            important_props(v, acc)
    return acc

def stat_line(key, p):
    val = p.get("m_strValue")
    if val is None or fmt_num(val) in ("0", ""):
        return None
    label = loc.get(f"{key}_label") or loc.get(f"{key}_postvalue_label")
    if not label:
        return None
    post = loc.get(f"{key}_postfix", "")
    if "{" in post: post = ""
    pre = loc.get(f"{key}_prefix", "")
    v = fmt_num(val)
    sign = "+" if "{s:sign}" in pre and not v.startswith("-") else ""
    units = p.get("m_eDisplayUnits", "")
    if not post and units == "EDisplayUnit_Meters": post = "m"
    if not post and key in ("AbilityCooldown", "AbilityDuration"): post = "s"
    return {"key": key, "label": label, "value": f"{sign}{v}{post}"}

def truthy(v):
    return str(v).strip('"').lower() in ("true", "1")

items = []
for key, v in data.items():
    if not isinstance(v, dict) or v.get("m_eAbilityType") != "EAbilityType_Item":
        continue
    if truthy(v.get("m_bDisabled", "false")) or not key.startswith("upgrade_"):
        continue  # removed / test items
    icon_src = v.get("m_strShopIconLarge") or ""
    m = re.search(r"\{images\}/items/(.+)\.psd", icon_src)
    if not m:
        continue
    icon_rel = f"{m.group(1)}_psd.png"
    icon_ok = os.path.exists(os.path.join(ICONDIR, icon_rel))
    props = v.get("m_mapAbilityProperties", {}) or {}
    tier = int(str(v.get("m_iItemTier", "EModTier_0")).rsplit("_", 1)[-1])
    mode = "street_brawl" if m.group(1).startswith("brawl/") else "standard"
    desc_keys = find_loc_strings(v.get("m_vecTooltipSectionInfo", []), [])
    if not desc_keys and f"{key}_desc" in loc:
        desc_keys = [f"{key}_desc"]
    desc_html = "\n\n".join(render(loc[k], props) for k in desc_keys if k in loc)
    seen, stats = set(), []
    for pk in important_props(v.get("m_vecTooltipSectionInfo", []), []):
        if pk in seen or pk not in props: continue
        seen.add(pk)
        s = stat_line(pk, props[pk])
        if s: stats.append(s)
    items.append({
        "id": key,
        "name": loc.get(key) or humanize(key.removeprefix("upgrade_")),
        "category": CATEGORY.get(str(v.get("m_eItemSlotType")), "other"),
        "tier": tier,
        "cost": PRICES[tier] if 0 <= tier < len(PRICES) else None,
        "mode": mode,
        "active": truthy(v.get("m_bIsActive", "false")) or v.get("m_eAbilityActivation") not in (None, "CITADEL_ABILITY_ACTIVATION_PASSIVE"),
        "description": strip_html(desc_html),
        "description_html": desc_html.replace("\n", "<br>"),
        "stats": stats,
        "icon": icon_rel if icon_ok else None,
    })

items.sort(key=lambda i: (i["mode"], i["category"], i["tier"], i["name"]))
json.dump(items, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"wrote {len(items)} items -> {OUT}")
