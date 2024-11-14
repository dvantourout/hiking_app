from geoalchemy2 import functions
from sqlalchemy.orm import Session

from ..models import Point
from ..utils import SRID
from .utils import BaseGeometryRepository


class PointRepository(BaseGeometryRepository):
    def list(
        cls,
        db: Session,
        bbox: list[int] | None = None,
        limit: int = 100,
    ) -> list[Point]:
        query = db.query(
            Point.id,
            Point.name,
            Point.object_type,
            Point.tags,
            # TODO: create during the importation process
            # osm2pgsql column geojson with create_only argument
            # Then run an update query
            functions.ST_AsGeoJSON(Point.geom).label("geojson"),
        )

        # http://bboxfinder.com/#0.000000,0.000000,0.000000,0.000000
        if bbox:
            query = query.filter(
                functions.ST_Intersects(
                    Point.geom,
                    functions.ST_MakeEnvelope(
                        *bbox,
                        SRID.EPSG_4326,
                    ),
                ),
            )

        query = query.order_by(Point.id.asc())
        query = query.limit(limit)

        return query.all()
