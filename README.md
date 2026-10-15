# Deadlock Items

A fan-made item list and quiz for [Deadlock](https://store.steampowered.com/app/1422450/Deadlock/).
It's a static site with no backend; everything in `site/` is the web root.

- **Item list** (`items.html`): every shop item grouped by category and cost. Click an icon for its description and stats.
- **Quiz** (`index.html`): you're shown an item's icon, pick its name from 3 items in the same category, then pick its description.

## Run locally

```bash
cd site
python3 -m http.server 8765
```

Then open http://localhost:8765. The pages fetch `items.json`, so they have to be served over HTTP; opening the files directly won't work.

## Data

`site/items.json` and the icons are pulled from the game's own files:

| What | Where it comes from |
|---|---|
| Names | `game/citadel/resource/localization/citadel_gc_mod_names/*_english.txt` |
| Descriptions and stat labels | `.../citadel_mods/` and `.../citadel_attributes/` |
| Category, tier, stats, icon path | `scripts/abilities.vdata_c` inside `game/citadel/pak01_dir.vpk` |
| Cost per tier | `scripts/generic_data.vdata_c` (`m_nItemPricePerTier`) |
| Icons | `panorama/images/items/**` inside the VPK, converted to PNG |

### Rebuilding after a game patch

The scripts in `tools/` need [Source2Viewer-CLI](https://github.com/ValveResourceFormat/ValveResourceFormat/releases) (`cli-linux-x64.zip`).

- `vpk.py`: lists or extracts files from a VPK.
- `strip_red.py`: removes a resource's metadata block, which current Source2Viewer releases fail to parse for Deadlock's files.
- `build_map.py`: builds `items.json` from the decompiled ability data and the localization files.

```bash
GAME=~/.local/share/Steam/steamapps/common/Deadlock/game/citadel
mkdir -p work

# 1. Item data
python3 -I tools/vpk.py $GAME/pak01_dir.vpk '^scripts/abilities\.vdata_c$' work
python3 -I tools/strip_red.py work/scripts/abilities.vdata_c work/abilities.vdata_c
Source2Viewer-CLI -i work/abilities.vdata_c -b DATA > work/abilities.kv3

# 2. Icons (if any fail to convert, run strip_red.py on that file and convert it again)
Source2Viewer-CLI -i $GAME/pak01_dir.vpk --vpk_filepath panorama/images/items/ -d -o work/icons
cp -r work/icons/panorama/images/items/{weapon,vitality,spirit,brawl} site/

# 3. Map
python3 -I tools/build_map.py work/abilities.kv3 $GAME/resource/localization site site/items.json
```

Item prices are hard-coded in `build_map.py` (`PRICES`). Check them against `generic_data` if a patch changes costs.

## Legal

Not affiliated with or endorsed by Valve. Deadlock, its item names, descriptions and icons are property of Valve Corporation.
