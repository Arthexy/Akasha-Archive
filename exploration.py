"""Normalize Battle Chronicle exploration without inventing missing progress."""
from enka_client import allowed_image
from pathlib import Path

ASSETS = Path(__file__).parent / "static/images/explore"

# Geography aliases only; progress and identifiers always come from HoYoLAB.
SPECIAL_REGIONS = {
    "Dragonspine": "Mondstadt",
    "Chenyu Vale": "Liyue", "The Chasm": "Liyue",
    "Enkanomiya": "Inazuma", "Sea of Bygone Eras": "Fontaine",
    "Ancient Sacred Mountain": "Natlan", "Frost Moon": "Nod-Krai",
}
MAP_ICONS = {"Ancient Sacred Mountain": "sacred-mountain", "Temple of Space": "temple-of-space",
             "Frost Moon": "frost-moon"}
MOON_AREAS = {"dark side of the moon", "lunar island", "lunar isle", "moontide isle", "moontide isles", "moontide island", "moontide islands", "moontide side"}


def percent(value):
    if value is None:
        return None
    return min(100, max(0, float(value) / 10))


def average(values):
    available = [v for v in values if v is not None]
    return round(sum(available) / len(available), 2) if available else None


def normalize_exploration(raw):
    entries = []
    for item in raw:
        def image(key):
            value = item.get(key)
            return value if allowed_image(value) else None
        offerings = [{"name": o.get("name", ""), "level": o.get("level"),
                      "icon": o.get("icon") if allowed_image(o.get("icon")) else None,
                      "locked": o.get("open_state") == "OfferingOpenStateLocked"}
                     for o in item.get("offerings", [])]
        tribes = [{"name": t.get("name", ""), "level": t.get("level"),
                   "icon": t.get("icon") if allowed_image(t.get("icon")) else None}
                  for t in (item.get("natan_reputation") or {}).get("tribal_list", [])]
        entries.append({"id": str(item["id"]), "parent_id": str(item.get("parent_id", 0)),
            "name": item.get("name", ""), "progress": percent(item.get("exploration_percentage")),
            "icon": image("icon"), "background": image("background_image"),
            "statue_level": item.get("seven_statue_level") or None,
            "reputation_level": item.get("level") if item.get("type") == "Reputation" and item.get("level") else None,
            "offerings": offerings, "tribes": tribes,
            "areas": [{"name": a.get("name", ""), "progress": percent(a.get("exploration_percentage"))}
                      for a in item.get("area_exploration_list", [])],
            "special": item.get("world_type", 2 if item.get("type") == "Reputation" else 1) != 2,
            "included_in_main": False})
    roots = [e for e in entries if e["parent_id"] == "0"]
    for entry in roots:
        children = [e for e in entries if e["parent_id"] == entry["id"]]
        if children:
            entry["areas"].extend({"name": c["name"], "progress": c["progress"]} for c in children)
            # Chenyu's root value can be zero while its child areas have progress.
            values = [c["progress"] for c in children]
            if entry["name"] != "Chenyu Vale":
                entry["areas"].insert(0, {"name": entry["name"], "progress": entry["progress"]})
                values.insert(0, entry["progress"])
            if entry["special"] or entry["name"] in SPECIAL_REGIONS:
                entry["progress"] = average(values)
    mondstadt = next((e for e in roots if e["name"] == "Mondstadt"), None)
    if mondstadt:
        for wind in [e for e in roots if e["name"] == "Windrest Peak"]:
            names = {a["name"] for a in mondstadt["areas"]}
            mondstadt["areas"].extend(a for a in (wind["areas"] or [{"name": wind["name"], "progress": wind["progress"]}]) if a["name"] not in names)
            roots.remove(wind)
    # These maps belong to their nation even when the provider marks them as roots.
    for entry in roots:
        if entry["name"] in SPECIAL_REGIONS:
            entry["special"] = True
    nations = {e["name"]: e for e in roots if not e["special"]}
    for entry in roots:
        owner = nations.get(SPECIAL_REGIONS.get(entry["name"]))
        entry["group_id"] = owner["id"] if owner and entry["name"] not in {"Chenyu Vale", "The Chasm"} else entry["id"]
        entry["group_name"] = owner["name"] if owner else entry["name"]
    # HoYoLAB reports this separate-map area inside Nod-Krai's main aggregate.
    nod = nations.get("Nod-Krai")
    if nod:
        moon = [a for a in nod["areas"] if a["name"].casefold() in MOON_AREAS]
        if moon:
            nod["areas"] = [a for a in nod["areas"] if a not in moon]
            frost = next((e for e in roots if e["name"] == "Frost Moon"), None)
            if frost:
                frost["areas"].extend(a for a in moon if a["name"] not in {b["name"] for b in frost["areas"]})
            else:
                roots.append({**nod, "id": nod["id"] + "-frost-moon", "name": "Frost Moon",
                "progress": average([a["progress"] for a in moon]), "areas": moon, "offerings": [], "tribes": [],
                "statue_level": None, "reputation_level": None, "special": True,
                "included_in_main": True, "icon": None, "background": None,
                "group_id": nod["id"], "group_name": nod["name"]})
    groups = []
    for entry in roots:
        for kind in ("logo", "background"):
            filename = f"region-{entry['id']}-{kind}.png"
            if (ASSETS / filename).is_file():
                entry["local_icon" if kind == "logo" else "local_background"] = "/static/images/explore/" + filename
        if entry["name"] in MAP_ICONS:
            entry["local_icon"] = "/static/images/explore/" + MAP_ICONS[entry["name"]] + ".png"
            entry["local_background"] = "/static/images/explore/" + MAP_ICONS[entry["name"]] + "-background.png"
        if entry["group_id"] != entry["id"]:
            continue
        components = [e for e in roots if e["group_id"] == entry["id"] and not e["included_in_main"]]
        groups.append({"id": entry["id"], "name": entry["name"],
                       "progress": average([e["progress"] for e in components])})
    roots.sort(key=lambda e: (e["special"], int(e["group_id"]), e["id"]))
    groups.sort(key=lambda g: int(g["id"]))
    return {"regions": roots, "groups": groups}
