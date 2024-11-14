from pydantic import BaseModel, Json


class Point(BaseModel):
    id: int
    name: str | None
    object_type: str
    tags: dict
    geojson: Json


class Polygon(BaseModel):
    id: int
    name: str | None
    object_type: str
    tags: dict
    centroid: Json
    geojson: Json
