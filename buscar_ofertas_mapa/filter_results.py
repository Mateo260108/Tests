import csv
import os

def filter_lines(my_file, iso_code):
    web_included = []
    email_included = []
    nothing_included = []
    try:
        with open(my_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter='\t')
            for row in reader:
                name = (row.get('name') or '').strip()
                if not name:
                    continue

                web_final = (row.get('website') or '').strip() or (row.get('contact:website') or '').strip()
                email_final = (row.get('email') or '').strip() or (row.get('contact:email') or '').strip()

                place = {
                    'id': row.get('@id', ''),
                    'name': name,
                    'type': (row.get('tourism') or '').strip(),
                    'lat': (row.get('@lat') or '').strip(),
                    'lon': (row.get('@lon') or '').strip(),
                    'web': web_final,
                    'email': email_final
                }

                if email_final:
                    email_included.append(place)
                elif web_final:
                    web_included.append(place)
                else:
                    nothing_included.append(place)

                results = [email_included, web_included, nothing_included]

        return results

    except OSError:
        print(f"File: {my_file} not found.")
        return

def save_to_csv(file_name, data_list, iso_code):
    if not data_list:
        print("No data to store")
        return

    folder_name = f"{iso_code}_filtered"
    os.makedirs(folder_name, exist_ok=True)
    full_path = os.path.join(folder_name, file_name)

    columns = data_list[0].keys()
    with open(full_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, delimiter="\t")
        writer.writeheader  
        writer.writerows(data_list)

