import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOOD_TRUCKS_PATH = PROJECT_ROOT / "public" / "data" / "food-trucks.json"
FOOD_IMAGES_PATH = PROJECT_ROOT / "public" / "images" / "food"
VALID_DAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}


def test_food_truck_feed_has_valid_references() -> None:
    feed = json.loads(FOOD_TRUCKS_PATH.read_text(encoding="utf-8"))
    trucks = {truck["id"] for truck in feed["foodTrucks"]}
    locations = {location["id"] for location in feed["locations"]}

    assert feed["schemaVersion"] == 1
    assert len(trucks) == len(feed["foodTrucks"])
    assert len(locations) == len(feed["locations"])
    assert all(stop["truckId"] in trucks for stop in feed["stops"])
    assert all(stop["locationId"] in locations for stop in feed["stops"])
    assert all(stop["days"] and set(stop["days"]) <= VALID_DAYS for stop in feed["stops"])
    assert all(
        (FOOD_IMAGES_PATH / truck["image"]).is_file()
        for truck in feed["foodTrucks"]
    )


def test_everyday_stands_are_present_on_all_seven_days() -> None:
    feed = json.loads(FOOD_TRUCKS_PATH.read_text(encoding="utf-8"))
    everyday_ids = {"stand-pizza-casino", "creperie", "bibim-pop"}
    stops = {
        stop["truckId"]: set(stop["days"])
        for stop in feed["stops"]
        if stop["truckId"] in everyday_ids
    }

    assert stops == {truck_id: VALID_DAYS for truck_id in everyday_ids}


def test_requested_food_truck_details_are_published() -> None:
    feed = json.loads(FOOD_TRUCKS_PATH.read_text(encoding="utf-8"))
    trucks = {truck["id"]: truck for truck in feed["foodTrucks"]}
    locations = {location["id"]: location for location in feed["locations"]}

    assert trucks["sopiadin"]["phone"] == "07 66 60 48 71"
    assert trucks["bibim-pop"] == {
        "id": "bibim-pop",
        "name": "BIBIM POP",
        "cuisine": "Distributeur de plats coréens",
        "website": "https://www.bibimpop.fr/",
        "phone": "06 15 32 62 52",
        "note": "Accessible 24 h/24 et 7 j/7",
        "image": "asian-bowl.jpg",
    }
    assert locations["metrhotel"]["name"] == "Devant Metrhôtel · face au Buffalo Grill"
    assert locations["la-taable"]["name"] == "Devant « La Taable »"
    creperie_stop = next(
        stop for stop in feed["stops"] if stop["truckId"] == "creperie"
    )
    assert creperie_stop["locationId"] == "la-taable"
