from sampley import *



u_sightings = DataPoints.from_file(
    filepath=import_folder+'sightings.csv',
    x_col='lon',
    y_col='lat',
    crs_import='EPSG:4326',
    crs_working='EPSG:32619',
    datetime_col='datetime',
    tz_import='UTC-05:00'
)
u_sightings.save(folder=export_folder)  # , crs_export=4326, tz_export='UTC-07:00')
odps = DataPoints.open(export_folder, 'datapoints-sightings')  # , 32619, 'UTC-05:00')
odps.name, u_sightings.name
odps.parameters, u_sightings.parameters
odps.datapoints, u_sightings.datapoints
odps.datapoints['datetime'], u_sightings.datapoints['datetime']


u_sections = Sections.from_file(
    filepath=import_folder+'sections.gpkg',
    crs_working='EPSG:32619',
    datetime_col='datetime_beg',
    tz_import='UTC-05:00'
)
u_sections.save(folder=export_folder, crs_export=4326, tz_export='UTC-07:00')
osecs = Sections.open(export_folder, 'sections-sections', 32619, 'UTC-05:00')
osecs.name, u_sections.name
osecs.parameters, u_sections.parameters
osecs.sections, u_sections.sections
osecs.sections['datetime'], u_sections.sections['datetime']


u_periods = Periods.delimit(
    extent=u_sections,
    unit='day',
    num=8)
u_periods.save(folder=export_folder)
operiods = Periods.open(export_folder, 'periods-8d')
operiods.name, u_periods.name
operiods.parameters, u_periods.parameters
operiods.periods, u_periods.periods
operiods.periods['datetime_beg'], u_periods.periods['datetime_beg']


u_periods = Periods.delimit(
    extent=(['2019-01-25 10:18:13', '2019-03-03 14:32:57'], 'UTC-05:00'),
    unit='day',
    num=8)
u_periods.periods[['date_beg', 'date_mid', 'date_end']]
u_periods = Periods.delimit(
    extent=(['2019-01-25 10:18:13', '2019-10-03 14:32:57'], 'UTC-05:00'),
    unit='month',
    num=2)
u_periods.periods[['date_beg', 'date_mid', 'date_end']]
u_periods = Periods.delimit(
    extent=(['2019-01-25 10:18:13', '2023-10-03 14:32:57'], 'UTC-05:00'),
    unit='year',
    num=1)
u_periods.periods[['date_beg', 'date_mid', 'date_end']]
u_periods = Periods.delimit(
    extent=(['2019-01-25 10:18:13', '2019-03-03 14:32:57'], None),
    unit='day',
    num=8)
u_periods.periods[['date_beg', 'date_mid', 'date_end']]
u_periods = Periods.delimit(
    extent=(['2019-01-25 10:18:13', '2019-10-03 14:32:57'], None),
    unit='month',
    num=2)
u_periods.periods[['date_beg', 'date_mid', 'date_end']]
u_periods = Periods.delimit(
    extent=(['2019-01-25 10:18:13', '2023-10-03 14:32:57'], None),
    unit='year',
    num=1)
u_periods.periods[['date_beg', 'date_mid', 'date_end']]
u_periods.save(folder=export_folder)
operiods = Periods.open(export_folder, 'periods-8d')
operiods.name, u_periods.name
operiods.parameters, u_periods.parameters
operiods.periods, u_periods.periods
operiods.periods['datetime_beg'], u_periods.periods['datetime_beg']


u_cells = Cells.delimit(
    extent=u_sections,
    var='hexagonal',
    side=5000)
u_cells.save(folder=export_folder, crs_export=4326)

u_segments = Segments.delimit(
    sections=u_sections,
    var='simple',
    target=10000,
    rand=True)
u_segments.save(folder=export_folder, crs_export=4326)

u_presences = Presences.delimit(
    datapoints=u_sightings,
    presence_col='individuals')
u_presences.thin(
    sp_threshold=10000,
    tm_threshold=5,
    tm_unit='day')
u_presences.save(folder=export_folder, crs_export=4326)

u_presencezones = PresenceZones.delimit(
    sections=u_sections,
    presences=u_presences,
    sp_threshold=10000,
    tm_threshold=5,
    tm_unit='day',
)
u_presencezones.save(folder=export_folder, crs_export=4326)

u_absences = Absences.delimit(
    sections=u_sections,
    presencezones=u_presencezones,
    var='along',
    target=20)
u_absences.thin(
    sp_threshold=10000,
    tm_threshold=5,
    tm_unit='day',
    target=9)
u_absences.save(folder=export_folder, crs_export=4326)


#####
# open


operiods = Periods.open(export_folder, 'periods-8d')
operiods.name
operiods.parameters
operiods.periods

ocells = Cells.open(export_folder, basename, 32619)
ocells.name
ocells.parameters
ocells.cells

osegs = Segments.open(export_folder, 'segments-s10000m', 32619)
osegs.name
osegs.parameters
osegs.segments

opres = Presences.open(export_folder, 'presences-sightings', 32619)
opres.name
opres.parameters
opres.full
opres.kept
opres.removed

oals = PresenceZones.open(export_folder, 'presencezones-10000m-5day', 32619)
oals.name
oals.parameters
oals.presencezones

oabs = Absences.open(export_folder, 'absences-a-10000m-5day', 32619)
oabs.name
oabs.parameters
oabs.full
oabs.kept
oabs.removed





