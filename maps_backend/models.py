from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import HSTORE

from .database import Base


class OsmElementMixin(object):
    osm_id = Column(Integer, primary_key=True)
    admin_level = Column(Integer, nullable=True)
    amenity = Column(String, nullable=True)
    boundary = Column(String, nullable=True)
    name = Column(String, nullable=True)
    tags = Column(HSTORE, nullable=True)
    tourism = Column(String, nullable=True)


class Polygon(OsmElementMixin, Base):
    __tablename__ = "planet_osm_polygon"
    way = Column(
        Geometry(
            "GEOMETRY",
            srid=3857,
        )
    )


class Point(OsmElementMixin, Base):
    __tablename__ = "planet_osm_point"
    way = Column(
        Geometry(
            "POINT",
            srid=3857,
        )
    )
