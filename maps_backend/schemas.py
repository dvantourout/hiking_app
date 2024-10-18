from pydantic import BaseModel, Json


class Polygon(BaseModel):
    osm_id: int
    name: str | None
    tags: dict | None
    way: str | None


class Geometry(BaseModel):
    osm_id: int
    # admin_level: str | None
    amenity: str | None
    # boundary: str | None
    name: str | None
    tags: dict | None
    tourism: str | None
    geojson: Json | None
