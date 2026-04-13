from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

TICKETMASTER_API_KEY = (os.getenv("TICKETMASTER_API_KEY") or "").strip().strip('"')
SERPAPI_API_KEY = (os.getenv("SERPAPI_API_KEY") or "").strip().strip('"')
PREDICTHQ_API_KEY = (os.getenv("PREDICTHQ_API_KEY") or "").strip().strip('"')


def normalize_city(city):
    city = city.strip()
    lower = city.lower()

    if "washington" in lower:
        return "Washington"
    if "new york" in lower:
        return "New York"
    if "los angeles" in lower:
        return "Los Angeles"
    if "chicago" in lower:
        return "Chicago"
    if "san francisco" in lower:
        return "San Francisco"
    if "houston" in lower:
        return "Houston"
    if "miami" in lower:
        return "Miami"
    if "boston" in lower:
        return "Boston"

    return city.title()


def get_ticketmaster_events(city):
    if not TICKETMASTER_API_KEY:
        print("Ticketmaster key missing")
        return []

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "city": city,
        "size": 10,
        "sort": "date,asc"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        events = []
        for event in data.get("_embedded", {}).get("events", []):
            title = event.get("name")
            date = event.get("dates", {}).get("start", {}).get("localDate")

            venue = "Unknown"
            venues = event.get("_embedded", {}).get("venues", [])
            if venues:
                venue = venues[0].get("name", "Unknown")

            if title and date:
                events.append({
                    "title": title,
                    "date": date,
                    "venue": venue,
                    "source": "Ticketmaster"
                })

        return events

    except Exception as e:
        print("Ticketmaster error:", e)
        return []


def get_serpapi_events(city):
    if not SERPAPI_API_KEY:
        print("SerpApi key missing")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_events",
        "q": f"Events in {city}",
        "api_key": SERPAPI_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        events = []
        for event in data.get("events_results", [])[:10]:
            title = event.get("title")

            date_info = event.get("date")
            if isinstance(date_info, dict):
                date = date_info.get("start_date", "")
            else:
                date = str(date_info).strip() if date_info else ""

            address = event.get("address")
            if isinstance(address, list) and address:
                venue = address[0]
            else:
                venue = "Unknown"

            if title and date:
                events.append({
                    "title": title,
                    "date": date,
                    "venue": venue,
                    "source": "SerpApi"
                })

        return events

    except Exception as e:
        print("SerpApi error:", e)
        return []


def get_predicthq_events(city):
    if not PREDICTHQ_API_KEY:
        print("PredictHQ key missing")
        return []

    url = "https://api.predicthq.com/v1/events/"
    headers = {
        "Authorization": f"Bearer {PREDICTHQ_API_KEY}",
        "Accept": "application/json"
    }
    params = {
        "q": city,
        "limit": 3,
        "sort": "start"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        events = []
        for event in data.get("results", []):
            title = event.get("title")
            date = event.get("start", "")

            location = event.get("location")
            if isinstance(location, list):
                venue = "Location unavailable"
            elif location:
                venue = str(location)
            else:
                venue = "Location unavailable"

            if title and date:
                events.append({
                    "title": title,
                    "date": date,
                    "venue": venue,
                    "source": "PredictHQ"
                })

        return events

    except Exception as e:
        print("PredictHQ error:", e)
        return []


def remove_duplicates(events):
    seen = set()
    unique_events = []

    for event in events:
        key = (
            event.get("title", "").lower().strip(),
            event.get("date", "").lower().strip(),
            event.get("venue", "").lower().strip()
        )

        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    return unique_events


def sort_events(events):
    return sorted(events, key=lambda x: x.get("date", ""))


def balance_events(ticketmaster_events, serp_events, predicthq_events, max_total=12):
    balanced = []

    balanced.extend(ticketmaster_events[:4])
    balanced.extend(serp_events[:4])
    balanced.extend(predicthq_events[:2])

    remaining = ticketmaster_events[4:] + serp_events[4:] + predicthq_events[2:]

    for event in remaining:
        if len(balanced) >= max_total:
            break
        balanced.append(event)

    return balanced


@app.route("/")
def home():
    city = request.args.get("city", "").strip()
    events = []

    if city:
        api_city = normalize_city(city)

        ticketmaster_events = get_ticketmaster_events(api_city)
        serp_events = get_serpapi_events(api_city)
        predicthq_events = get_predicthq_events(api_city)

        print("Original city:", city)
        print("Normalized city:", api_city)
        print("Ticketmaster key loaded:", bool(TICKETMASTER_API_KEY))
        print("SerpApi key loaded:", bool(SERPAPI_API_KEY))
        print("PredictHQ key loaded:", bool(PREDICTHQ_API_KEY))
        print("Ticketmaster events:", len(ticketmaster_events))
        print("SerpApi events:", len(serp_events))
        print("PredictHQ events:", len(predicthq_events))

        all_events = balance_events(ticketmaster_events, serp_events, predicthq_events, max_total=12)
        print("Combined events before dedupe:", len(all_events))

        events = remove_duplicates(all_events)
        events = sort_events(events)

        print("Final events after dedupe/sort:", len(events))

    return render_template("index.html", city=city, events=events)


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)