import os
import csv

discard_terms = (
    'noreply', 'no-reply', 'donotreply', 'privacy', 'gdpr', 'dpo',
    'webmaster', 'admin@', 'support', 'billing', 'invoice', 'accounting',
    'newsletter', 'press', 'media', 'security', 'abuse', 'postmaster'
)

max_priority = (
    'jobs', 'career', 'careers', 'work', 'hr', 'rekry', 'jobb', 'tyopaikat',
    'info', 'contact', 'kontakt', 'post', 'office', 'hello', 'hei',
    'reception', 'frontdesk', 'stay', 'mail'
)

def select_best_email(emails):
    if not emails:
        return None

    data = [e.strip().lower() for e in emails.split(',') if '@' in e]
    valid = [e for e in data if not e.startswith(discard_terms)]
    if not valid:
        return None

    for prefix in max_priority:
        for email in valid:
            email_prefix = email.split('@')[0]
            if email_prefix == prefix or email_prefix.startswith(prefix):
                return email

    return valid[0]

def read_csv(my_path):
    if not os.path.exists(my_path):
        return []

    with open(my_path, "r", encoding="utf-8") as file:
        return list(csv.DictReader(file, delimiter='\t'))

def save_best_email_to_csv(my_path, rows):
    if not rows:
        print(f"No data available to save to {my_path}")
        return 

    fieldnames = rows[0].keys()
    with open(my_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

def final_email_list(iso_code):
    folder = f"{iso_code}_filtered"

    direct_emails = os.path.join(folder, f"email_list_{iso_code}.csv")
    scraped_emails = os.path.join(folder, f"scraped_emails_{iso_code}.csv")
    output_path = os.path.join(folder, f"all_emails_{iso_code}.csv")

    rows_direct = read_csv(direct_emails)
    rows_scraped = read_csv(scraped_emails)

    seen_emails = set()
    seen_ids = set()
    finals = []

    for row in (rows_direct + rows_scraped):
        values = list(row.values())
        id = row.get('id') or (values[0] if values else '') 
        if id in seen_ids:
            continue

        best_email = select_best_email(row.get('email', ''))
        if not best_email or best_email in seen_emails:
            continue

        row['email'] = best_email
        seen_emails.add(best_email)
        if id:
            seen_ids.add(id)
        finals.append(row)

    save_best_email_to_csv(output_path, finals)

if __name__ == "__main__":
    final_email_list("IS")