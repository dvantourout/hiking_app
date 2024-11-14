from geoalchemy2 import functions
from sqlalchemy.orm import Session

from ..models import Polygon


class PolygonRepository:
    def list(self, db: Session, limit: int = 100) -> list[Polygon]:
        query = db.query(
            Polygon.id,
            Polygon.name,
            Polygon.tags,
            Polygon.object_type,
            # TODO: create during the importation process
            # osm2pgsql column geojson with create_only argument
            # Then run an update query
            functions.ST_AsGeoJSON(Polygon.centroid).label("centroid"),
            functions.ST_AsGeoJSON(Polygon.geom).label("geojson"),
        )

        query = query.order_by(Polygon.id.asc())
        query = query.limit(limit)

        return query.all()
