from geopy.distance import distance # type: ignore
from geoalchemy2.shape import from_shape
import os, os.path
import psycopg2 
from shapely.geometry import Point
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import SQLAlchemyError
from corelte.cursor import Cursor
from corelte.orm.db import get_db_session
from corelte.reading import Reading
from corelte.orm.models import Cell_orm, Network, Reading_orm, Sector, Survey



class Fusion:

    def __init__(self, argument):

        self.argument = argument

        # Initialise la liste de points de mesure fusionnée
        self.linesFusion : list[Reading] = []


    def fusion_data(self, cursorGps: Cursor, linesGps: list[Reading], cursorMp4: Cursor, linesMp4: list[Reading]):
        
        # Index de la première mesure GPS à fusionner
        first_index_gps = 0
        
        # Index de la première mesure MP4 à fusionner
        first_index_mp4 = cursorMp4.first_non_null_idx

        # Traite le cas rare ou le gps démarre après le screencast. 
        if cursorGps.first_non_null_reading_time > cursorMp4.first_non_null_reading_time:
            while (first_index_mp4 < len(linesMp4)) and (linesMp4[first_index_mp4].reading_time < cursorGps.first_non_null_reading_time):
                first_index_mp4 += 1

        # Le Gps démarre avant le screencast dans le mode d'utilisation habituel.
        # BUG cursorMp4.first_non_null_reading_time contient la date d'aujourd'hui ce qui est faux
        while (first_index_gps < len(linesGps)-1) & (linesGps[first_index_gps].reading_time < cursorMp4.first_non_null_reading_time):
            first_index_gps += 1

        # Fusionne les données
        idx_gps = first_index_gps
        for idx_mp4 in range(first_index_mp4, len(linesMp4)):

            if idx_gps >= len(linesGps):
                break # cas où l'enregistrement du GPS se serait arrêté avant le screencast. ()
            
            r = Reading(self.argument.survey_id)
            
            r.band = linesMp4[idx_mp4].band
            r.carrier = linesMp4[idx_mp4].carrier
            r.cellid = linesMp4[idx_mp4].cellid 
            r.reading_time = linesMp4[idx_mp4].reading_time
            r.file_idx = linesMp4[idx_mp4].file_idx
            r.tac = linesMp4[idx_mp4].tac
            r.pci = linesMp4[idx_mp4].pci

            r.bwd_azimuth = linesGps[idx_gps].bwd_azimuth
            r.calculated = linesGps[idx_gps].calculated
            r.fwd_azimuth = linesGps[idx_gps].fwd_azimuth
            r.fwd_distance = linesGps[idx_gps].fwd_distance
            r.latitude = linesGps[idx_gps].latitude
            r.longitude = linesGps[idx_gps].longitude
            r.speed = linesGps[idx_gps].speed 

            self.linesFusion.append(r)
            idx_gps +=1

        print(f"Nb de lignes fusionnées={len(self.linesFusion)}")


    def clarify_with_minimum_distance2(self):
        """
        Supprime les points qui se trouvent trop près les uns des autres. 
        En fonction de la distance et des virages ou demi-tours éventuels
        """
        
        def is_far_enough(r1: Reading, r2: Reading) -> bool:
            """
            Retourne vrai si les deux points sont suffisament distant en fonction de la vitesse et de l'angle de déplacement.
            """

            # Vérifie la validité de la valeur speed: elle est none dans de rare cas (as in Survey 0295)    
            if not (r1.speed):
                return False

            dist = distance((r1.latitude, r1.longitude), (r2.latitude, r2.longitude)).m

            # formule empirique pour disperser les points à grande vitesse
            dist_min = 50 + r1.speed * 10

            # calcul de l'angle quand la trajectoire tourne
            beta = abs(r1.fwd_azimuth - r2.fwd_azimuth)
            alpha = min(beta, 360 - beta)

            # en vitesse de marche (<3 m/s), on filtre les points gps qui font des zig-zags.
            result = dist > dist_min or (alpha > 45 and r1.speed > 3)
            return result

        # 0. Si la liste est déjà vide on sort de suite.
        if len(self.linesFusion) < 2:
            return

        # 1. On ne garde que les mesures valides
        rows = [r for r in self.linesFusion if r.is_valid()]

        # 2. On ne garde que les points qui marquent un changement de cellid
        keep = [0] # premier row
        for i, reading in enumerate(rows[1:]):
            if reading.cellid != rows[keep[-1]].cellid:
                keep.append(i)
        keep.append(len(rows) -1) # dernier row

        # 3. Entre deux point 'keep', on ajoute un point tous les 50m ou plus selon la vitesse de déplacement.
        newrows = []
        for i, k in enumerate(keep):
            rk = rows[k]
            newrows.append(rk)
            next_k = keep[i + 1] if i < len(keep) - 1 else k  

            # on selectionne les points entre deux keep
            for t in range(k + 1, next_k): 
                rt = rows[t]
                if is_far_enough(rk, rt):
                    newrows.append(rt)
                    rk = rt

        # 4. On assigne la nouvelle liste fusion
        self.linesFusion = newrows


    def apply_exclusions(self):
        if len(self.argument.exclusions) == 0:
            return
        print(f"Nb de lignes avant l'exclusion={len(self.linesFusion)}")
        oldlines = self.linesFusion.copy()
        newlines = oldlines
        for intervalle in self.argument.exclusions:
            lo, hi = intervalle
            newlines = [r for r in oldlines if (r.file_idx < lo) or (r.file_idx > hi)]    
            oldlines = newlines.copy()
        self.linesFusion = newlines.copy()
        print(f"Nb de lignes après les exclusions={len(self.linesFusion)}")

    def apply_speed_compensation_to_linesFusion(self):
        for key, r in enumerate(self.linesFusion):
            r.apply_time_compensation()

    def save_linesFusion_to_database(self, survey_date):

        with get_db_session() as session:

            try:

                net_id = self.argument.network_id
                survey_id = self.argument.survey_id

                # Efface la version précédente de ce survey et tous les éléments de Reading en cascade
                stmt = delete(Survey) \
                    .where(Survey.network_id == net_id) \
                    .where(Survey.survey_id == survey_id)
                print(stmt)
                
                session.execute(stmt) 
                #    session.commit()

                # Ajoute le Survey
                survey = Survey(survey_id=survey_id, 
                                network_id=net_id, 
                                survey_date=survey_date, 
                                comment=self.argument.survey_comment, 
                                device=self.argument.device, 
                                model=self.argument.model,
                                os_version=self.argument.os_version
                                )
                session.add(survey) 
                
                for r in self.linesFusion:

                    # Check if the cell exists, if not, add it
                    stmt = select(Cell_orm).where(Cell_orm.network_id == net_id).where(Cell_orm.cell_id == r.cellid)
                    cell = session.execute(stmt).scalars().first()
                    if cell is None:
                        cell = Cell_orm(network_id=net_id, cell_id=r.cellid, tac=r.tac, geom=None)
                        session.add(cell)
                        session.flush()  # Sans le flush, le prochain passage esseyerait de l'ajouter à nouveau
                            
                    geom = from_shape(Point(r.longitude, r.latitude), srid=4326) 

                    reading = Reading_orm(
                        network_id=net_id, cell_id=r.cellid, survey_id=r.survey_id, 
                        pci=r.pci, band=r.band, tac=r.tac, file_idx=r.file_idx, 
                        fwd_azimuth=r.fwd_azimuth, speed=r.speed, reading_time=r.reading_time,
                        survey=survey,
                        cell=cell,
                        geom=geom
                    )
                    session.add(reading)
                
                session.commit()
            
            except SQLAlchemyError as e:
                print(e)




