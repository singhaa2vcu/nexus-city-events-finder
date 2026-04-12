from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
PREDICTHQ_API_KEY = os.getenv("PREDICTHQ_API_KEY")


# ---------- API 1: Ticketmaster ----------
def get_ticketmaster_events(city):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    params = {
        "apikey": TICKETMASTER_API_KEY,
        "city": city,
        "size": 5
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        events = []

        if "_embedded" in data:
            for event in data["_embedded"]["events"]:
                name = event.get("name")
                date = event.get("dates", {}).get("start", {}).get("localDate")

                venue = "Unknown"
                if "_embedded" in event and "venues" in event["_embedded"]:
                    venue = event["_embedded"]["venues"][0].get("name")

                if name and date and venue:
                    events.append({
                        "title": name,
                        "date": date,
                        "venue": venue,
                        "source": "Ticketmaster"
                    })

        return events

    except Exception as e:
        print("Ticketmaster error:", e)
        return []


# ---------- API 2: SerpApi ----------
def get_serpapi_events(city):
    if not SERPAPI_API_KEY:
        return []

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_events",
        "q": f"Events in {city}",
        "api_key": SERPAPI_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        events = []

        for event in data.get("events_results", []):
            title = event.get("title")

            date_info = event.get("date")
            if isinstance(date_info, dict):
                date = date_info.get("start_date", "")
            else:
                date = str(date_info) if date_info else ""

            address = event.get("address")
            if isinstance(address, list) and address:
                venue = address[0]
            else:
                venue = "Unknown"

            if title and date and venue:
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


# ---------- API 3: PredictHQ ----------
def get_predicthq_events(city):
    if not PREDICTHQ_API_KEY:
        return []

    url = "https://api.predicthq.com/v1/events/"
    headers = {
        "Authorization": f"Bearer {PREDICTHQ_API_KEY}",
        "Accept": "application/json"
    }
    params = {
        "q": city,
        "limit": 5,
        "sort": "start"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        events = []

        for event in data.get("results", []):
            title = event.get("title")
            date = event.get("start", "")

            location = event.get("location")
            if isinstance(location, list):
                venue = str(location)
            else:
                venue = "Unknown"

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


# ---------- Clean data ----------
def remove_duplicates(events):
    seen = set()
    unique_events = []

    for event in events:
        key = (
            event["title"].lower().strip(),
            event["date"].lower().strip(),
            event["venue"].lower().strip()
        )

        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    return unique_events


def sort_events(events):
    return sorted(events, key=lambda x: x["date"] if x["date"] else "")


# ---------- Routes ----------
@app.route("/")
def home():
    city = request.args.get("city", "")
    events = []

    if city:
        tm_events = get_ticketmaster_events(city)
        serp_events = get_serpapi_events(city)
        phq_events = get_predicthq_events(city)

        print("Ticketmaster events:", len(tm_events))
        print("SerpApi events:", len(serp_events))
        print("PredictHQ events:", len(phq_events))

        events = tm_events + serp_events + phq_events
        events = remove_duplicates(events)
        events = sort_events(events)

    return render_template("index.html", city=city, events=events)


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True)