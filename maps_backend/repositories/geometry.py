from geoalchemy2 import functions
from sqlalchemy import select, union_all
from sqlalchemy.orm import Session

from ..models import Point, Polygon
from .utils import BaseGeometryOperations


class GeometryRepository:
    def list_huts(
        self,
        db: Session,
        offset: int = 0,
        limit: int = 100,
        intersects_with_polygons_id: list[int] = None,
        bbox: list[int] = None,
    ) -> list[Polygon | Point]:

        point_query = select(
            Point.osm_id.label("osm_id"),
            Point.amenity,
            Point.name,
            Point.tags,
            Point.tourism,
        ).select_from(Point)

        point_query = BaseGeometryOperations.convert_column_to_geojson(
            point_query,
            Point.way,
        )

        point_query = BaseGeometryOperations.filter_huts(
            point_query,
            Point,
        )

        polygon_query = select(
            Polygon.osm_id.label("osm_id"),
            Polygon.amenity,
            Polygon.name,
            Polygon.tags,
            Polygon.tourism,
        ).select_from(Polygon)

        polygon_query = BaseGeometryOperations.convert_column_to_geojson(
            polygon_query,
            Polygon.way,
        )

        polygon_query = BaseGeometryOperations.filter_huts(
            polygon_query,
            Polygon,
        )

        if intersects_with_polygons_id:
            intersects_with_polygons_cte = (
                db.query(Polygon.way)
                .filter(Polygon.osm_id.in_(intersects_with_polygons_id))
                .cte()
            )

            point_query = point_query.filter(
                functions.ST_Intersects(Point.way, intersects_with_polygons_cte.c.way)
            )

            polygon_query = polygon_query.filter(
                functions.ST_Intersects(Polygon.way, intersects_with_polygons_cte.c.way)
            )

        if bbox:
            # TODO: only use st_transform when needed and allows to used any srid
            point_query = point_query.filter(
                functions.ST_Intersects(
                    Point.way,
                    functions.ST_Transform(
                        functions.ST_MakeEnvelope(*bbox, 4326), 3857
                    ),
                )
            )

            polygon_query = polygon_query.filter(
                functions.ST_Intersects(
                    Polygon.way,
                    functions.ST_Transform(
                        functions.ST_MakeEnvelope(*bbox, 4326), 3857
                    ),
                )
            )

        combined_query = union_all(point_query, polygon_query)
        combined_query = combined_query.order_by("osm_id").offset(offset).limit(limit)

        return db.execute(combined_query).all()
