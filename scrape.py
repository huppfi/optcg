#!/usr/bin/env python3
"""
One Piece TCG -> TCG Arena Card List Generator
==============================================
Fetches all One Piece cards from https://optcgapi.com and generates
a CardList.json file compatible with TCG Arena (tcg-arena.fr).

Usage:
    pip install requests
    python generate_optcg_cards.py

Output: CardList.json (in the same directory)
"""

import requests
import json
import time
import sys

API_BASE = "https://optcgapi.com/api"

# All known set IDs
SET_IDS = [
    "OP-01", "OP-02", "OP-03", "OP-04", "OP-05", "OP-06", "OP-07", "OP-08",
    "OP-09", "OP-10", "OP-11", "OP-12", "OP-13", "OP-14",
    "EB-01", "EB-02",
    "PRB-01",
]

# All known starter deck IDs
ST_IDS = [
    "ST-01", "ST-02", "ST-03", "ST-04", "ST-05", "ST-06", "ST-07", "ST-08",
    "ST-09", "ST-10", "ST-11", "ST-12", "ST-13", "ST-14", "ST-15", "ST-16",
    "ST-17", "ST-18", "ST-19", "ST-20", "ST-21",
]


def fetch_json(url):
    """Fetch JSON from a URL with error handling."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else []
        else:
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def fetch_all_cards():
    """Try bulk endpoints first, fall back to per-set fetching."""
    all_raw = []
    seen = set()

    def add_cards(cards):
        count = 0
        for card in cards:
            cid = card.get("card_set_id", "")
            img_id = card.get("card_image_id") or ""
            # Skip parallel/alternate art (_p1, _p2, etc.)
            if "_p" in img_id:
                continue
            if cid and cid not in seen:
                seen.add(cid)
                all_raw.append(card)
                count += 1
        return count

    # --- Try bulk endpoints first ---
    print("Trying bulk endpoint /api/allSetCards/ ...")
    bulk = fetch_json(f"{API_BASE}/allSetCards/")
    if bulk:
        n = add_cards(bulk)
        print(f"  Got {n} unique cards from bulk set endpoint")
    else:
        print("  Bulk unavailable, fetching per set...")
        for sid in SET_IDS:
            print(f"  Fetching {sid}...", end=" ", flush=True)
            cards = fetch_json(f"{API_BASE}/sets/{sid}/")
            n = add_cards(cards)
            print(f"{n} new cards")
            time.sleep(0.5)

    print("\nTrying bulk endpoint /api/allSTCards/ ...")
    bulk_st = fetch_json(f"{API_BASE}/allSTCards/")
    if bulk_st:
        n = add_cards(bulk_st)
        print(f"  Got {n} new unique cards from bulk ST endpoint")
    else:
        print("  Bulk unavailable, fetching per deck...")
        for sid in ST_IDS:
            print(f"  Fetching {sid}...", end=" ", flush=True)
            cards = fetch_json(f"{API_BASE}/decks/{sid}/")
            n = add_cards(cards)
            print(f"{n} new cards")
            time.sleep(0.5)

    print("\nFetching promo cards (PRB-01)...")
    promos = fetch_json(f"{API_BASE}/sets/PRB-01/")
    if promos:
        n = add_cards(promos)
        print(f"  Got {n} new unique promo cards")

    return all_raw


def convert_to_tcg_arena(raw_cards):
    """
    Convert raw API cards to TCG Arena CardList.json format.
    Uses the actual card number (e.g. OP01-001) as both the key and id.
    """
    card_list = {}

    for raw in raw_cards:
        card_set_id = raw.get("card_set_id", "")
        if not card_set_id:
            continue

        card_name = raw.get("card_name", "Unknown")
        card_type = raw.get("card_type", "Character")
        card_cost = raw.get("card_cost")
        card_power = raw.get("card_power")
        card_color = raw.get("card_color", "")
        card_text = raw.get("card_text", "")
        life = raw.get("life")
        counter = raw.get("counter_amount")
        attribute = raw.get("attribute", "")
        sub_types = raw.get("sub_types", "")
        rarity = raw.get("rarity", "")
        set_name = raw.get("set_name", "")
        image_url = raw.get("card_image", "")

        # Derive short set code from card_set_id (e.g. "OP01-077" -> "OP01")
        set_code = card_set_id.rsplit("-", 1)[0] if "-" in card_set_id else card_set_id

        # Normalize values to strings
        try:
            cost_val = str(int(card_cost)) if card_cost is not None else "0"
        except (ValueError, TypeError):
            cost_val = "0"

        try:
            power_val = str(int(card_power)) if card_power is not None else "0"
        except (ValueError, TypeError):
            power_val = "0"

        try:
            counter_val = str(int(counter)) if counter is not None else "0"
        except (ValueError, TypeError):
            counter_val = "0"

        try:
            life_val = str(int(life)) if life is not None else "0"
        except (ValueError, TypeError):
            life_val = "0"

        # Stage cards are displayed horizontally in One Piece TCG
        is_horizontal = (card_type == "Stage")

        # Normalize cost to int for face.front.cost
        try:
            cost_int = int(card_cost) if card_cost is not None else 0
        except (ValueError, TypeError):
            cost_int = 0

        # Use actual card number as key and id (e.g. "OP01-001")
        card_list[card_set_id] = {
            "id": card_set_id,
            "name": card_name,
            "type": card_type,
            "face": {
                "front": {
                    "name": card_name,
                    "type": card_type,
                    "cost": cost_int,
                    "isHorizontal": is_horizontal,
                    "image": image_url,
                }
            },
            "Color": card_color,
            "cost": cost_int,
            "isHorizontal": is_horizontal,
            "Cost": cost_val,
            "Power": power_val,
            "Counter": counter_val,
            "Life": life_val,
            "Attribute": attribute,
            "Subtypes": sub_types,
            "Text": card_text,
            "Rarity": rarity,
            "Set": set_code,
        }

    return card_list


def main():
    print("=" * 60)
    print("  One Piece TCG -> TCG Arena Card List Generator")
    print("=" * 60)
    print()

    raw_cards = fetch_all_cards()

    if not raw_cards:
        print("\nNo cards fetched! Check your internet connection.")
        sys.exit(1)

    # Sort by set_id then card_set_id
    raw_cards.sort(key=lambda c: (c.get("set_id", ""), c.get("card_set_id", "")))

    print(f"\nConverting {len(raw_cards)} cards to TCG Arena format...")
    card_list = convert_to_tcg_arena(raw_cards)

    output_file = "CardList.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(card_list, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(card_list)} cards to {output_file}")

    # Summary
    type_counts = {}
    color_counts = {}
    set_counts = {}
    for card in card_list.values():
        t = card["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
        c = card.get("Color", "")
        if c:
            for color in c.split("/"):
                color_counts[color.strip()] = color_counts.get(color.strip(), 0) + 1
        s = card.get("Set", "")
        if s:
            set_counts[s] = set_counts.get(s, 0) + 1

    print(f"\nCard types:")
    for t, n in sorted(type_counts.items()):
        print(f"  {t}: {n}")
    print(f"\nColors:")
    for c, n in sorted(color_counts.items()):
        print(f"  {c}: {n}")
    print(f"\nSets:")
    for s, n in sorted(set_counts.items()):
        print(f"  {s}: {n}")
    print(f"\nDone! Host CardList.json and paste the URL into TCG Arena.")


if __name__ == "__main__":
    main()