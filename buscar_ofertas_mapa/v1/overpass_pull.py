import requests
import os
import time

contact_email = os.getenv("USER_EMAIL", "generic_user@example.com")

def pull_list_from_api(iso_code):
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:60];
    area["ISO3166-1"="{iso_code.upper()}"][admin_level=2]->.searchArea;
    (
      nwr(area.searchArea)["tourism"="hostel"];
      nwr(area.searchArea)["tourism"="hotel"];
      nwr(area.searchArea)["tourism"="guest_house"];
    );
    out center;
    """
    headers = {
        "User-Agent": f"BuscadorHoteles/1.1 ({contact_email})"
    }

    for tries in range(5):
        try:
            response = requests.post(url, data={"data": query}, headers=headers, timeout=65)
            if response.status_code == 200:
                print("Request completed successfully. Pulling data...")
                elements = response.json().get("elements", [])
                results = []

                for el in elements:
                    tags = el.get("tags", {})
                    center = el.get("center", {})
                    lat = el.get("lat") if el.get("lat") is not None else center.get("lat", "")
                    lon = el.get("lon") if el.get("lon") is not None else center.get("lon", "")

                    results.append({
                        "id": f"{el.get('type', '')}/{el.get('id', '')}",
                        "name": tags.get("name", ""),
                        "lat": lat,
                        "lon": lon,
                        "category": tags.get("tourism", ""),
                        "web": tags.get("contact:website") or tags.get("website") or "",
                        "email": tags.get("contact:email") or tags.get("email") or "",
                        "phone": tags.get("contact:phone") or tags.get("phone") or "",
                    })
                return results

            if response.status_code in (429, 502, 503, 504):
                wait_time = 30 + (tries * 10)
                print(f"Status {response.status_code}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Request failed with status code {response.status_code}. No retry.")
                break

        except (requests.exceptions.RequestException, ValueError) as e:
            wait_time = 30 + (tries * 10)
            print(f"Request error ({e}). Retrying in {wait_time}s...")
            time.sleep(wait_time)

    print("Server was too busy or failed after retries.")
    return []