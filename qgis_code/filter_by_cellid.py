from qgis.core import QgsExpression, QgsFeatureRequest
from qgis.gui import QgsMapToolIdentifyFeature

from sqlalchemy import select
from corelte.orm.db import get_db_session
from corelte.orm.models import Sector



# Define the layer you're working with
layer = iface.activeLayer()



NB_SECTORS_DEFAULT = 3

sectors_exceptions = {
    17063938 : 2,
    18756609 : 2,
    18941698 : 4,
    18354947 : 2
}


# Define a custom map tool to detect clicks on features
class FilterTool(QgsMapToolIdentifyFeature):
    
    def __init__(self, layer):
        self.layer = layer
        self.filter_cycle = 0
        self.cell_id = 0
        self.network_id = 0
        #self.nb_sectors = NB_SECTORS_DEFAULT
        self.sector_split = NB_SECTORS_DEFAULT
        super().__init__(iface.mapCanvas())
    

    def identify_nbSectors(self, cell_id : int):
        """L'identification des secteurs s'observe sur le terrain et un des cell_id est ajouté aux exceptions"""
        result = NB_SECTORS_DEFAULT
        for key, value in sectors_exceptions.items():
            if abs(cell_id - key) < 100: 
                result = value
        return result

    def identify_nbSectors_in_table_sector(self, net_id: int, cell_id: int):
        """La gestion du nombre de secteur se fait à l'aide du champ Sector.sector_split """
        stmt = select(Sector) \
            .where(Sector.network_id == net_id) \
            .where(cell_id - 100 <= Sector.cell_id <= cell_id + 100)
        
        with get_db_session as session:
            sector: Sector = session.execute(stmt).scalars.one()
            if sector: 
                return sector.sector_split
            return NB_SECTORS_DEFAULT


    def canvasReleaseEvent(self, event):
        # Identify the feature clicked on
        identified_features = self.identify(event.x(), event.y(), [self.layer], QgsMapToolIdentifyFeature.TopDownStopAtFirst)

        if identified_features:
            
            # Get the feature and the specific attribute for filtering
            feature = identified_features[0].mFeature
            self.cell_id = int(feature['cell_id'])  # replace with your attribute field name
            self.network_id = int(feature['network_id'])
            #self.nb_sectors = self.identify_nbSectors(self.cell_id)
            
            self.sector_split = self.identify_nbSectors(self.cell_id)

            """ if feature['sector_split'] != None :
                sector_split = int(feature['sector_split'])
                if not (2 <= sector_split <= 4):
                    sector_split = 3 """

            print(f'cell_id={self.cell_id} sector_split={self.sector_split} ok')
         
            # Cycle filters on or off based on the attribute value   
            if self.filter_cycle == 0:
                self.filter_cycle += 1
                # Apply filter on station
                #expression = f'"cell_id" = \'{attribute_value}\''
                expression = f'"network_id" = 1 AND abs("cell_id" - {self.cell_id}) < 100'
                self.layer.setSubsetString(expression)
            elif self.filter_cycle == 1:
                # Apply filter on sections
                self.filter_cycle += 1
                #mod_value = self.cell_id % self.nb_sectors
                mod_value = self.cell_id % self.sector_split
                expression = f'"network_id" = 1 AND abs("cell_id" - {self.cell_id}) < 100 AND MOD("cell_id",{self.sector_split}) = {mod_value}'
                self.layer.setSubsetString(expression)
            elif self.filter_cycle == 2:
                # Remove filter
                self.filter_cycle = 0
                self.layer.setSubsetString("")

# Set the custom tool as the active tool
filter_tool = FilterTool(layer)
iface.mapCanvas().setMapTool(filter_tool)
