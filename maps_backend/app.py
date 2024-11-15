from dotenv import load_dotenv

load_dotenv()

from typing import Annotated

from fastapi import Depends, FastAPI, Query
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from maps_backend import schemas

from .database import get_db
from .repositories import PointRepository, PolygonRepository

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.get("/")
def root():
    return {"hello": "world!"}


@app.get("/points", response_model=list[schemas.Point])
def get_points(
    bbox: Annotated[list[float] | None, Query()] = None,
    limit: int | None = 1000,
    db: Session = Depends(get_db),
):
    print(bbox)

    points_repository = PointRepository()
    points = points_repository.list(
        db,
        limit=limit,
        bbox=bbox,
    )

    return [
        {
            "id": point.id,
            "name": point.name,
            "object_type": point.object_type,
            "tags": point.tags,
            "geojson": point.geojson,
        }
        for point in points
    ]


@app.get("/polygons", response_model=list[schemas.Polygon])
def get_polygons(db: Session = Depends(get_db)):
    polygons_repository = PolygonRepository()
    polygons = polygons_repository.list(db)

    return [
        {
            "id": polygon.id,
            "name": polygon.name,
            "object_type": polygon.object_type,
            "tags": polygon.tags,
            "centroid": polygon.centroid,
            "geojson": polygon.geojson,
        }
        for polygon in polygons
    ]
