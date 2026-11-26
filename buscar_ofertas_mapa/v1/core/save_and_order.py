import csv

from utils import lambda_km, apply_proximity_order

def classify_relevance(html_text, positive_keywords, negative_keywords):
    if not html_text:
        return "regular"
    text_lower = html_text.lower()

    has_negative = any(kw in text_lower for kw in (negative_keywords or []))
    if has_negative:
        return "irrelevant"

    has_positive = any(kw in text_lower for kw in (positive_keywords or []))
    if has_positive:
        return "relevant"

    return "regular"

def order_by_relevance_and_proximity(
    places,
    reference_places,
    use_proximity=False,
    mode="rural",
    decay_km=lambda_km,
):
    relevant = [dict(p) for p in places if p.get("relevance") == "relevant"]
    regular = [dict(p) for p in places if p.get("relevance", "regular") == "regular"]
    irrelevant = [dict(p) for p in places if p.get("relevance") == "irrelevant"]

    if use_proximity:
        relevant = apply_proximity_order(relevant, reference_places, mode=mode, decay_km=decay_km)
        regular = apply_proximity_order(regular, reference_places, mode=mode, decay_km=decay_km)
        irrelevant = apply_proximity_order(irrelevant, reference_places, mode=mode, decay_km=decay_km)

    return relevant + regular + irrelevant

def filtering_output(rows, columns, allow_empty=True):
    if not rows or not columns:
        return []

    output = []
    for row in rows:
        if not allow_empty:
            has_all = all(str(row.get(col) or "").strip() != "" for col in columns)
            if not has_all:
                continue

        projected = {col: row.get(col, "") for col in columns}
        output.append(projected)

    return output

def save_to_csv(rows, output_path="email_list.csv"):
    print("Saving to CSV format file...")
    if not rows:
        print("No data to save.")
        return

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {output_path}")