from convert_wgs84_to_ch1903 import GPSConverter
import csv
from datetime import datetime
from geoalchemy2 import Geometry
import json
import psycopg2
import re
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Session, Mapped, mapped_column
from sqlalchemy import Integer, TIMESTAMP, VARCHAR, func
from sqlalchemy import delete, create_engine, inspect, MetaData, Table
from shapely.geometry import Point
from geoalchemy2.shape import from_shape


import sys

class Base(MappedAsDataclass, DeclarativeBase):
    pass


class Station(Base):

    __tablename__ = "station"
    __table_args__ = {'schema': 'lte'}

    #id: Mapped[int] = mapped_column(primary_key=True, init=False)
    network_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(20), primary_key=True)
    technos: Mapped[int] = mapped_column(Integer)
    power_id: Mapped[int] = mapped_column(Integer)

    date_fiche: Mapped[None] = mapped_column(TIMESTAMP, nullable=True, server_default=None)
    uploaded: Mapped[None] = mapped_column(TIMESTAMP, init=False, server_default=func.now())
    geom: Mapped[None] = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)


Network_dict = {
    'Swisscom' : 1,
    'Sunrise' : 2,
    'Salt' : 3,
    'SBB' : 8
}

Power_dict = {
    'très' : 1, # correspond à 'très faible'
    'faible' : 2,
    'moyenne' : 3,
    'forte' : 4
}

TECHNO_2G = 1 << 0
TECHNO_3G = 1 << 1
TECHNO_4G = 1 << 2
TECHNO_5G = 1 << 3

Techno_dict = {
    '2G' : TECHNO_2G,
    '3G' : TECHNO_3G,
    '4G' : TECHNO_4G,
    '5G' : TECHNO_5G
}

class convert_bakom_file_to_csv():

    def __init__(self, filename):
        self.fname_in = filename
        self.fname_out = 'bakom-output-4g.csv'
        self.lines : list[Station] = []

    def convert(self):

        # Opening JSON file
        with open(self.fname_in) as f:

            # returns JSON object as a dictionary
            data = json.load(f)

            converter = GPSConverter()

            power_id = 0
            gen_id = 4 # LTE
            for feature in data['features']:

                # copie le nom de l'opérateur et de la station    
                stations = feature['properties']['station'].split()
                try:
                    network_id = Network_dict[stations[0]]
                except:
                    network_id = 0
                try:
                    station = stations[1]
                except:
                    station = 'unknown'        
                
                # copie et combine les technologies
                techno_strs = re.split(r'[ ,]', feature['properties']['techno_fr'])
                technos = 0
                try:
                    for i in 1, len(techno_strs) - 1:
                        technos |= Techno_dict[techno_strs[i]]
                except:
                    technos = 0

                # copie la catégorie de puissance émise
                power_frs = feature['properties']['power_fr'].split()
                try:
                    power_str = power_frs[4]
                    power_id = Power_dict[power_str]
                except :
                    power_id = 0

                # copie la date de la fiche technique
                bws = re.split(r'[ -]', feature['properties']['bewilligung_fr'])
                try:
                    date_fiche = datetime(year=int(bws[3]), month=int(bws[4]), day=int(bws[5]))
                except:
                    date_fiche = None

                # copie et converti les coordonée en CRS:WGS84    
                coord = feature['geometry']['coordinates']
                #chLat, chLon = map(int, coord.split(','))
                chLat = coord[0]
                chLon = coord[1]

                #Converti données en format CRS:WGS84
                Latitude, Longitude = converter.LV03toWGS84_2(x=chLat-2000000, y=chLon-1000000)

                # Create a Shapely Point
                point = Point(Longitude, Latitude)
    
                # Convert Shapely Point to GeoAlchemy format
                geom=from_shape(point, srid=4326)


                s = Station(network_id=network_id, 
                            name=station, 
                            technos=technos, 
                            power_id=power_id, 
                            date_fiche=date_fiche,
                            geom=geom
                            )
                #self.lines.append([network_id, station, technos, power_id, date_fiche, chLat, chLon, Latitude, Longitude])
                self.lines.append(s)

                # print("id=",id," wgs84=", wgs84, "powercode=", pc_fr)



    def save_file(self):
        
        # Opening JSON file
        fields = ['network_id','station','technos','power_id','date_fiche', 'lat_lv95','lon_lv95','latitude','longitude']

        with open(self.fname_out, 'w') as csvfile:
            # creating a csv writer object
            csvwriter = csv.writer(csvfile)

            # writing the fields
            csvwriter.writerow(fields)

            # writing the data rows
            csvwriter.writerows(self.lines)


    def delete_table(self, engine):

        metadata = Base.metadata
        tablename = Station.__tablename__
        lte_schema = 'lte'
        station_table = Table(tablename, metadata, autoload_with=engine, schema=lte_schema)

        if inspect(engine).has_table( table_name=tablename, schema=lte_schema):
            station_table.drop(engine)

        """ stmt = delete(Station) 
        print(f"stmt={stmt}")        
        with Session(engine) as session:
            session.execute(stmt)
            session.commit() """

    def save_lines_to_database(self, engine):

        with Session(engine) as session:   
            try:

                #objects_to_insert = [Station(field1=value1, field2=value2) for value1, value2 in large_dataset]
                session.bulk_save_objects([station for station in self.lines if station.network_id > 0 ])                
                session.commit()
            
            except(Exception, psycopg2.DatabaseError) as error:
                print(error)



def main():

    #bakom_file = "~/SURVEYS/DB_STORE/standorte-mobilfunkanlagen_2056.json"
    bakom_file = "/Users/mext/SURVEYS/DB_STORE/standorte-mobilfunkanlagen_2056.json"
    
    c = convert_bakom_file_to_csv(bakom_file)

    engine = create_engine("postgresql://gis:password@127.0.0.1:5432/gis", echo=True)
    with engine.begin() as conn: 
        c.convert()
        #c.save_file()
        
        c.delete_table(engine)    
        Base.metadata.create_all(conn)
        conn.commit()

        c.save_lines_to_database(engine)
        conn.commit()
        conn.close()
    

if __name__ == "__main__":
    main()