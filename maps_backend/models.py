from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import HSTORE

from .database import Base
from .utils import SRID


# https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html
class OsmElementMixin(object):
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    osm_type = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    tags = Column(HSTORE, nullable=False)


class Polygon(OsmElementMixin, Base):
    __tablename__ = "polygons"
    centroid = Column(
        Geometry(
            "POINT",
            srid=SRID.EPSG_4326,
        )
    )
    geom = Column(
        Geometry(
            "GEOMETRY",
            srid=SRID.EPSG_4326,
        )
    )


class Point(OsmElementMixin, Base):
    __tablename__ = "nodes"
    geom = Column(
        Geometry(
            "POINT",
            srid=SRID.EPSG_4326,
        )
    )
