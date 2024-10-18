from enum import Enum

from sqlalchemy import Column, Select, and_, func, or_, select, text, union_all
from sqlalchemy.orm import Query, Session

from .models import OsmElementMixin, Point, Polygon


class SRID(Enum):
    WSG84 = 4326


class BaseGeometry:
    def convert_column_to_geojson(
        query: Select,
        column: Column,
        label: str = "geojson",
        srid: SRID = SRID.WSG84,
    ) -> Select:
        query = query.add_columns(
            func.ST_AsGeoJson(
                func.ST_Transform(
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


class PolygonRepository:
    def list(
        self,
        db: Session,
        filter_by_name: str | None = None,
        boundary_in: list[str] | None = None,
        admin_level_in: list[str] | None = None,
    ) -> list[Polygon]:
        query = db.query(
            Polygon.osm_id,
            Polygon.name,
            Polygon.tags,
            Polygon.way,
        )

        if filter_by_name:
            query = query.filter(
                Polygon.tags["name:en"].op("%")(filter_by_name),
            ).order_by(
                Polygon.tags["name:en"].op("<->")(filter_by_name).asc(),
            )

        if boundary_in:
            query = query.filter(Polygon.boundary.in_(boundary_in))

        if admin_level_in:
            query = query.filter(Polygon.admin_level.in_(admin_level_in))

        query = query.limit(10)

        return query.all()


class GeometryRepository:
    def list_huts_d(self, db: Session):
        france_polygon = (
            db.query(Polygon.way)
            .filter(Polygon.tags["name:en"].op("%")("France"))
            .order_by(Polygon.name.op("<->")("France"))
        ).first()

        if france_polygon is None:
            return []

        points_query = db.query(
            Point.osm_id.label("osm_id"),
            Point.amenity,
            Point.name,
            Point.tags,
            Point.tourism,
            Point.way.label("point_way"),
            func.ST_AsGeoJson(func.ST_Transform(Point.way, 4326)).label("geojson"),
        ).filter(
            and_(
                or_(
                    Point.tourism.in_(["alpine_hut", "wilderness_hut"]),
                    and_(
                        Point.amenity == "shelter",
                        Point.tags["shelter_type"] == "basic_hut",
                    ),
                ),
                func.ST_Intersects(Point.way, france_polygon.way),
            )
        )

        polygons_query = db.query(
            Polygon.osm_id.label("osm_id"),
            Polygon.amenity,
            Polygon.name,
            Polygon.tags,
            Polygon.tourism,
            func.ST_AsGeoJson(func.ST_Transform(Polygon.way, 4326)).label("geojson"),
        ).filter(
            and_(
                or_(
                    Polygon.tourism.in_(["alpine_hut", "wilderness_hut"]),
                    and_(
                        Polygon.amenity == "shelter",
                        Polygon.tags["shelter_type"] == "basic_hut",
                    ),
                ),
                func.ST_Intersects(Polygon.way, france_polygon.way),
            )
        )

        query = (
            points_query.union_all(polygons_query).order_by(text("osm_id")).limit(100)
        )

        return query.all()

    def list_huts(
        self,
        db: Session,
        offset: int = 0,
        limit: int = 50,
        intersects_with: Polygon | Point = None,
    ) -> list[Polygon | Point]:
        point_query = select(
            Point.osm_id.label("osm_id"),
            Point.amenity,
            Point.name,
            Point.tags,
            Point.tourism,
        ).select_from(Point)

        point_query = BaseGeometry.convert_column_to_geojson(
            point_query,
            Point.way,
        )

        point_query = BaseGeometry.filter_huts(
            point_query,
            Point,
        )

        if intersects_with:
            point_query = point_query.filter(
                func.ST_Intersects(Point.way, intersects_with)
            )

        polygon_query = select(
            Polygon.osm_id.label("osm_id"),
            Polygon.amenity,
            Polygon.name,
            Polygon.tags,
            Polygon.tourism,
        ).select_from(Polygon)

        polygon_query = BaseGeometry.convert_column_to_geojson(
            polygon_query,
            Polygon.way,
        )

        polygon_query = BaseGeometry.filter_huts(
            polygon_query,
            Polygon,
        )

        if intersects_with:
            polygon_query = polygon_query.filter(
                func.ST_Intersects(Polygon.way, intersects_with)
            )

        combined_query = union_all(point_query, polygon_query)
        combined_query = combined_query.order_by("osm_id").offset(offset).limit(limit)

        return db.execute(combined_query).all()
