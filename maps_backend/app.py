from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from maps_backend import repositories, schemas

from .database import get_db

app = FastAPI()


@app.get("/search", response_model=list[schemas.Polygon])
async def filter_by_name(
    q: str, db: Session = Depends(get_db)
) -> list[schemas.Polygon]:
    polygons = repositories.PolygonRepository().list(
        db,
        filter_by_name=q,
        boundary_in=["administrative"],
        admin_level_in=["2"],
    )

    return [
        {
            "osm_id": polygon.osm_id,
            "name": polygon.name,
            "tags": polygon.tags,
            "way": None,  # str(polygon.way),
        }
        for polygon in polygons
    ]


@app.get(
    "/polygons/",
    response_model=list[schemas.Geometry],
)
async def get_huts(
    min_x: float | None = None,
    min_y: float | None = None,
    max_x: float | None = None,
    max_y: float | None = None,
    db: Session = Depends(get_db),
):
    # http://bboxfinder.com/#45.234283,5.657959,45.525111,6.059647
    # print([min_x, min_y, max_x, max_y])
    bbox = (
        [min_x, min_y, max_x, max_y]
        if min_x is not None
        and min_y is not None
        and max_x is not None
        and max_y is not None
        else None
    )

    # ?min_x=5.657959&min_y=45.234283&max_x=6.059647&max_y=45.525111
    geometries = repositories.GeometryRepository().list_huts(
        db,
        bbox=bbox,
    )

    return [
        {
            "osm_id": geometry.osm_id,
            # "admin_level": geometry.admin_level,
            "amenity": geometry.amenity,
            # "boundary": geometry.boundary,
            "name": geometry.name,
            "tourism": geometry.tourism,
            "tags": geometry.tags,
            "geojson": geometry.geojson,
        }
        for geometry in geometries
    ]
