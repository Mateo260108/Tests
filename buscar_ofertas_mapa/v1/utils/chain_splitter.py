import json

from .translating import email_terms_translated

shared_fields = ("domain", "name", "web", "instagram", "facebook", "linkedin")


def extract_email_domain(place):
    raw_email = (place.get("email") or "").strip().lower()
    if "@" not in raw_email:
        return ""
    return raw_email.split("@", 1)[1].strip()


def chain_keys(place):
    keys = []

    exact_name = (place.get("name") or "").strip().lower()
    if exact_name:
        keys.append(("name_exact", exact_name))

    exact_web = (place.get("web") or "").strip().lower()
    if exact_web:
        keys.append(("web_exact", exact_web))

    email_domain = extract_email_domain(place)
    if email_domain:
        keys.append(("email_domain_exact", email_domain))

    for platform in ("instagram", "facebook", "linkedin"):
        exact_social = (place.get(platform) or "").strip()
        if exact_social:
            keys.append((f"{platform}_exact", exact_social))

    return keys


def separate_unique_and_chains(places, selected_columns=None, local_langs=None):
    n = len(places)
    if n == 0:
        return [], []

    discard_terms, _ = email_terms_translated(langs=local_langs)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    first_seen_by_key = {}
    for idx, place in enumerate(places):
        for key in chain_keys(place):
            if key in first_seen_by_key:
                union(first_seen_by_key[key], idx)
            else:
                first_seen_by_key[key] = idx

    groups = {}
    for idx in range(n):
        root = find(idx)
        groups.setdefault(root, []).append(places[idx])

    unique_places = []
    candidate_chains = []
    for members in groups.values():
        if len(members) == 1:
            unique_places.append(members[0])
        else:
            candidate_chains.append(members)

    candidate_fields = list(selected_columns) if selected_columns else [
        "name", "category", "web", "email", "phone",
        "instagram", "facebook", "linkedin", "lat", "lon", "score_s", "relevance"
    ]
    loc_base_fields = []
    for f in ["id"] + candidate_fields:
        if f not in loc_base_fields:
            loc_base_fields.append(f)

    chains_payload = []
    c_idx = 1

    for members in candidate_chains:
        general = {}
        shared_fields = set()

        for field in candidate_fields:
            vals = [str(m.get(field) or "").strip() for m in members]
            if all(vals) and len(set(vals)) == 1:
                general[field] = members[0].get(field)
                shared_fields.add(field)

        domains = [extract_email_domain(m) for m in members]
        if all(domains) and len(set(domains)) == 1:
            general["domain"] = domains[0]

        has_shared_chain_data = any(
            str(general.get(field) or "").strip()
            for field in shared_fields
        )
        if not has_shared_chain_data:
            unique_places.extend(members)
            continue

        locations = []
        for m in members:
            loc = {}
            for field in loc_base_fields:
                if field == "id":
                    if m.get("id"):
                        loc["id"] = m.get("id")
                    continue
                if field in shared_fields:
                    continue
                val = m.get(field, "")
                if val != "":
                    loc[field] = val
            locations.append(loc)

        chains_payload.append({
            "chain_id": f"chain_{c_idx}",
            "location_count": len(members),
            "general": general,
            "locations": locations,
        })
        c_idx += 1

    return unique_places, chains_payload


def save_chains_to_json(chains_payload, output_path="chains.json"):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chains_payload, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(chains_payload)} chains to {output_path}")