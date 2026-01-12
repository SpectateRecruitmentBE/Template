from locale import Error

from pydantic import ValidationError
from sanic import Blueprint, response
from slugify import slugify
import json
from urllib.request import urlopen, quote

from application.database.db import fetch_all, fetch_one, execute_query
from application.schemas.schemas import EventCreate, EventUpdate

bp = Blueprint('events', url_prefix='/events')

@bp.route('/', methods=['GET'])
async def get_all_events(request):
    events = []
    try:
        events = await fetch_all(request.app.ctx.db, "SELECT * FROM event")
    except Error as e:
        return response.json({"message": f"An error occurred: {e}"}, 500)

    if not events:
        return response.json({"message": "No event found"}, 404)

    return response.json(events)


@bp.route('/<event_id>', methods=['GET'])
async def get_event_by_id(request, event_id):
    event = None

    try:
        event = await fetch_one(
            request.app.ctx.db, "SELECT * FROM event WHERE id = ?", (event_id,)
        )
    except Error as e:
        return response.json({"message": f"An error occurred: {e}"}, 500)

    if not event:
        return response.json({'error': 'Event not found'}, status=404)

    return response.json(event)

@bp.route('/', methods=['POST'])
async def create_event(request):
    # event_data = request.json
    # Your code to validate and save the event to the database
    event_teams = "Arsenal v Leeds"
    team_logos = get_event_logos(event_teams)

    try:
        event = EventCreate(**request.json).model_dump()
        if not event.get("slug"):
            event["slug"] = slugify(event["name"])

    except ValidationError as e:
        return response.json({"message": f"Invalid data: {e.errors()}"}, 400)

    try:
        await execute_query(
            request.app.ctx.db,
            "INSERT INTO event (name, active, slug,type, status, start_time, actual_start_time, sport_id,logos) VALUES (?, ?, ?,?, ?, ?,?, ?, ?)",
            (event["name"], event["active"], event["slug"],event["type"], event["status"], event["start_time"],event["actual_start_time"], event["sport_id"], team_logos),
        )
    except Error as e:
        return response.json({"message": f"An error occurred: {e}"}, 500)

    return response.json({"message": "Event created successfully"}, 201)



@bp.route('/<event_id>', methods=['PATCH'])
async def update_event(request, event_id):
    # event_data = request.json
    # Your code to validate and update the event in the database
    try:
        event_data = EventUpdate.model_validate(request.json).model_dump()
    except ValidationError as e:
        return response.json(
            {"message": "Invalid request data", "errors": e.errors()},
            status=400
        )
    query = "UPDATE event SET "
    values = []
    for key, value in event_data.items():
        if value is None:
            continue
        query += f"{key} = ?, "
        values.append(value)

    query = query.rstrip(", ") + " WHERE id = ?"
    values.append(event_id)

    try:
        await execute_query(request.app.ctx.db, query, tuple(values))
    except Error as e:
        return response.json({"message": f"An error occurred: {e}"}, 500)
    return response.json({"message": "Event updated successfully"})


@bp.route('/<event_id>', methods=['DELETE'])
async def delete_event(request, event_id):
    # Your code to delete the event with the given ID from the database
    try:
        await execute_query(
            request.app.ctx.db, "DELETE FROM event WHERE id = ?", (event_id,)
        )
    except Error as e:
        return response.json({"message": f"An error occurred: {e}"}, 500)
    return response.empty(status=204)

def fetch_team_logo(team_name: str):
    """
    Fetches the 'strLogo' value for a given team using urllib.
    Returns:
        - A single string URL
        - If API returns a list, returns the first non-empty value
        - "" if logo not found
    """
    url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={quote(team_name)}"

    try:
        with urlopen(url) as resp:
            data = json.loads(resp.read().decode())
    except Error as e:
        return ""  # API error → treat as no logo

    teams = data.get("teams", [])
    if not teams:
        return ""

    # Some APIs may return strLogo as a single string or a list
    logo = teams[0].get("strLogo", "")

    if isinstance(logo, list):
        # return first valid list element
        return next((x for x in logo if x), "")
    else:
        return logo or ""

def get_event_logos(event_name: str):
    """
    Given event name like "Arsenal v Leeds":
      - Fetch logos for both teams
      - RETURN formats:
           "link1|link2"
           ""|link2
           link1|""
           None    (if both empty)
    """
    parts = event_name.split(" v ")
    if len(parts) != 2:
        raise ValueError("Event name must be in format 'TeamA v TeamB'")

    team1, team2 = parts

    logo1 = fetch_team_logo(team1)
    logo2 = fetch_team_logo(team2)

    # If both missing → return None
    if not logo1 and not logo2:
        return None

    return f"{logo1}|{logo2}"