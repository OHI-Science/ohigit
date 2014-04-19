# This generates the following shapefiles in the output directory:
#   rgn_[offshore|inland]{distance}{units}_[gcs|mol]
# where:
#   rgn = regions
#   offshore = zone extending from shore to the EEZ. rgn_type: eez, eez-disputed, eez-inland, fao, ccamlr.
#   inland = zone extending from shore inland. rgn_type: land, land-disputed.
#   distance = integer of distance {optional}
#   units = one of: nm (nautical miles), km (kilometers), mi (miles) {optional}
#   gcs = geographic coordinate system
#   mol = Mollweide projection, used to generate Thiessen polygons within a viable global projection
#
# If distance and units are not specified, then the regions are for the full extent,
# ie the entirety of that state's inland area or offshore area extending out to the EEZ.
#
# All shapefiles contain the region id (rgn_id) and name (rgn_name).
# The region id is automatically generated by ascending latitude coordinate in Mollweide projection.
# The rgn_*_gcs shapefiles also have a geodesic area calculated (area_km2).
# 
# Run on cmd:
#  amphitrite: C:\Python27\ArcGIS10.2\python.exe G:\ohiprep\Global\NCEAS-Regions_v2014\digest_buffers.py
#  optimus:    C:\Python27\ArcGISx6410.1\python.exe D:\best\docs\GitHub\ohiprep\Global\NCEAS-Regions_v2014\digest_buffers.py

# C:\Users\best\Downloads\get-pip.py

# modules
import arcpy, os, sys, re, socket, pandas, time
from numpy.lib import recfunctions
arcpy.SetLogHistory(True) # C:\Users\bbest\AppData\Roaming\ESRI\Desktop10.2\ArcToolbox\History

# configuration based on machine name
conf = {
    'amphitrite':
    {'dir_git'    :'G:/ohiprep',
     'dir_neptune':'N:',
     'dir_tmp'    :'C:/tmp',
     },
    'optimus':
    {'dir_git'    :'D:/best/docs/GitHub/ohiprep',
     'dir_neptune':'N:',
     'dir_tmp'    :'D:/best/tmp',
     }}[socket.gethostname().lower()]

# paths
nm      = 'NCEAS-Regions_v2014'                                      # name of data product
td      = '{0}/{1}'.format(conf['dir_tmp'], nm)                      # temp directory on local filesystem
gdb     = '{0}/geodb.gdb'.format(td)                                 # file geodatabase
ad      = '{0}/git-annex/Global/{1}'.format(conf['dir_neptune'], nm) # git annex directory on neptune
gd      = '{0}/Global/{1}'.format(conf['dir_git'], nm)               # git directory on local filesystem

# inputs
sp_gcs = '{0}/sp_gcs'.format(gdb)
buffers = ['inland1km','offshore3nm','offshore100nm','offshore1km','inland25km']

# buffer units dictionary
buf_units_d = {'nm':'NauticalMiles',
               'km':'Kilometers',
               'mi':'Miles'}

# fields
sp_flds = ['sp_type' ,'sp_id' ,'sp_name' ,'sp_key',
           'rgn_type','rgn_id','rgn_name','rgn_key',
           'cntry_id12','rgn_id12','rgn_name12']
rgn_flds = ['rgn_type','rgn_id','rgn_name','rgn_key']
sp_area_flds  = [ 'sp_type', 'sp_id', 'sp_name', 'sp_key','area_km2']
rgn_area_flds = ['rgn_type','rgn_id','rgn_name','rgn_key','area_km2']

# feature classes to use depending on direction of buffer (diced sp_*_d50k_gcs generated below)
dict_zone = {'inland'  :{'sp_types' :"'land','land-ccamlr'",
                         'buffer'   :'sp_offshore_dens1km_dice100k_gcs',
                         'intersect':'sp_inland_gcs'},
             'offshore':{'sp_types' :"'eez','fao','eez-ccamlr'",
                         'buffer'   :'sp_inland_dens1km_dice100k_gcs',
                         'intersect':'sp_offshore_gcs'}}

# projections
sr_mol = arcpy.SpatialReference('Mollweide (world)') # projected Mollweide (54009)
sr_gcs = arcpy.SpatialReference('WGS 1984')          # geographic coordinate system WGS84 (4326)

# environment
if not os.path.exists(td): os.makedirs(td)
if not arcpy.Exists(gdb): arcpy.CreateFileGDB_management(os.path.dirname(gdb), os.path.basename(gdb))
arcpy.env.workspace       = gdb
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = sr_gcs

# functions
def add_area(fc, fld_area='area_km2'):
    if fld_area in [fld.name for fld in arcpy.ListFields(fc)]:
        arcpy.DeleteField_management(fc, fld_area)
    arcpy.AddField_management(       fc, fld_area, 'DOUBLE')
    arcpy.CalculateField_management( fc, fld_area, '!shape.area@SQUAREKILOMETERS!', 'PYTHON_9.3')

def export_shpcsv(fc, flds, shp, csv):
    arcpy.CopyFeatures_management(fc, shp)
    d = pandas.DataFrame(arcpy.da.TableToNumPyArray(fc, flds))
    d.to_csv(csv, index=False)

# DEBUG: quick fixes
##print('DEBUG fix sp_gcs, rgn_gcs (%s)' % time.strftime('%H:%M:%S'))
##arcpy.Dissolve_management('sp_AQrsliver', 'sp_gcs' , sp_flds)
##print('  dissolving to rgn_gcs (%s)' % time.strftime('%H:%M:%S'))
##arcpy.Dissolve_management('sp_AQrsliver', 'rgn_gcs', rgn_flds)
##print('  repairing (%s)' % time.strftime('%H:%M:%S'))
##arcpy.RepairGeometry_management('sp_gcs')
##arcpy.RepairGeometry_management('rgn_gcs')
##arcpy.CheckGeometry_management (['sp_gcs','rgn_gcs'], 'checkgeom_results')
##print('  calculating area (%s)' % time.strftime('%H:%M:%S'))
##add_area('sp_gcs')
##add_area('rgn_gcs')
##print('  exporting shp and csv (%s)' % time.strftime('%H:%M:%S'))
##export_shpcsv(
##    fc   = 'sp_gcs',
##    flds = sp_area_flds,
##    shp  = '{0}/data/sp_gcs.shp'.format(ad),
##    csv  = '{0}/data/sp_data.csv'.format(gd))
##export_shpcsv(
##    fc   = 'rgn_gcs',
##    flds = rgn_area_flds,
##    shp  = '{0}/data/rgn_gcs.shp'.format(ad),
##    csv  = '{0}/data/rgn_data.csv'.format(gd))

# onshore or offshore. note: excluding potential sp_types: eez-inland, land-disputed & eez-disputed
# dice so buffering doesn't take forever
##for z in ('inland','offshore'):
##    print('select & copy: sp_%s_gcs (%s)' % (z, time.strftime('%H:%M:%S')))
##    arcpy.Select_analysis('sp_gcs', 'sp_%s_gcs' % z, "\"sp_type\"  IN (%s)" % dict_zone[z]['sp_types'])
##    arcpy.CopyFeatures_management('sp_%s_gcs' % z, 'sp_%s_dens1km_gcs' % z)
##    print('densify: sp_%s_dens1km_gcs (%s)' % (z, time.strftime('%H:%M:%S')))
##    arcpy.Densify_edit('sp_%s_dens1km_gcs' % z, 'DISTANCE', '1 Kilometers')
##    print('dice: sp_%s_dens1km_dice100k_gcs (%s)' % (z, time.strftime('%H:%M:%S')))
##    arcpy.Dice_management('sp_%s_dens1km_gcs' % z, 'sp_%s_dens1km_dice100k_gcs' % z, 100000)


# HACK for Antarctica
##sp_class     = 'ccamlr'
##dict_clasess = {'ccamlr':{'inland':['land','land-ccamlr'],
##                        'offshore':['eez-ccamlr']}}

# get list of spatial ids over which to iterate (b/c buffering all at once not working), skip ids without both inland and offshore components
##sp_dict_inland   = dict(arcpy.da.TableToNumPyArray('sp_inland_gcs', ['sp_id', 'sp_name'])); print(len(sp_dict_inland))
##sp_dict_offshore = dict(arcpy.da.TableToNumPyArray('sp_offshore_gcs', ['sp_id', 'sp_name']))
sp_dict_inland   = dict(arcpy.da.TableToNumPyArray('sp_inland_gcs'  , ['sp_id', 'sp_name'])) # , '"sp_type" IN (\'%s\')' % "','".join(dict_clasess[sp_class]['inland'])))
sp_dict_offshore = dict(arcpy.da.TableToNumPyArray('sp_offshore_gcs', ['sp_id', 'sp_name'])) #, '"sp_type" IN (\'%s\')' % "','".join(dict_clasess[sp_class]['offshore'])))
sp_ids_offshore_withland    = sorted(set(sp_dict_offshore.keys()) & set(sp_dict_inland.keys())) # fao or ccamlr regions without land
sp_ids_offshore_withoutland = sorted(set(sp_dict_offshore.keys()) - set(sp_dict_inland.keys()))
print 'skipping offshore sp_gcs without land (fao, ccamlr):'
print '\n  '.join(['%d: %s' % (id, sp_dict_offshore[id]) for id in sorted(sp_ids_offshore_withoutland)])
sp_dict = {x: sp_dict_inland[x] for x in sp_ids_offshore_withland}

# buffer
for buf in buffers:  # buf = 'inland1km'
    
    # identify buffer
    ##sp_buf  = 'sp_%s_%s_gcs'  % (buf, sp_class)
    ##rgn_buf = 'rgn_%s_%s_gcs' % (buf, sp_class)
    sp_buf  = 'sp_%s_gcs'  % buf
    rgn_buf = 'rgn_%s_gcs' % buf
    print('buffering: %s (%s)' % (sp_buf, time.strftime('%H:%M:%S')))    
    buf_zone, buf_dist, buf_units = re.search('(\\D+)(\\d+)(\\D+)', buf).groups()
    sp_ids =  sorted(sp_dict.iterkeys())

    for i, sp_id in enumerate(sorted(sp_dict.iterkeys())): # i, sp_id = (9999, 248500)
        sp_name = sp_dict[sp_id]
        buf_i = 'buf_%s_%06d' % (buf, sp_id)

        if not arcpy.Exists('%s_s_b_d' % buf_i):

            # clean up: DEBUG
            for fc in ('buf_tmp_sp', buf_i, '%s_d' % buf_i, '%s_r' % buf_i, '%s_d_r' % buf_i):
                if arcpy.Exists(fc): arcpy.Delete_management(fc)
            print('    (%03d of %d, %s) %06d %s ' % (i+1, len(sp_dict), time.strftime('%H:%M:%S'), sp_id, sp_name))            

            # buffer
            arcpy.Select_analysis(dict_zone[buf_zone]['buffer'], '%s_s' % buf_i, '"sp_id"=%d' % sp_id)        
            arcpy.Buffer_analysis('%s_s' % buf_i, '%s_s_b' % buf_i, '%s %s' % (buf_dist, buf_units_d[buf_units]), 'FULL', 'ROUND', 'ALL')
            arcpy.Dissolve_management('%s_s_b' % buf_i, '%s_s_b_d' % buf_i)
            arcpy.RepairGeometry_management('%s_s_b_d' % buf_i)

        if not arcpy.Exists('%s_s_b_d_i' % buf_i):
            try:
                print('    (%03d of %d, %s) %06d %s INTERSECT' % (i+1, len(sp_dict), time.strftime('%H:%M:%S'), sp_id, sp_name))
                arcpy.Intersect_analysis(['buf_%s_m_d' % buf, dict_zone[buf_zone]['intersect']], 'buf_%s_m_d_i' % buf, 'NO_FID')
                arcpy.RepairGeometry_management('buf_%s_m_d_i' % buf)
            else:
                print '      ERROR', sys.exc_info()[0]
                print '      FAILED: %06d %s' % (sp_id, sp_name)
                sp_ids.remove(sp_id)

    try:
        print('  buf_%s_m (%s)' % (buf, time.strftime('%H:%M:%S')))
        buf_ids = ['buf_%s_%06d_s_b_d_i' % (buf, sp_id) for sp_id in sp_ids]
        arcpy.Merge_management(buf_ids, 'buf_%s_m' % buf)
        arcpy.RepairGeometry_management('buf_%s_m' % buf)
            
        print('  dissolving to %s, %s (%s)' % (sp_buf, rgn_buf, time.strftime('%H:%M:%S')))
        arcpy.Dissolve_management('buf_%s_m' % buf, sp_flds)
        arcpy.Dissolve_management(sp_buf, rgn_buf, rgn_flds)

        print('  repairing %s, %s (%s)' % (sp_buf, rgn_buf, time.strftime('%H:%M:%S')))
        arcpy.RepairGeometry_management(sp_buf)
        arcpy.RepairGeometry_management(rgn_buf)

        # add areas
        print('  calculating areas (%s)' % time.strftime('%H:%M:%S'))
        add_area( sp_buf)
        add_area(rgn_buf)

        # export shp and csv
        print('  exporting shp and csv (%s)' % time.strftime('%H:%M:%S'))
        export_shpcsv(
            fc   = sp_buf,
            flds = sp_area_flds,
            shp  = '{0}/data/{1}.shp'.format(     ad, sp_buf),
            csv  = '{0}/data/{1}_data.csv'.format(ad, sp_buf))
        export_shpcsv(
            fc   = rgn_buf,
            flds = rgn_area_flds,
            shp  = '{0}/data/{1}.shp'.format(     ad, rgn_buf),
            csv  = '{0}/data/{1}_data.csv'.format(ad, rgn_buf))    
        print('  finished (%s)' % time.strftime('%H:%M:%S'))
    else:
        print '      ERROR', sys.exc_info()[0]
