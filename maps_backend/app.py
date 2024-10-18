from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from sqlalchemy import text
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
    # min_x: float | None = None,
    # min_y: float | None = None,
    # max_x: float | None = None,
    # max_y: float | None = None,
    db: Session = Depends(get_db),
):
    # print([min_x, min_y, max_x, max_y])
    # (
    #     [min_x, min_y, max_x, max_y]
    #     if min_x is not None
    #     and min_y is not None
    #     and max_x is not None
    #     and max_y is not None
    #     else None
    # ),

    # geometries = db.execute(
    #     text(
    #         """
    # select osm_id, amenity, "name", tags, tourism, ST_AsGeoJSON(ST_Transform(way, 4326)) as geojson
    # from planet_osm_polygon
    # where (tourism in ('alpine_hut', 'wilderness_hut')
    # or amenity = 'shelter' and tags->'shelter_type' = 'basic_hut')
    # and (st_intersects(
    # (select way from planet_osm_polygon where boundary = 'administrative' and admin_level = '2' and (tags->'name:en') % 'France' order by (tags->'name:en') <-> 'France'),
    # way))
    # union all
    # select osm_id, amenity, "name", tags, tourism, ST_AsGeoJSON(ST_Transform(way, 4326)) as geojson
    # from planet_osm_point
    # where (tourism in ('alpine_hut', 'wilderness_hut')
    # or amenity = 'shelter' and tags->'shelter_type' = 'basic_hut')
    # and (st_intersects(
    # (select way from planet_osm_polygon where boundary = 'administrative' and admin_level = '2' and (tags->'name:en') % 'France' order by (tags->'name:en') <-> 'France'),
    # way
    # ))
    # order by osm_id
    # limit 100
    #                                  """
    #     )
    # )

    # geometries = repositories.GeometryRepository().list_huts(
    #     db,
    #     intersects_with=repositories.PolygonRepository()
    #     .list(
    #         db,
    #         filter_by_name="France",
    #         admin_level_in=["2"],
    #         boundary_in=["administrative"],
    #     )[0]
    #     .way,
    # )

    geometries = repositories.GeometryRepository().list_huts_d(db)

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
