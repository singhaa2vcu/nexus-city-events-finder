from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

API_KEY = os.getenv("TICKETMASTER_API_KEY")


def get_events(city):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    params = {
        "apikey": API_KEY,
        "city": city,
        "size": 5   # 🔥 limit results (prevents messy UI)
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        events = []

        if "_embedded" in data:
            for event in data["_embedded"]["events"]:
                name = event.get("name")
                date = event.get("dates", {}).get("start", {}).get("localDate")

                venue = "Unknown"
                if "_embedded" in event and "venues" in event["_embedded"]:
                    venue = event["_embedded"]["venues"][0].get("name")

                # 🔥 filter bad/missing data
                if name and date and venue:
                    events.append({
                        "title": name,
                        "date": date,
                        "venue": venue
                    })

        return events

    except Exception as e:
        print("ERROR:", e)
        return []


# 🔥 remove duplicates
def remove_duplicates(events):
    seen = set()
    unique_events = []

    for event in events:
        key = (event["title"], event["date"], event["venue"])

        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    return unique_events


# 🔥 sort by date
def sort_events(events):
    return sorted(events, key=lambda x: x["date"] if x["date"] else "")


@app.route("/")
def home():
    city = request.args.get("city", "")
    events = []

    if city:
        events = get_events(city)
        events = remove_duplicates(events)
        events = sort_events(events)

    return render_template("index.html", city=city, events=events)


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(debug=True)