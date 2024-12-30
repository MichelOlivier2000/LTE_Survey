from datetime import datetime
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape
from sqlalchemy import ForeignKeyConstraint, func, Identity, Index, Integer, REAL, SmallInteger, String, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped
from sqlalchemy.orm import mapped_column, relationship
from shapely.geometry import Point


# Classe de base pour tous les modèles
class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Cell_orm(Base):
    __tablename__ = 'cell'

    network_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cell_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tac: Mapped[int] = mapped_column(nullable=True)
    geom: Mapped[None] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)

    # le default_factory = list est important pour initialiser 
    readings: Mapped[list['Reading_orm']] = relationship('Reading_orm', back_populates='cell', default_factory=list, overlaps='cell,readings')


class Network(Base):
    __tablename__ = "network"

    id : Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True, init=False)
    mcc: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mnc: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Reading_orm(Base):

    __tablename__ = "reading"
    __table_args__ = ( 
        ForeignKeyConstraint(['network_id', 'cell_id'], # relation SQL Many-to-One to Table 'cell'
                             ['cell.network_id','cell.cell_id']), 
        ForeignKeyConstraint(['network_id', 'survey_id'], # relation SQL Many-to-One to Table 'survey'
                             ['survey.network_id','survey.survey_id'], ondelete='CASCADE'),
        Index('ix_network_id_cell_id', 'network_id', 'cell_id'),
        Index('ix_network_id_survey_id', 'network_id', 'survey_id')
    ) 
    
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True, init=False)
    network_id : Mapped[int] = mapped_column(Integer, nullable=False) 
    cell_id: Mapped[int] = mapped_column(Integer, nullable=False) 
    survey_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pci: Mapped[int] = mapped_column(SmallInteger, nullable=True)
    band: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tac: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_idx: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fwd_azimuth: Mapped[float] = mapped_column(REAL, nullable=False)
    speed: Mapped[float] = mapped_column(REAL, nullable=False)
    reading_time: Mapped[None] = mapped_column(TIMESTAMP, nullable=False) # Without timezone by default
    geom: Mapped[None] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    
    cell: Mapped['Cell_orm'] = relationship('Cell_orm', back_populates='readings', default=None, overlaps='readings,cell') # relation Python class Cell_orm
    survey: Mapped['Survey'] = relationship('Survey', back_populates='readings', default=None, overlaps='readings,survey') # relation Python class Survey
    
    def __repr__(self) -> str:
        return \
            f"Reading(id={self.id!r}, network_id={self.network_id!r}, survey_id={self.survey_id}," + \
            f"cell_id={self.reading_time.strftime('%d-%m-%Y %H:%M')}, file_idx={self.file_idx})"


class Sector(Base):
    __tablename__ = 'sector'
    __table_args__ = (
        ForeignKeyConstraint(['network_id', 'station_name'], # relation SQL Many-to-One to Table 'cell'
                             ['station.network_id','station.name']), 
    )
    network_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cell_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_name: Mapped[str] = mapped_column(String(20), index=True)
    geom: Mapped[None] = mapped_column(Geometry(geometry_type="MultiPolygon", srid=4326), nullable=True)


class Station(Base):
    __tablename__ = 'station'

    network_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20), primary_key=True)
    technos: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    power_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    date_fiche: Mapped[None] = mapped_column(TIMESTAMP, nullable=False)
    uploaded: Mapped[None] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    geom: Mapped[None] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)


class Survey(Base):
    __tablename__ = 'survey'

    network_id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(primary_key=True)

    survey_date: Mapped[None] = mapped_column(TIMESTAMP, nullable=False)
    uploaded: Mapped[None] = mapped_column(TIMESTAMP, init=False, server_default=func.now())
    comment: Mapped[str] = mapped_column(String(255))
    device: Mapped[str] = mapped_column(String(30))
    os_version: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(30))

    # le default_factory = list est important pour initialiser 
    readings: Mapped[list["Reading_orm"]] = relationship("Reading_orm", back_populates="survey", default_factory=list, overlaps='survey,readings')


    # La ligne suivante devrait passer pourtant elle plante dans QGIS... bizare.
    """ def __repr__(self) -> str:
        return f"Survey(id={self.survey_id!r}, network_id={self.network_id}, survey_date={self.survey_date.strftime("%d-%m-%Y %H:%M")}, comment={self.comment})" """
        
