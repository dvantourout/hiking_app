from enum import Enum

from geoalchemy2 import functions
from sqlalchemy import Column, Select, and_, or_

from ..models import Point, Polygon


class SRID(Enum):
    WSG84 = 4326


class BaseGeometryOperations:
    def convert_column_to_geojson(
        query: Select,
        column: Column,
        label: str = "geojson",
        srid: SRID = SRID.WSG84,
    ) -> Select:
        query = query.add_columns(
            functions.ST_AsGeoJSON(
                functions.ST_Transform(
                    column,
                    srid.value,
                ),
            ).label(label),
        )

        return query

    def filter_huts(query: Select, column: Point | Polygon) -> Select:
        query = query.filter(
            or_(
                column.tourism.in_(
                    [
                        "alpine_hut",
                        "wilderness_hut",
                    ]
                ),
                and_(
                    column.amenity == "shelter",
                    column.tags["shelter_type"].in_(
                        [
                            "basic_hut",
                            "lean_to",
                        ]
                    ),
                ),
            )
        )

        return query
