from slugify import slugify
from aiosqlite import Error
from pydantic import ValidationError
from sanic import Blueprint
from sanic.response import json, text

from application.database.db import execute_query, fetch_all, fetch_one
from application.schemas.schemas import SportCreate, SportUpdate

bp = Blueprint("sports", url_prefix="/sports")

@bp.route('/', methods=['GET'])
async def get_all_sports(request):
    try:
        sports = await fetch_all(request.app.ctx.db, "SELECT * FROM sport")
    except Error as e:
        return json({"message": f"An error occurred: {e}"}, 500)
    
    if not sports:
        return json({"message": "No sports found"}, 404)

    return json(sports)

@bp.route("/<sport_id:int>", methods=["GET"])
async def get_sport(request, sport_id: int) -> json:
    try:
        sport = await fetch_one(
            request.app.ctx.db, "SELECT * FROM sport WHERE id = ?", (sport_id,)
        )
    except Error as e:
        return json({"message": f"An error occurred: {e}"}, 500)
    
    if not sport:
        return json({"message": "Sport not found"}, 404)
    
    return json(sport)


@bp.route("/", methods=["POST"])
async def create_sport(request) -> json:
    try:
        sport = SportCreate(**request.json).model_dump()
        if not sport.get("slug"):
            sport["slug"] = slugify(sport["name"])

    except ValidationError as e:
        return json({"message": f"Invalid data: {e.errors()}"}, 400)

    try:
        await execute_query(
            request.app.ctx.db,
            "INSERT INTO sport (Name, Slug, Active) VALUES (?, ?, ?)",
            (sport["name"], sport["slug"], sport["active"]),
        )
    except Error as e:
        return json({"message": f"An error occurred: {e}"}, 500)

    return json({"message": "Sport created successfully"}, 201)


@bp.route("/<sport_id:int>", methods=["PATCH"])
async def update_sport(request, sport_id) -> json:
    sport_data = SportUpdate(**request.json).model_dump()
    query = "UPDATE sport SET "
    values = []
    for key, value in sport_data.items():
        if value is None:
            continue
        query += f"{key} = ?, "
        values.append(value)

    query = query.rstrip(", ") + " WHERE id = ?"
    values.append(sport_id)

    try:
        await execute_query(request.app.ctx.db, query, tuple(values))
    except Error as e:
        return json({"message": f"An error occurred: {e}"}, 500)
    return json({"message": "Sport updated successfully"})


@bp.route("/<sport_id:int>", methods=["DELETE"])
async def delete_sport(request, sport_id):
    try:
        await execute_query(
            request.app.ctx.db, "DELETE FROM sport WHERE id = ?", (sport_id,)
        )
    except Error as e:
        return json({"message": f"An error occurred: {e}"}, 500)
    return text('', 204)
