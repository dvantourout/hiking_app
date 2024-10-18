from sqlalchemy.orm import Session

from ..models import Polygon


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
