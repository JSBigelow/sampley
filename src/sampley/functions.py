# Core functions for sampling

##############################################################################################################
# Imports
from collections import Counter
from datetime import timedelta
from functools import reduce
import math
from pyproj import Geod
from shapely import Point, MultiPoint, LineString, MultiLineString, Polygon, line_locate_point
from shapely.errors import GEOSException
from shapely.ops import substring, nearest_points

from .auxiliary import *


##############################################################################################################
# Stage 1: Opening functions
def datapoints_from_file(
        filepath: str,
        x_col: str = 'lon',
        y_col: str = 'lat',
        geometry_col: str = None,
        crs_input: str | int | pyproj.crs.crs.CRS = None,
        crs_working: str | int | pyproj.crs.crs.CRS = None,
        datetime_col: str = None,
        datetime_format: str = None,
        tz_input: str | timezone | pytz.BaseTzInfo | None = None,
        tz_working: str | timezone | pytz.BaseTzInfo | None = None,
        datapoint_id_col: str = None,
        section_id_col: str = None):

    # open file
    check_dtype(par='filepath', obj=filepath, dtypes=str)
    datapoints = open_file(filepath)  # open the datapoints file

    # spatial
    if not isinstance(datapoints, gpd.GeoDataFrame):  # if not already GeoDataFrame (i.e., input file is CSV/XLSX)...
        check_crs(par='crs_input', crs=crs_input)
        if geometry_col is None:  # if no geometry column specified
            check_dtype(par='x_col', obj=x_col, dtypes=str, none_allowed=True)
            check_dtype(par='y_col', obj=y_col, dtypes=str, none_allowed=True)
            check_cols(df=datapoints, cols=[x_col, y_col])
            datapoints = parse_xy(datapoints, x_col, y_col, crs_input)  # convert to geopandas GeoDataFrame
        elif geometry_col is not None:  # else if geometry column is specified
            check_dtype(par='geometry_col', obj=geometry_col, dtypes=str, none_allowed=True)
            check_cols(df=datapoints, cols=geometry_col)
            datapoints = parse_geoms(datapoints, geometry_col, crs_input)  # convert to geopandas GeoDataFrame

    gtypes = list(set([type(geometry) for geometry in datapoints.geometry]))  # get geometry types
    if len(gtypes) == 1 and gtypes[0] == Point:  # if there is one type: Point
        pass
    elif ((len(gtypes) == 1 and gtypes[0] == MultiPoint) or  # else if there is one type: MultiPoint...
          (len(gtypes) == 2 and Point in gtypes and MultiPoint in gtypes)):  # ...or two types: MultiPoint and Point...
        print('Note: some or all geometries are MultiPoints and will be exploded to Points.')
        datapoints = datapoints.explode()  # explode MultiPoints to Points
    else:  # else if there are other types, print error message...
        raise TypeError(f'geometries are not Points or MultiPoints. \nGeometry types include {', '.join(gtypes)}.')

    if crs_working is not None:  # if a working CRS is provided
        check_crs(par='crs_working', crs=crs_working)
        datapoints = reproject_crs(datapoints, crs_working)  # reproject to CRS working

    check_projected(obj_name='datapoints', crs=datapoints.crs)  # check that the CRS is projected

    # temporal
    if datetime_col is not None:  # if datetime column specified
        check_dtype(par='datetime_col', obj=datetime_col, dtypes=str)
        check_cols(df=datapoints, cols=datetime_col)
        check_dtype(par='datetime_format', obj=datetime_format, dtypes=str, none_allowed=True)
        check_tz(par='tz_input', tz=tz_input, none_allowed=True)
        parse_dts(datapoints, datetime_col, datetime_format, tz_input)  # parse datetimes and set TZ
        if tz_working is not None:  # if a working timezone is specified
            check_tz(par='tz_working', tz=tz_working)
            datapoints = convert_tz(datapoints, datetime_col, tz_working)  # convert to working TZ
        if datetime_col != 'datetime':  # if datetime column not already called 'datetime'...
            datapoints['datetime'] = datapoints[datetime_col]  # ...rename datetime column
            print(f'Note: column \'{datetime_col}\' renamed to \'datetime\'.')
    else:  # else if no datetime column specified...
        datapoints['datetime'] = None  # ...make dummy column with None

    if section_id_col is not None:  # if a section ID column is specified
        check_dtype(par='section_id_col', obj=section_id_col, dtypes=str)
        check_cols(datapoints, section_id_col)
        if section_id_col != 'section_id':  # if section ID column not called 'section_id'...
            datapoints.rename(columns={section_id_col: 'section_id'}, inplace=True)  # ...rename it
            print(f'Note: column \'{section_id_col}\' renamed to \'section_id\'.')
        key_cols = ['datapoint_id', 'section_id', 'geometry', 'datetime']
    else:
        key_cols = ['datapoint_id', 'geometry', 'datetime']

    if datapoint_id_col is not None:  # if a datapoint ID column is specified
        check_dtype(par='datapoint_id_col', obj=datapoint_id_col, dtypes=str)
        check_cols(datapoints, datapoint_id_col)
        if datapoints[datapoint_id_col].nunique() < len(datapoints[datapoint_id_col]):  # check that all IDs are unique
            raise Exception('\n\n____________________'
                            '\nError: two or more datapoints have the same datapoint ID.'
                            f'\nPlease ensure that all values in \'{datapoint_id_col}\' are unique.'
                            '\nAlternatively, leave \'datapoint_id_col\' unspecified and datapoint IDs will be'
                            'generated automatically.'
                            '\n____________________')
        if datapoint_id_col != 'datapoint_id':  # if datapoint ID column not called 'datapoint_id'...
            datapoints.rename(columns={datapoint_id_col: 'datapoint_id'}, inplace=True)  # ...rename it
            print(f'Note: column \'{datapoint_id_col}\' renamed to \'datapoint_id\'.')
    else:  # else if datapoint ID column is not specified
        datapoints['datapoint_id'] = ['d' + str(i).zfill(len(str(len(datapoints))))  # make datapoint IDs
                                      for i in range(1, len(datapoints) + 1)]
        print('Success: datapoint IDs successfully generated.')

    datapoints = datapoints[key_cols + [c for c in datapoints if c not in key_cols]]  # reorder columns
    return datapoints


def sections_from_file(
        filepath: str,
        crs_working: str | int | pyproj.crs.crs.CRS = None,
        datetime_col: str = None,
        datetime_format: str = None,
        tz_input: str | timezone | pytz.BaseTzInfo | None = None,
        tz_working: str | timezone | pytz.BaseTzInfo | None = None,
        section_id_col: str = None):

    # open file
    check_dtype(par='filepath', obj=filepath, dtypes=str)
    sections = open_file(filepath)  # open the sections file

    # spatial
    gtypes = list(set([type(geometry) for geometry in sections.geometry]))  # get geometry types
    if len(gtypes) == 1 and gtypes[0] == LineString:  # if there is one type: LineString
        pass
    elif ((len(gtypes) == 1 and gtypes[0] == MultiLineString) or  # else if there is one type: MultiLineString...
          (len(gtypes) == 2 and  # ...or two types: ...
           LineString in gtypes and MultiLineString in gtypes)):  # ...MultiLineString and LineString
        print('Note: some or all geometries are MultiLineStrings and will be exploded to LineStrings.')
        sections = sections.explode()  # explode MultiLineStrings to LineStrings
    else:  # else if there are other types, print error message...
        raise TypeError('geometries are not LineStrings or MultiLineStrings.'
                        f'\nGeometry types include {', '.join(gtypes)}.'
                        '\nTo make sections from Points, first input the Points as DataPoints and then'
                        ' use Sections.from_datapoints() to make Sections from the DataPoints.')

    if crs_working is not None:  # if a working CRS is provided
        check_crs(par='crs_working', crs=crs_working)
        sections = reproject_crs(sections, crs_working)  # reproject to CRS working

    check_projected(obj_name='sections', crs=sections.crs)  # check that the CRS is projected

    # temporal
    if datetime_col is not None:  # if datetime column specified
        check_dtype(par='datetime_col', obj=datetime_col, dtypes=str)
        check_cols(df=sections, cols=datetime_col)
        check_dtype(par='datetime_format', obj=datetime_format, dtypes=str, none_allowed=True)
        check_tz(par='tz_input', tz=tz_input, none_allowed=True)
        parse_dts(sections, datetime_col, datetime_format, tz_input)  # parse datetimes and set TZ
        if tz_working is not None:  # if a working timezone is specified
            check_tz(par='tz_working', tz=tz_working)
            sections = convert_tz(sections, datetime_col, tz_working)  # convert to working TZ
        if datetime_col != 'datetime':  # if datetime column not already called 'datetime'...
            sections.rename(columns={datetime_col: 'datetime'}, inplace=True)  # ...rename datetime column
            print(f'Note: column \'{datetime_col}\' renamed to \'datetime\'.')
    else:  # else if no datetime column specified...
        sections['datetime'] = None  # ...make dummy column with None

    if section_id_col is not None:  # if a section ID column is specified
        check_dtype(par='section_id_col', obj=section_id_col, dtypes=str)
        check_cols(sections, section_id_col)
        if sections[section_id_col].nunique() < len(sections[section_id_col]):  # check that all IDs are unique
            raise Exception('\n\n____________________'
                            '\nError: two or more sections have the same section ID.'
                            f'\nPlease ensure that all values in \'{section_id_col}\' are unique.'
                            '\nAlternatively, leave \'section_id_col\' unspecified and section IDs will be'
                            'generated automatically.'
                            '\n____________________')
        if section_id_col != 'section_id':  # if section ID column not called 'section_id'...
            sections.rename(columns={section_id_col: 'section_id'}, inplace=True)  # ...rename it
            print(f'Note: column \'{section_id_col}\' renamed to \'section_id\'.')
    else:  # else if section ID column is not specified
        sections['section_id'] = ['s' + str(i).zfill(len(str(len(sections))))  # make section IDs
                                  for i in range(1, len(sections) + 1)]
        print('Success: section IDs successfully generated.')

    sections = sections[['section_id', 'geometry', 'datetime'] +  # reorder columns
                        [c for c in sections if c not in ['section_id', 'geometry', 'datetime']]]
    return sections


def sections_from_datapoints(
        datapoints: gpd.GeoDataFrame,
        cols: dict = None,
        sortby: str | list[str] = None,
        section_id_col: str = 'section_id'):

    sections = datapoints.copy()  # copy datapoints GeoDataFrame

    check_dtype(par='section_id_col', obj=section_id_col, dtypes=str)
    check_cols(sections, section_id_col)

    if sortby is not None:  # if there is column to sort by
        check_dtype(par='sortby', obj=sortby, dtypes=[str, list])
        check_cols(sections, sortby)
        sortby = sortby if isinstance(sortby, list) else [sortby] if isinstance(sortby, str) else None  # sortby to list
        sortby = ['section_id'] + [col for col in sortby if col != 'section_id']  # add 'section_id' to sortby list
        sections.sort_values(sortby, inplace=True)  # sort by sortby list

    if cols is not None:  # if aggregation dict provided
        check_dtype(par='agg_dict', obj=cols, dtypes=dict)
        check_cols(sections, list(cols.keys()))
    else:  # else no aggregation dict provided..
        cols = {}  # ...make empty dict

    try:
        sections = sections.groupby(['section_id']).agg(  # group by section ID and...
            cols | {  # ...combine the aggregation dict with dict to...
               'geometry': lambda geometry: LineString(list(geometry)),  # ...convert the Points to LineStrings...
               'datetime': 'first',  # ...keep the first datetime
            }).reset_index()  # ...and reset the index
    except GEOSException:  # occurs if attempt to make a LineString from a single Point
        raise GEOSException('\n\n____________________'  # raise error
                            '\nGEOSException: one or more sections contains a single datapoint.'
                            '\nPlease ensure that all sections have a minimum of two datapoints.'
                            '\n____________________')
    sections = gpd.GeoDataFrame(sections, geometry='geometry', crs=datapoints.crs)  # GeoDataFrame
    sections = sections[['section_id', 'geometry', 'datetime'] +  # reorder columns
                        [c for c in sections if c not in ['section_id', 'geometry', 'datetime']]]
    return sections


##############################################################################################################
# Stage 2: Functions for delimiters (Cells, Segments, Periods, Presences, AbsenceLines, Absences)
def periods_delimit(
        extent: pd.DataFrame | tuple[list, str],
        num: int | float,
        unit: str,
        datetime_col: str = 'datetime')\
        -> pd.DataFrame:

    check_dtype(par='extent', obj=extent, dtypes=[pd.DataFrame, tuple])
    check_dtype(par='num', obj=num, dtypes=[int, float])
    check_dtype(par='unit', obj=unit, dtypes=str)
    unit = unit.lower()
    check_opt(par='unit', opt=unit, opts=['day', 'd', 'month', 'm', 'year', 'y'])

    if isinstance(extent, tuple):  # if extent is a tuple...
        tz = extent[1]  # get timezone
        check_tz(par='extent timezone', tz=tz)
        extent = pd.DataFrame({'datetime': extent[0]})  # make DataFrame from extent list
        parse_dts(extent, 'datetime', tz)  # parse datetimes
        datetime_col = 'datetime'  # set datetime column
    elif isinstance(extent, pd.DataFrame):  # if extent is a DataFrame
        check_dtype(par='datetime_col', obj=datetime_col, dtypes=str)
        check_cols(df=extent, cols=datetime_col)

    # get the begin datetime
    timecodes = {'d': 'd', 'm': 'MS', 'y': 'YS'}  # set time period codes
    timecode = str(int(num)) + timecodes[unit[0]]  # make time code for grouper by combining number and unit
    periods = extent.groupby(pd.Grouper(key=datetime_col, freq=timecode)).first().reset_index()  # group
    periods.rename(columns={datetime_col: 'datetime_beg'}, inplace=True)  # rename column

    # get the end datetime (different for days, months, and years)
    if unit in ['d', 'day']:  # days: add the number of days to the begin datetime and subtract 1 sec
        periods['datetime_end'] = periods['datetime_beg'].apply(lambda d: d + timedelta(days=num, seconds=-1))
    elif unit in ['m', 'month']:  # months: add years and months based on number of months and subtract 1 sec
        periods['datetime_end'] = periods['datetime_beg'].apply(lambda d: datetime(
            d.year + (d.month + num) // 12 if (d.month + num) % 12 != 0 else d.year + (d.month + num) // 12 - 1,
            (d.month + num) % 12 if (d.month + num) % 12 != 0 else 12,
            d.day)) - timedelta(seconds=1)
    elif unit in ['y', 'year']:  # years: add the number of years to the begin datetime and subtract 1 sec
        periods['datetime_end'] = periods['datetime_beg'].apply(lambda d: datetime(
            d.year + num, d.month, d.day)) - timedelta(seconds=1)

    periods['datetime_mid'] = periods.apply(  # get mid datetime by adding difference to begin datetime, floor to secs
        lambda r: (r['datetime_beg'] + (r['datetime_end'] - r['datetime_beg']) / 2).floor('s'), axis=1)
    periods['period_id'] = periods['datetime_beg'].apply(  # make period IDs
        lambda d: 'p' + str(d)[:10] + '-' + str(int(num)) + unit[0])
    periods = periods[['period_id', 'datetime_beg', 'datetime_mid', 'datetime_end']]  # keep only necessary columns
    return periods


def cells_delimit(
        extent: gpd.GeoDataFrame | tuple[list, str | int | pyproj.crs.crs.CRS],
        var: str,
        side: int | float,
        buffer: int | float = None)\
        -> gpd.GeoDataFrame:

    check_dtype(par='extent', obj=extent, dtypes=[gpd.GeoDataFrame, tuple])
    check_dtype(par='var', obj=var, dtypes=str)
    var = var.lower()
    check_opt(par='var', opt=var, opts=['rectangular', 'hexagonal', 'r', 'h'])
    check_dtype(par='side', obj=side, dtypes=[int, float])

    if isinstance(extent, tuple):  # if extent is a tuple...
        x_min, y_min, x_max, y_max = extent[0]  # ...get the min and max x and y values
        crs = extent[1]  # ...get the CRS
        check_crs(par='extent', crs=crs)
    elif isinstance(extent, gpd.GeoDataFrame):  # if the extent is a GeoDataFrame...
        x_min, y_min, x_max, y_max = extent.total_bounds  # ...get the min and max x and y values
        crs = extent.crs  # ...get the CRS
    else:  # else if extent is neither tuple nor GeoDataFrame (should never be reached given check_dtype() above)
        raise TypeError
    check_projected(obj_name='extent', crs=crs)

    if buffer is not None:  # if a buffer is provided...
        check_dtype(par='buffer', obj=buffer, dtypes=[int, float])
        x_min -= buffer  # ...adjust x and y mins and maxs
        y_min -= buffer
        x_max += buffer
        y_max += buffer

    # make the polygons
    if var in ['r', 'rectangular']:  # rectangular variation
        var = 'rectangular'
        xs = list(np.arange(x_min, x_max + side, side))  # list of x values
        ys = list(np.arange(y_min, y_max + side, side))  # list of y values
        polygons = []  # list for the polygons
        for y in ys[:-1]:  # for each row
            for x in xs[:-1]:  # for each column
                polygons.append(Polygon([  # create cell by specifying the following points:
                    (x, y),  # bottom left
                    (x + side, y),  # bottom right
                    (x + side, y + side),  # top right
                    (x, y + side)]))  # top left
    elif var in ['h', 'hexagonal']:  # hexagonal variation
        var = 'hexagonal'
        hs = np.sqrt(3) * side  # horizontal spacing
        vs = 1.5 * side  # vertical spacing
        nr = int(np.ceil((y_max - y_min) / vs)) + 1  # number of rows
        nc = int(np.ceil((x_max - x_min) / hs)) + 1  # number of columns
        ocx, ocy = x_min, y_min  # origin cell centre point
        olx, oly = (ocx + side * math.cos(math.pi / 180 * 210),
                    ocy + side * math.sin(math.pi / 180 * 210))  # origin cell lower left point
        cxs, cys = np.meshgrid([ocx + hs * n for n in range(0, nc)],
                               [ocy + vs * n for n in range(0, nr)])  # all cells centre points
        lxs, lys = np.meshgrid([olx + hs * n for n in range(0, nc)],
                               [oly + vs * n for n in range(0, nr)])  # all cells lower left points
        polygons = []  # list for the polygons
        ri = 1  # row index
        for cxr, cyr, lxr, lyr in zip(cxs, cys, lxs, lys):  # for each row
            if ri % 2 == 0:  # if row is even...
                cxr, lxr = cxr + hs/2, lxr + hs/2  # ...add half a horizontal spacing
            for cx, cy, lx, ly in zip(cxr, cyr, lxr, lyr):  # for centre and lower left points of each cell
                polygons.append(Polygon([(cx, cy + side), (lx + hs, ly + side), (lx + hs, ly),
                                         (cx, cy - side), (lx, ly), (lx, ly + side)]))  # create cell
            ri += 1  # increase row index
    else:  # else the variation is unknown...
        polygons = None

    cells = gpd.GeoDataFrame({'polygon': polygons}, geometry='polygon', crs=crs)  # GeoDataFrame
    cells['centroid'] = cells.centroid  # get cell centroids
    cells['cell_id'] = ['c' + str(i).zfill(len(str(len(cells)))) +  # make cell IDs
                        '-' + var[0] + str(side) + cells.crs.axis_info[0].unit_name[0]
                        for i in range(1, len(cells) + 1)]
    cells = cells[['cell_id', 'polygon', 'centroid']]  # keep only necessary columns
    return cells


def segments_delimit(
        sections: gpd.GeoDataFrame,
        var: str,
        target: int | float,
        rand: bool = False)\
        -> gpd.GeoDataFrame:

    check_dtype(par='sections', obj=sections, dtypes=gpd.GeoDataFrame)
    check_projected(obj_name='sections', crs=sections.crs)
    check_cols(sections, ['datetime', 'section_id'])
    check_dtype(par='var', obj=var, dtypes=str)
    var = var.lower()
    check_opt(par='var', opt=var, opts=['s', 'simple', 'j', 'joining', 'r', 'redistribution'])
    check_dtype(par='target', obj=target, dtypes=[int, float])
    check_dtype(par='rand', obj=rand, dtypes=bool)

    no_segments_max = np.ceil(sections.length.sum() / target + len(sections))  # maximum possible number of segments
    segment_no = 1  # set the segment number to 1
    segments_dicts = []  # list for segments

    for section_id, section_geometry, section_datetime in (  # for each section, its geometry, and its datetime
            zip(sections['section_id'], sections['geometry'], sections['datetime'])):
        section_length = section_geometry.length  # section length
        no_segments_prov = int(section_length // target)  # provisional number of segments
        remainder_length = section_length % target  # remainder length

        if no_segments_prov > 0:  # if section needs to be cut, calculate segment lengths (different for each variation)
            if var in ['s', 'simple']:  # simple variation
                var = 'simple'
                if remainder_length > 0:  # if there is a remainder (almost inevitable)
                    lengths = [target] * no_segments_prov + [remainder_length]
                else:  # if there is no remainder (very unlikely, but possible)
                    lengths = [target] * no_segments_prov
            elif var in ['j', 'joining']:  # joining variation
                var = 'joining'
                if remainder_length >= (target / 2):  # if the remainder is equal to or more than half the target...
                    lengths = [target] * no_segments_prov + [remainder_length]
                else:  # else the remainder is less than half the target...
                    lengths = [target] * (no_segments_prov - 1) + [target + remainder_length]
            elif var in ['r', 'redistribution']:  # redistribution variation
                var = 'redistribution'
                if remainder_length >= (target / 2):  # if the remainder is equal to or more than half the target...
                    lengths = [section_length / (no_segments_prov + 1)] * (no_segments_prov + 1)
                else:  # else the remainder is less than half the target length...
                    lengths = [section_length / no_segments_prov] * no_segments_prov
            else:  # else the variation is unknown (should never be reached given check_opt() above)
                raise KeyError
        else:  # else the section does not need to be cut
            lengths = [section_length]  # single segment length

        # if using simple or joining variation and randomising and there are multiple segments...
        # ...shuffle lengths to place remainder / joined segment at random point along section
        if var in ['s', 'simple', 'j', 'joining'] and rand and len(lengths) > 1:
            random.shuffle(lengths)

        # calculate locations of the begin and end breakpoints (as distances from the beginning of the section: DFBSEC)
        dfbsecs_beg = [0] + list(np.cumsum(lengths))[:-1]  # begin breakpoints
        dfbsecs_end = list(np.cumsum(lengths))  # end breakpoints

        for dfbsec_beg, dfbsec_end in zip(dfbsecs_beg, dfbsecs_end):  # for each begin and end breakpoint (segment)
            segment_id = ('s' + str(int(segment_no)).zfill(len(str(int(no_segments_max)))) +  # segment ID
                          '-' + var[0] + str(target) + sections.crs.axis_info[0].unit_name[0])
            segment_geometry = substring(section_geometry, dfbsec_beg, dfbsec_end)  # segment as a LineString
            segments_dicts.append({  # append to list a dict containing...
                'segment_id': segment_id,  # ...segment ID
                'line': segment_geometry,  # ...segment geometry
                'date': section_datetime.date() if section_datetime is not None else None,  # ...segment date
                'section_id': section_id,  # ...section ID
                'dfbsec_beg': dfbsec_beg,  # ...distance from beginning of section to begin breakpoint
                'dfbsec_end': dfbsec_end  # ...distance from beginning of section to end breakpoint
            })
            segment_no += 1  # increase segment number by 1

    segments = gpd.GeoDataFrame(segments_dicts, geometry='line', crs=sections.crs)  # GeoDataFrame of segments
    segments['midpoint'] = segments['line'].apply(lambda line: line.interpolate(line.length / 2))  # midpoints
    segments = segments[['segment_id', 'line', 'midpoint', 'date', 'section_id', 'dfbsec_beg', 'dfbsec_end']]  # nec
    return segments


def presences_delimit(
        datapoints: gpd.GeoDataFrame,
        presence_col: str | None = None)\
        -> gpd.GeoDataFrame:

    check_dtype(par='datapoints', obj=datapoints, dtypes=gpd.GeoDataFrame)

    presences = datapoints.copy()  # copy the datapoints
    if presence_col is not None:  # if a presence column is specified
        check_dtype(par='presence_col', obj=presence_col, dtypes=str)
        check_cols(df=datapoints, cols=presence_col)
        try:
            presences = presences[presences[presence_col] > 0].reset_index(drop=True)  # select only detections
        except TypeError:
            raise TypeError(
                '\n\n____________________'
                f'\nTypeError: The column \'{presence_col}\' (i.e., the presence column) contains invalid values.'
                '\nValues in the presence column must be integers or floats.'
                f'\nPlease check the values in \'{presence_col}\'.'
                '\n____________________')

    presences.rename(columns={'geometry': 'point', 'datetime': 'date'}, inplace=True)  # rename columns
    presences['date'] = presences['date'].apply(  # get dates (if there are datetimes)
        lambda dt: pd.to_datetime(dt.date()) if isinstance(dt, (datetime, pd.Timestamp)) else dt)
    presences = gpd.GeoDataFrame(presences, geometry='point', crs=datapoints.crs)  # GeoDataFrame
    presences['point_id'] = ['p' + str(i).zfill(len(str(len(presences))))
                             for i in range(1, len(presences) + 1)]  # create point IDs
    presences = presences[['point_id', 'point', 'date', 'datapoint_id']]  # reorder columns
    return presences


def absencelines_delimit(
        sections: gpd.GeoDataFrame,
        presences: gpd.GeoDataFrame,
        sp_threshold: int | float,
        tm_threshold: int | float | None = None,
        tm_unit: str | None = None)\
        -> gpd.GeoDataFrame:

    # surveyed lines
    check_dtype(par='sections', obj=sections, dtypes=gpd.GeoDataFrame)
    absencelines = sections.copy()[['section_id', 'datetime', 'geometry']]
    absencelines['date'] = absencelines['datetime'].apply(
        lambda dt: pd.to_datetime(dt.date()) if isinstance(dt, (datetime, pd.Timestamp)) else dt)

    # presence zones
    check_dtype(par='presences', obj=presences, dtypes=gpd.GeoDataFrame)
    check_dtype(par='sp_threshold', obj=sp_threshold, dtypes=[int, float])
    if tm_threshold is not None and tm_unit is not None:  # if there is a temporal threshold and how
        check_dtype(par='tm_threshold', obj=tm_threshold, dtypes=[int, float], none_allowed=True)
        check_dtype(par='tm_unit', obj=tm_unit, dtypes=str)
        tm_unit = tm_unit.lower()
        check_opt(par='tm_unit', opt=tm_unit, opts=['day', 'doy', 'year'])
        print(f'Note: absence lines to be generated with a temporal threshold of {tm_threshold} {tm_unit}(s).')

        absencelines['unit'] = get_units(datetimes=absencelines['date'], tm_unit=tm_unit)
        presences['unit'] = get_units(datetimes=presences['date'], tm_unit=tm_unit)
        presencezones = []
        for section_unit in absencelines['unit'].unique():
            presences_overlap = []
            if tm_unit.lower() in ['year', 'day']:
                for presence_unit, presence_point in zip(presences['unit'], presences['point']):
                    if abs(section_unit - presence_unit) <= tm_threshold:
                        presences_overlap.append(presence_point)
            elif tm_unit.lower() in ['doy']:
                tm_threshold_complementary = 365 - tm_threshold
                for presence_unit, presence_point in zip(presences['unit'], presences['point']):
                    inner_diff = max(section_unit, presence_unit) - min(section_unit, presence_unit)
                    if inner_diff <= tm_threshold or inner_diff >= tm_threshold_complementary:
                        presences_overlap.append(presence_point)
            presencezones.append({
                'unit': section_unit,
                'presencezones':
                    MultiPoint(presences_overlap).buffer(sp_threshold) if len(presences_overlap) > 0 else None})
        absencelines = pd.merge(absencelines, pd.DataFrame(presencezones), on='unit', how='left')
        absencelines['presencezones'] = gpd.GeoSeries(absencelines['presencezones'], crs=presences.crs)
        absencelines.drop('unit', axis=1, inplace=True)
        presences.drop('unit', axis=1, inplace=True)
    else:
        print('Note: absence lines to be generated without a temporal threshold.')
        absencelines['presencezones'] = MultiPoint(presences['point']).buffer(sp_threshold)

    # absence lines
    absencelines['absencelines'] = (
        absencelines.apply(lambda r:  # take surveyed lines and detection zones and...
                            r['geometry'].difference(r['presencezones'])  # ...get the difference between them...
                            if r['presencezones']  # ...but only if there are presence zones...
                            else r['geometry'], axis=1))  # ...otherwise absence lines are the surveyed lines
    absencelines = absencelines[['section_id', 'date', 'absencelines', 'presencezones']]  # necessary columns
    absencelines = gpd.GeoDataFrame(absencelines, geometry='absencelines', crs=sections.crs)  # GeoDataFrame
    return absencelines


def absences_delimit(
        absencelines: gpd.GeoDataFrame,
        var: str,
        target: int | float,
        dfls: list[int | float] = None)\
        -> gpd.GeoDataFrame:

    check_dtype(par='absencelines', obj=absencelines, dtypes=gpd.GeoDataFrame)
    check_dtype(par='var', obj=var, dtypes=str)
    var = var.lower()
    check_opt(par='var', opt=var, opts=['along', 'a', 'from', 'f'])
    check_dtype(par='target', obj=target, dtypes=int)
    check_dtype(par='dfls', obj=dfls, dtypes=list, none_allowed=True)

    absencelines['dfbal'] = absencelines.geometry.length.cumsum()
    absence_line = absencelines.geometry.union_all()  #
    absences_list = []  # list for the absences
    i = 0
    while i < target:  # while count of absences is less than the target to be generated
        # generate an absence point (depends on variation)
        if var in ['a', 'along']:  # along-the-line variation - randomly sample point along absence line
            point = absence_line.interpolate(random.uniform(a=0, b=absence_line.length))  # point along line
            dfbal = line_locate_point(absence_line, point)  # get distance from beginning of absence line to point a
            absenceline = absencelines.iloc[absencelines[absencelines['dfbal'] > dfbal]['dfbal'].idxmin()]  # get absence line along which point a lies
            # if-point-not-in-corresponding-presence-zones check not necessary as this will never happen
            absences_list.append({  # append...
                'point': point,  # ...point
                'date': absenceline['date'],  # ...date
                'dfbal': dfbal})  # ...distance from beginning of absence line to point a
            i += 1  # increase the count

        elif var in ['f', 'from']:  # from-the-line variation - randomly sample point from absence line
            dist = random.uniform(a=0, b=absence_line.length-0.001)  # randomly select distance along absence line
            point_a = absence_line.interpolate(dist)  # make point at that distance
            point_b = absence_line.interpolate(dist+0.001)  # make point at that distance plus a tiny distance
            dfl = random.choice(dfls)  # randomly select distance from the line)
            side = np.random.choice(['left', 'right'])  # randomly choose side
            # generate a point at the specified distance from the line by...
            #   ...making a tiny line from point a to point b - LineString()
            #   ...making a line parallel to the tiny line at the specified distance - parallel_offset()
            #   ...getting the first coordinate of the parallel - coords[0]
            point = Point(LineString([point_a, point_b]).parallel_offset(dfl, side).extract[0])  # point

            dfbal = line_locate_point(absence_line, point_a)  # get distance from beginning of absence line to point a
            absenceline = absencelines.iloc[absencelines[absencelines['dfbal'] > dfbal]['dfbal'].idxmin()]  # get absence line along which point a lies
            if not point.intersects(absenceline['presencezones']):  # if point not in corresponding presence zones...
                absences_list.append({  # ...append...
                    'point': point,  # ...point
                    'date': absenceline['date'],  # ...date
                    'point_al': point_a,  # ...point a
                    'dfbal': dfbal})  # ...distance from beginning of absence line to point a
                i += 1  # increase the count

        else:  # unrecognised variation (should not be reached given check_opt() above)
            raise Exception

    absences = gpd.GeoDataFrame(absences_list, geometry='point', crs=absencelines.crs)  # GeoDataFrame
    absences = absences.sort_values(['date', 'dfbal']).reset_index(drop=True)  # sort by date and distance
    absences['point_id'] = ['a' + str(i).zfill(len(str(target))) for i in range(1, target + 1)]  # create point IDs
    if var in ['a', 'along']:  # along-the-line variation...
        absences = absences[['point_id', 'point', 'date']]  # ...necessary columns
    elif var in ['f', 'from']:  # from-the-line variation...
        absences = absences[['point_id', 'point', 'date', 'point_al']]  # ...necessary columns
    remove_cols(absencelines, 'dfbal')  # clean up
    # print('Please ignore RuntimeWarning: invalid value encountered in line_locate_point')
    return absences


##############################################################################################################
# Stage 3: Functions for Samples
def assign_cells(gdf: gpd.GeoDataFrame, cells: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    geometry_col = gdf.geometry.name
    crs = gdf.crs

    remove_cols(gdf, ['cell_id', 'polygon'])  # remove columns (if applicable)
    gdf = gpd.sjoin(gdf, cells[['cell_id', 'polygon']], how='left')  # spatial join
    gdf = gdf.drop('index_right', axis=1)  # drop index_right (byproduct of spatial join)

    gdf = gpd.GeoDataFrame(gdf, geometry=geometry_col, crs=crs)
    return gdf


def assign_periods(gdf: gpd.GeoDataFrame, periods: pd.DataFrame | str | None) -> gpd.GeoDataFrame:

    geometry_col = gdf.geometry.name
    crs = gdf.crs

    if isinstance(periods, pd.DataFrame):  # if periods were delimited with delimit_periods()
        remove_cols(gdf, ['period_id'])  # remove columns (if applicable)
        gdf = pd.merge_asof(gdf.sort_values('datetime'), periods[['period_id', 'datetime_beg']],  # temporal join
                            left_on='datetime', right_on='datetime_beg', direction='backward')
        remove_cols(df=gdf, cols='datetime_beg')
        gdf = gdf.sort_index()
    elif isinstance(periods, str):  # if periods are preset and the column name has been entered
        check_cols(df=gdf, cols=periods)
        if periods != 'period_id':  # if periods column not called 'period_id'...
            gdf['period_id'] = gdf[periods]  # ...duplicate it
            print(f'Success: column \'period_id\' made from column \'{periods}\'.')
    elif not periods:  # if there are no periods
        gdf['period_id'] = 'none'
    else:  # period is not of a recognised datatype
        raise TypeError('\nunable to assign periods. Periods of invalid datatype.')

    gdf = gpd.GeoDataFrame(gdf, geometry=geometry_col, crs=crs)
    return gdf


def assign_segments(gdf: gpd.GeoDataFrame, segments: gpd.GeoDataFrame, how: str) -> gpd.GeoDataFrame:

    check_dtype(par='how', obj=how, dtypes=str)
    how = how.lower()
    check_opt(par='how', opt=how, opts=['line', 'midpoint', 'dfb'])

    geometry_col = gdf.geometry.name
    crs = gdf.crs  # get CRS
    remove_cols(gdf, ['dfbsec_beg', 'segment_id'])  # remove columns, if present

    if how in ['line', 'midpoint']:
        id_pairs_list = []  # a list for pairs of IDs and segment IDs

        if all(gdf['datetime']) and all(segments['date']):  # if GeoDataFrame has datetimes and segments have dates
            for datapoint_id, datapoint_datetime, datapoint_point in (  # for each datapoint, its datetime, and its geometry
                    zip(gdf['datapoint_id'], gdf['datetime'], gdf['geometry'])):
                # determine which segments temporally overlap the datapoint (i.e., occur on the same date)
                segments['overlap'] = segments['date'].apply(
                    lambda d: 1 if d.strftime('%Y-%m-%d') == datapoint_datetime.strftime('%Y-%m-%d') else 0)
                # determine nearest overlapping segment
                if segments['overlap'].sum() == 0:  # if no segments temporally overlap...
                    print('\n\n____________________'  # ...raise warning
                          f'Warning: A datapoint (ID: {datapoint_id}) does not temporally overlap any segment.'
                          '\n____________________')
                elif segments['overlap'].sum() == 1:  # if 1 segment temporally overlaps...
                    id_pairs_list.append(  # ...it is the nearest so add it to the list
                        {'datapoint_id': datapoint_id,
                         'segment_id': segments['segment_id'].iloc[segments['overlap'].idxmax()]})
                else:  # if multiple segments temporally overlap...
                    if how == 'line':
                        id_pairs_list.append(  # ...add the nearest segment to the list
                            {'datapoint_id': datapoint_id,
                             'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                                 nearest_points(datapoint_point, segments[segments['overlap'] == 1].geometry)[1]).idxmin()]
                             })
                    elif how == 'midpoint':
                        id_pairs_list.append(  # ...add the nearest segment to the list
                            {'datapoint_id': datapoint_id,
                             'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                                 segments[segments['overlap'] == 1]['midpoint']).idxmin()]
                             })
        else:  # if one or both of the GeoDataFrame and segments do not contain datetimes or dates
            for datapoint_id, datapoint_point in (zip(gdf['datapoint_id'], gdf['geometry'])):  # for each datapoint and its geometry
                if how == 'line':
                    id_pairs_list.append(  # ...add the nearest segment to the list
                        {'datapoint_id': datapoint_id,
                         'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                             nearest_points(datapoint_point, segments.geometry)[1]).idxmin()]
                         })
                elif how == 'midpoint':
                    id_pairs_list.append(  # ...add the nearest segment to the list
                        {'datapoint_id': datapoint_id,
                         'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                             segments['midpoint']).idxmin()]
                         })

        id_pairs = pd.DataFrame(id_pairs_list)  # make DataFrame of ID pairs
        remove_cols(segments, 'overlap')  # clean up
        gdf = pd.merge(gdf, id_pairs, on='datapoint_id', how='left')  # merge pairs to datapoints

    elif how in ['dfb']:
        gdf = get_dfb(trackpoints=gdf, grouper=['section_id'], grouper_name='sec')
        gdf = pd.merge_asof(gdf.sort_values('dfbsec'),  # merge the trackpoints to the segments...
                            segments[['section_id', 'dfbsec_beg', 'segment_id']].sort_values('dfbsec_beg'),
                            left_on='dfbsec', right_on='dfbsec_beg', direction='backward',  # ...by DFBSEC...
                            by='section_id')  # ...provided within the same section
        gdf = gdf.sort_values(['section_id', 'dfbsec']).reset_index(drop=True)  # sort by section and DFBSEC
        gdf.drop(['dfbsec', 'dfbsec_beg'], axis=1, inplace=True)  # remove unnecessary

    gdf = gpd.GeoDataFrame(gdf, geometry=geometry_col, crs=crs)  # convert to GeoDataFrame
    return gdf


def samples_grid(cells: gpd.GeoDataFrame, periods: pd.DataFrame | str | None, datapoints: gpd.GeoDataFrame,
                 cols: dict, full: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:

    assigned = datapoints.copy()  # copy datapoints
    assigned = assign_cells(gdf=assigned, cells=cells)  # assign each datapoint its cell
    assigned = assign_periods(gdf=assigned, periods=periods)  # assign each datapoint its period

    check_dtype(par='cols', obj=cols, dtypes=dict)
    check_cols(df=assigned, cols=list(cols.keys()))
    try:  # group the datapoints into samples
        samples = assigned.copy().groupby(['cell_id', 'period_id']).agg(cols).reset_index()
    except AttributeError:
        raise AttributeError('\n\n____________________'
                             f'\nAttributeError: One or more functions in cols is invalid. '
                             '\nPlease check values in cols. '
                             'Options include: \'mean\', \'sum\', \'count\', and more.'
                             'Use help(Samples.grid) to see more options.',
                             '\n____________________')

    check_dtype(par='full', obj=full, dtypes=bool)
    if full:  # if full true, get all cell-period combos and merge them
        ids = [(cell, period) for cell in cells['cell_id'] for period in periods['period_id']]  # get all combos of IDs
        ids = pd.DataFrame({'cell_id': [i[0] for i in ids], 'period_id': [i[1] for i in ids]})  # make DataFrame
        samples = pd.merge(ids, samples, on=['cell_id', 'period_id'], how='left')  # merge to samples

    samples = pd.merge(periods, samples, on='period_id', how='right')  # add IDs and limits
    samples = pd.merge(cells, samples, on='cell_id', how='right')  # add IDs and limits
    return assigned, samples


def samples_segment(segments: gpd.GeoDataFrame, datapoints: gpd.GeoDataFrame,
                    cols: dict, how: str) -> tuple[pd.DataFrame, pd.DataFrame]:

    assigned = datapoints.copy()  # copy datapoints
    assigned = assign_segments(gdf=assigned, segments=segments, how=how)  # assign each datapoint its segment

    check_dtype(par='cols', obj=cols, dtypes=dict)
    check_cols(df=assigned, cols=list(cols.keys()))
    try:  # group the datapoints into samples
        samples = assigned.copy().groupby(['segment_id']).agg(cols).reset_index()
    except AttributeError:
        raise AttributeError('\n\n____________________'
                             f'\nAttributeError: One or more functions in cols is invalid. '
                             '\nPlease check values in cols. '
                             'Options include: \'mean\', \'sum\', \'count\', and more.'
                             'Use help(Samples.grid) to see more options.'
                             '\n____________________')
    samples = pd.merge(segments, samples, on='segment_id', how='left')  # add IDs and limits ('left' to get all)
    return assigned, samples


def samples_point(datapoints: gpd.GeoDataFrame, presences: gpd.GeoDataFrame, absences: gpd.GeoDataFrame,
                  cols: list[str], sections: gpd.GeoDataFrame = None) -> gpd.GeoDataFrame:

    check_dtype(par='cols', obj=cols, dtypes=list)
    check_cols(df=datapoints, cols=cols)
    cols.remove('datapoint_id') if 'datapoint_id' in cols else None  # remove 'datapoint_id' if in cols

    # datapoints to presences
    crs = presences.crs  # get presences CRS
    presences = pd.merge(presences,  # merge the presences...
                         datapoints[['datapoint_id'] + cols],  # ...to selected columns of datapoints...
                         how='left', on='datapoint_id')  # ...by matching their datapoint IDs
    presences = gpd.GeoDataFrame(presences, geometry='point', crs=crs)  # GeoDataFrame

    # datapoints to absences
    if sections is not None:  # if Sections provided
        sections_lines = sections.geometry.union_all()  # sections to single geometry
        absences['dfbsl'] = line_locate_point(sections_lines,  # DFBSL for each absence
                                              absences['point_al'] if 'point_al' in absences else absences['point'])
        datapoints = get_dfb(trackpoints=datapoints, grouper=None, grouper_name='sl')  # DFBSL for each datapoint

        crs = absences.crs  # get absences CRS
        absences = pd.merge_asof(absences.sort_values('dfbsl'),  # merge the thinned absences with datapoints by...
                                 datapoints[['dfbsl', 'datapoint_id'] + cols].sort_values('dfbsl'),
                                 on='dfbsl', direction='backward')  # ...the nearest DFBSLP going backwards as...
        # ...backwards merge selects nearest point PRIOR to the absence
        #   assumption: conditions at absence are those of most recently recorded point, i.e., conditions remain those
        #    of most recently recorded point till another point says otherwise
        absences = gpd.GeoDataFrame(absences, geometry='point', crs=crs)  # GeoDataFrame
        remove_cols(datapoints, 'dfbsl')  # remove DFBSL from datapoints
        remove_cols(absences, 'dfbsl')  # remove DFBSL from absences

    # concat presences and absences
    presences['p-a'] = 1  # set presence-absence value
    absences['p-a'] = 0  # set presence-absence value
    samples = pd.concat([presences, absences]).reset_index(drop=True)  # concat presences and absences
    samples = samples[['point_id', 'point', 'date', 'datapoint_id', 'p-a'] +  # reorder columns
                      [c for c in samples if c not in ['point_id', 'point', 'date', 'datapoint_id', 'p-a']]]
    samples = gpd.GeoDataFrame(samples, geometry='point', crs=datapoints.crs)  # GeoDataFrame
    return samples


def samples_grid_se(sections: gpd.GeoDataFrame, cells: gpd.GeoDataFrame, periods: pd.DataFrame | str | None,
                    length: bool = True, esw: int | float = None, euc_geo: str = 'euclidean', full: bool = False)\
        -> tuple[pd.DataFrame, pd.DataFrame]:

    check_dtype(par='length', obj=length, dtypes=bool)
    check_dtype(par='esw', obj=esw, dtypes=[int, float], none_allowed=True)
    check_dtype(par='euc_geo', obj=euc_geo, dtypes=str)
    euc_geo = euc_geo.lower()
    check_opt(par='euc_geo', opt=euc_geo, opts=['e', 'euclidean', 'g', 'geodesic', 'b', 'both'])

    cells_se = cells.copy()  # copy cells
    cells_se.set_index('cell_id', inplace=True)  # set cell IDs as index

    assigned = pd.DataFrame(columns=['section_id', 'datetime', 'period_id', 'cell_id'])  # skeleton assigned DataFrame
    samples = pd.DataFrame(columns=['cell_id', 'period_id'])  # skeleton survey effort DataFrame

    assigned_periods = assign_periods(gdf=sections.copy(), periods=periods)  # assign periods
    if length:  # if lengths...
        assigned_length = assigned_periods.copy()  # copy the sections with assigned periods
        assigned_length = assign_cells(gdf=assigned_length, cells=cells)  # assign cells
        assigned_length['subsection'] = (  # cut sections by cell to get subsections
            assigned_length.apply(lambda r: r['geometry'].intersection(cells_se.loc[r['cell_id']]['polygon']), axis=1))
        assigned_length.set_geometry('subsection', crs=assigned_length.crs, inplace=True)  # subsections as geometry
        assigned_length.drop('geometry', axis=1, inplace=True)  # remove full sections

        agg_dict = {}  # set empty aggregation dictionary
        if euc_geo in ['e', 'euclidean', 'b', 'both']:  # if Euclidean or both...
            assigned_length['se_length'] = assigned_length.length  # ...measure Euclidean lengths and add
            agg_dict['se_length'] = 'sum'  # add column to aggregation dictionary
        if euc_geo in ['g', 'geodesic', 'b', 'both']:  # if geodesic or both, measure geodesic lengths and add
            assigned_length['se_length_geo'] = [Geod(ellps='WGS84').geometry_length(subsection)
                                                for subsection in assigned_length.geometry.to_crs('EPSG:4326')]
            agg_dict['se_length_geo'] = 'sum'  # add column to aggregation dictionary

        assigned = pd.merge(assigned,  # merge assigned skeleton to...
                            assigned_length,  # ...length measurements
                            on=['section_id', 'datetime', 'period_id', 'cell_id'], how='outer')
        samples_length = (assigned_length.copy().groupby(['cell_id', 'period_id']).  # group by cell-period...
                          agg(agg_dict).reset_index())  # ...and sum measurements
        samples = pd.merge(samples,  # merge samples skeleton...
                           samples_length,  # ...to length samples
                           on=['cell_id', 'period_id'], how='outer')

    if esw:  # if ESW...
        assigned_area = assigned_periods.copy()  # copy the sections with assigned periods
        assigned_area.geometry = assigned_area.buffer(esw, cap_style='flat')  # buffer the track to the ESW
        assigned_area = assign_cells(gdf=assigned_area, cells=cells)  # assign cells
        assigned_area['subsection_area'] = (  # cut sections by cell to get subsections
            assigned_area.apply(lambda r: r['geometry'].intersection(cells_se.loc[r['cell_id']]['polygon']), axis=1))
        assigned_area.set_geometry('subsection_area', crs=assigned_area.crs, inplace=True)  # subsections as geometry
        assigned_area.drop('geometry', axis=1, inplace=True)  # remove full sections

        agg_dict = {}  # set empty aggregation dictionary
        if euc_geo in ['e', 'euclidean', 'b', 'both']:  # if Euclidean or both...
            assigned_area['se_area'] = assigned_area.area  # ...measure Euclidean lengths and add
            agg_dict['se_area'] = 'sum'  # add column to aggregation dictionary
        if euc_geo in ['g', 'geodesic', 'b', 'both']:  # if geodesic or both, measure geodesic areas and add
            assigned_area['se_area_geo'] = [abs(Geod(ellps='WGS84').geometry_area_perimeter(subsection_area)[0])
                                            for subsection_area in assigned_area.geometry.to_crs('EPSG:4326')]
            agg_dict['se_area_geo'] = 'sum'  # add column to aggregation dictionary

        assigned = pd.merge(assigned,  # merge assigned skeleton to...
                            assigned_area,  # ...area measurements
                            on=['section_id', 'datetime', 'period_id', 'cell_id'], how='outer')
        samples_area = (assigned_area.copy().groupby(['cell_id', 'period_id']).  # group by cell-period...
                          agg(agg_dict).reset_index())  # ...and sum measurements
        samples = pd.merge(samples,  # merge samples skeleton...
                           samples_area,  # ...to area samples
                           on=['cell_id', 'period_id'], how='outer')

    check_dtype(par='full', obj=full, dtypes=bool)
    if full:  # if full true, get all cell-period combos and merge them
        ids = [(cell, period) for cell in cells['cell_id'] for period in periods['period_id']]  # get all combos of IDs
        ids = pd.DataFrame({'cell_id': [i[0] for i in ids], 'period_id': [i[1] for i in ids]})  # make DataFrame
        samples = pd.merge(ids, samples, on=['cell_id', 'period_id'], how='left')  # merge to samples

    samples = pd.merge(periods, samples, on='period_id', how='right')  # add IDs and limits
    samples = pd.merge(cells, samples, on='cell_id', how='right')  # add IDs and limits
    return assigned, samples


def samples_segment_se(segments: gpd.GeoDataFrame, length: bool = True, esw: int | float = None,
                       audf: int | float = None, euc_geo: str = 'euclidean') -> pd.DataFrame:

    check_dtype(par='length', obj=length, dtypes=bool)
    check_dtype(par='esw', obj=esw, dtypes=[int, float], none_allowed=True)
    check_dtype(par='audf', obj=audf, dtypes=[int, float], none_allowed=True)
    check_dtype(par='euc_geo', obj=euc_geo, dtypes=str)
    euc_geo = euc_geo.lower()
    check_opt(par='euc_geo', opt=euc_geo, opts=['e', 'euclidean', 'g', 'geodesic', 'b', 'both'])

    samples = segments.copy()  # copy segments GeoDataFrame

    if euc_geo in ['e', 'euclidean', 'b', 'both']:  # if Euclidean or both...
        lengths = np.array(samples.length)  # ...measure lengths as Euclidean distances
        if length:  # if lengths...
            samples['se_length'] = lengths  # ...add lengths
        if esw:  # if ESW...
            samples['se_area'] = lengths * esw * 2  # ...calculate and add area
        if audf:  # if AUDF...
            samples['se_effective'] = lengths * audf * 2  # ...calculate and add effective area
    if euc_geo in ['g', 'geodesic', 'b', 'both']:  # if geodesic or both...
        lengths_geo = np.array([Geod(ellps='WGS84').geometry_length(segment) for segment in samples.geometry.to_crs('EPSG:4326')])  # ...measure lengths as geodesic distances
        if length:  # if lengths...
            samples['se_length_geo'] = lengths_geo  # ...add lengths
        if esw:  # if ESW...
            samples['se_area_geo'] = lengths_geo * esw * 2  # ...calculate and add area
        if audf:  # if AUDF...
            samples['se_effective_geo'] = lengths_geo * audf * 2  # ...calculate and add effective area

    return samples


def samples_merge(approach: str, **kwargs: pd.DataFrame):

    check_dtype(par='approach', obj=approach, dtypes=str)
    approach = approach.lower()
    check_opt(par='approach', opt=approach, opts=['g', 'grid', 's', 'segment'])

    if approach in ['g', 'grid']:  # grid approach
        merger = ['cell_id', 'polygon', 'centroid',  # merge on cell details and...
                  'period_id', 'datetime_beg', 'datetime_mid', 'datetime_end']  # ...period details
    elif approach in ['s', 'segment']:  # segment approach
        merger = ['segment_id', 'line', 'midpoint', 'date',  # merge on segment details
                  'section_id', 'dfbsec_beg', 'dfbsec_end']
    else:  # unknown approach (should never be reached given check_opt() above)
        raise ValueError

    # rename columns (if necessary)
    cols = []  # empty list for all cols
    for samples in kwargs.values():  # for each samples...
        cols += [col for col in samples if col not in merger]  # ...add cols that are not in merger
    cols = [k for k, v in Counter(cols).items() if v > 1]  # keep only cols that are present in multiple samples
    if len(cols) > 0:
        print(f'Warning: multiple samples contain one or more columns with the same name. '
              f'These columns will be renamed as follows:')
        for name, samples in kwargs.items():  # for each samples and its name
            renamer = {col: col + '_' + name for col in cols if col in samples}  # get cols to be renamed
            if len(renamer) > 0:  # if there are cols to be renamed...
                samples.rename(columns=renamer, inplace=True)  # ...rename them and...
                print(f'  In samples \'{name}\':'  # ...print message
                      f'\n    \'{'\n    \''.join([k + '\' to \'' + v + '\'' for k, v in renamer.items()])}')

    merged = reduce(lambda left, right: pd.merge(left, right, on=merger, how='outer'), kwargs.values())  # merge all
    return merged


##############################################################################################################
# Stage 3: Output
def extract(samples: gpd.GeoDataFrame) -> gpd.GeoDataFrame:

    if samples.crs.axis_info[0].unit_name == 'degree':
        suffix_x, suffix_y = '_lon', '_lat'
    else:
        suffix_x, suffix_y = '_x', '_y'

    for geometry in ['centroid', 'midpoint', 'point']:
        if geometry in samples:  # if it is in samples
            remove_cols(samples, [geometry + '_lon', geometry + '_lat', geometry + '_x', geometry + '_y'])
            index = samples.columns.get_loc(geometry)
            samples.insert(index + 1, geometry + suffix_y, samples[geometry].y)  # extract the y coords
            samples.insert(index + 1, geometry + suffix_x, samples[geometry].x)  # extract the x coords
    return samples


##############################################################################################################
# Plots
# zorders: 0 - unassigned; 1, 2 - polygons; 3, 4 - lines; 5, 6 - points
def datapoints_plot(ax, datapoints):
    datapoints.plot(ax=ax, marker='o', markersize=10, facecolor='#2e2e2e', linewidth=0.25, edgecolor='#ffffff', zorder=5)


def sections_plot(ax, sections):
    colours = (['#969696', '#787878'] * int(np.ceil(len(sections) / 2)))[:len(sections)]
    sections.plot(ax=ax, linewidth=7.5, color=colours, alpha=0.75, zorder=3)


def cells_colours(cells):
    n_cols = int((cells.total_bounds[2] - cells.total_bounds[0]) /
                 (cells.geometry.iloc[0].bounds[2] - cells.geometry.iloc[0].bounds[0]) + 0.25)
    colours_odd = (['#a30046', '#0055a3', '#fdbe57', '#d4bab8'] * int(np.ceil(n_cols / 4)))[:n_cols]
    colours_even = (['#fdbe57', '#d4bab8', '#a30046', '#0055a3'] * int(np.ceil(n_cols / 4)))[:n_cols]
    colours = pd.DataFrame({
        'cell_id': cells['cell_id'],
        'colours': ((colours_odd + colours_even) * int(np.ceil((len(cells) / n_cols / 2))))[:len(cells)]})
    return colours


def cells_plot(ax, cells):
    colours = cells_colours(cells)
    cells.plot(ax=ax, facecolor=colours['colours'], alpha=0.2, zorder=2)


def segments_colours(segments):
    colours = pd.DataFrame({
        'segment_id': segments['segment_id'],
        'colours': (['#a30046', '#0055a3', '#fdbe57'] * int(np.ceil(len(segments) / 3)))[:len(segments)]})
    return colours


def segments_plot(ax, segments):
    colours = segments_colours(segments)
    segments.plot(ax=ax, linewidth=5, color=colours['colours'], alpha=0.75, zorder=4)


def presences_plot(ax, points, buffer=None):
    points.plot(ax=ax, marker='+', markersize=50, color='#0055a3', zorder=5)
    points.buffer(buffer).plot(ax=ax, color='#0055a3', alpha=0.2, zorder=2) if buffer else None


def presences_removed_plot(ax, points, buffer=None):
    points.plot(ax=ax, marker='+', markersize=50, color='#fdbe57', zorder=5)
    points.buffer(buffer).plot(ax=ax, color='#fdbe57', alpha=0.2, zorder=2) if buffer else None


def absences_plot(ax, points, buffer=None):
    points.plot(ax=ax, marker='o', markersize=25, facecolor='none', edgecolor='#a30046', zorder=5)
    points.buffer(buffer).plot(ax=ax, color='#a30046', alpha=0.2, zorder=2) if buffer else None


def absences_removed_plot(ax, points, buffer=None):
    points.plot(ax=ax, marker='o', markersize=25, facecolor='none', edgecolor='#fdbe57', zorder=5)
    points.buffer(buffer).plot(ax=ax, color='#fdbe57', alpha=0.2, zorder=2) if buffer else None


def absencelines_plot(ax, lines):
    lines.plot(ax=ax, linewidth=2.5, color='#a30046', alpha=0.75, zorder=4)


def assigned_plot_cells_datapoints(ax, assigned, cells):
    colours = cells_colours(cells)
    cells.plot(ax=ax, facecolor=colours['colours'], alpha=0.2, zorder=2)
    assigned_colours = pd.merge(assigned.copy(), colours, on='cell_id', how='left')
    assigned_colours = gpd.GeoDataFrame(assigned_colours, geometry='geometry', crs=assigned.crs)
    assigned_colours.plot(ax=ax, markersize=10, color=assigned_colours['colours'], zorder=5)


def assigned_plot_cells_effort(ax, assigned, cells):
    colours = cells_colours(cells)
    assigned_colours = pd.merge(assigned.copy(), colours, on='cell_id', how='left')
    cells.plot(ax=ax, facecolor=colours['colours'], alpha=0.2, zorder=2)
    if 'subsection' in assigned_colours:
        subsections = assigned_colours.copy().dropna(subset='subsection')
        gpd.GeoSeries(subsections['subsection']).plot(ax=ax, linewidth=2.5, color=subsections['colours'], alpha=0.75, zorder=5)
    if 'subsection_area' in assigned_colours:
        subsection_areas = assigned_colours.copy().dropna(subset='subsection_area')
        gpd.GeoSeries(subsection_areas['subsection_area']).plot(ax=ax, color=subsection_areas['colours'], alpha=0.5, zorder=5)


def assigned_plot_segments_datapoints(ax, assigned, segments):
    colours = segments_colours(segments)
    segments.plot(ax=ax, linewidth=5, color=colours['colours'], alpha=0.2, zorder=4)
    assigned_colours = pd.merge(assigned.copy(), colours, on='segment_id', how='left')
    assigned_colours = gpd.GeoDataFrame(assigned_colours, geometry='geometry', crs=assigned.crs)
    assigned_colours.plot(ax=ax, markersize=10, facecolor=assigned_colours['colours'], edgecolor='#ffffff', linewidth=0.5, zorder=5)

