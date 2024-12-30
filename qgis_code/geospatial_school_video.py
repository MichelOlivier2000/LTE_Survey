fn_sectors = '/Users/mext/SURVEYS/DB_STORE/DB_STORE.shp'
lyr_sectors = QgsVectorLayer(fn_sectors, '', 'ogr')
#lyr_sectors = iface.addVectorLayer(fn_sectors, '', 'ogr')

newfeat = QgsFeature(lyr_sectors.fields())
newfeat.setAttributes(['2345', 'Mon secteur', "C'est le secteur préféré des bisons de Colovrex." ])
geom = QgsGeometry.fromPolyline([QgsPoint(686427.9, 5794587.4), QgsPoint(686053.6, 5795400.4)])
newfeat.setGeometry(geom)
lyr_sectors.dataProvider().addFeatures([newfeat])

iface.addVectorLayer(fn_sectors, '', 'ogr')

# https://www.youtube.com/watch?v=X-LvGvNor4E

