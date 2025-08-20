# Core functions for sampling

##############################################################################################################
# Imports
from collections import Counter
from datetime import timedelta
from functools import reduce
import math
import numpy as np
from pyproj import Geod
import random
from shapely import Point, MultiPoint, LineString, MultiLineString, Polygon
from shapely.errors import GEOSException
from shapely.ops import substring, nearest_points
import typing

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

    """Make a GeoDataFrame containing datapoints from a GPKG, SHP, CSV, or XLSX file.

    Takes as input a GPKG, SHP, CSV, or XLSX file that contains the datapoints and reformats it for subsequent
     processing by: renaming and reordering essential columns; if necessary, reprojecting it to a projected CRS;
     assigning each datapoint a unique ID.
    If loading data from a CSV or XLSX, locations of datapoints must be stored in one of two ways:
      two columns (x_col and y_col) containing x and y (e.g., longitude and latitude) coordinates
      one column (geometry_col) containing points as WKT geometry objects

    Parameters:
        filepath : str
            The path to the file containing the datapoints. Ensure that filepath includes the filename and the extension.
        x_col : str, optional, default 'lon'
            If inputting a CSV or XLSX with x and y coordinates, the name of the column containing the x coordinate
             (e.g., longitude) of each datapoint.
        y_col : str, optional, default 'lat'
            If inputting a CSV or XLSX with x and y coordinates, the name of the column containing the y coordinate
             (e.g., latitude) of each datapoint.
        geometry_col : str, optional, default None
            If inputting a CSV or XLSX with points as WKT geometry objects, the name of the column containing the WKT
             geometry objects.
        crs_input : str | int | pyproj.CRS, optional, default None
            If inputting a CSV or XLSX, the CRS of the coordinates/geometries. The CRS must be either: a pyproj.CRS; a
             string in a format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format
             accepted by pyproj.CRS.from_user_input (e.g., 4326).
        crs_working : str | int | pyproj.CRS, optional, default None
            The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that, preferably,
             preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a format accepted by
             pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted by
             pyproj.CRS.from_user_input (e.g., 4326).
        datetime_col : str, optional, default None
            If applicable, the name of the column containing the datetime or date of each datapoint.
        datetime_format : str, optional, default None
            Optionally, the format of the datetimes as a string (e.g., "%Y-%m-%d %H:%M:%S"). 
            It is possible to use format="ISO8601" if the datetimes meet ISO8601 (units in greatest to least order, 
             e.g., YYYY-MM-DD) or format="mixed" if the datetimes have different formats (although not recommended as 
             slow and risky).
        tz_input : str | timezone | pytz.BaseTzInfo, optional, default None
            If datetime_col is specified, the timezone of the datetimes contained within the column. The timezone must
             be either: a datetime.timezone; a string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a
             timezone name accepted by pytz (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’).
        tz_working : str | timezone | pytz.BaseTzInfo, optional, default None
            The timezone to be used for the subsequent processing. The timezone must be either: a datetime.timezone; a
             string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a timezone name accepted by pytz
             (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’). Note that tz_input must be specified if tz_working is
             specified.
        datapoint_id_col : str, optional, default None
            If applicable, the name of the column containing the datapoint IDs. The datapoint IDs must be unique.
        section_id_col : str, optional, default None
            If subsequently using Sections.from_datapoints, the name of the column containing the section IDs. Each
             individual section must have its own unique ID. All the datapoints that make up a given section must have
             the same value for section ID so that, when Sections.from_datapoints is run, they are grouped together to
             form a LineString. It is recommended that section IDs be codes consisting of letters and numbers and,
             optionally, underscores (e.g., ‘s001‘ or 20250710_s01‘).

    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing datapoints.
    """

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
            datapoints = parse_xy(df=datapoints, x_col=x_col, y_col=y_col, crs=crs_input)  # convert to geopandas GeoDataFrame
        elif geometry_col is not None:  # else if geometry column is specified
            check_dtype(par='geometry_col', obj=geometry_col, dtypes=str, none_allowed=True)
            check_cols(df=datapoints, cols=geometry_col)
            datapoints = parse_geoms(df=datapoints, geometry_col=geometry_col, crs=crs_input)  # convert to geopandas GeoDataFrame

    gtypes = list(set([type(geometry) for geometry in datapoints.geometry]))  # get geometry types
    if len(gtypes) == 1 and gtypes[0] == Point:  # if there is one type: Point
        pass
    elif ((len(gtypes) == 1 and gtypes[0] == MultiPoint) or  # else if there is one type: MultiPoint...
          (len(gtypes) == 2 and Point in gtypes and MultiPoint in gtypes)):  # ...or two types: MultiPoint and Point...
        print('Note: some or all geometries are MultiPoints and will be exploded to Points.')
        datapoints = datapoints.explode()  # explode MultiPoints to Points
    else:  # else if there are other types, print error message...
        raise TypeError(f'geometries are not Points or MultiPoints. \nGeometry types include {", ".join(gtypes)}.')

    if crs_working is not None:  # if a working CRS is provided
        check_crs(par='crs_working', crs=crs_working)
        datapoints = reproject_crs(gdf=datapoints, crs_target=crs_working)  # reproject to CRS working

    check_projected(obj_name='datapoints', crs=datapoints.crs)  # check that the CRS is projected

    # temporal
    if datetime_col is not None:  # if datetime column specified
        check_dtype(par='datetime_col', obj=datetime_col, dtypes=str)
        check_cols(df=datapoints, cols=datetime_col)
        check_dtype(par='datetime_format', obj=datetime_format, dtypes=str, none_allowed=True)
        check_tz(par='tz_input', tz=tz_input, none_allowed=True)
        parse_dts(df=datapoints, datetime_col=datetime_col, datetime_format=datetime_format, tz=tz_input)  # parse datetimes and set TZ
        if tz_working is not None:  # if a working timezone is specified
            check_tz(par='tz_working', tz=tz_working)
            datapoints = convert_tz(df=datapoints, datetime_cols=datetime_col, tz_target=tz_working)  # convert to working TZ
        if datetime_col != 'datetime':  # if datetime column not already called 'datetime'...
            datapoints['datetime'] = datapoints[datetime_col]  # ...rename datetime column
            print(f'Note: column "{datetime_col}" renamed to "datetime".')
    else:  # else if no datetime column specified...
        datapoints['datetime'] = None  # ...make dummy column with None

    if section_id_col is not None:  # if a section ID column is specified
        check_dtype(par='section_id_col', obj=section_id_col, dtypes=str)
        check_cols(df=datapoints, cols=section_id_col)
        if section_id_col != 'section_id':  # if section ID column not called 'section_id'...
            datapoints.rename(columns={section_id_col: 'section_id'}, inplace=True)  # ...rename it
            print(f'Note: column "{section_id_col}" renamed to "section_id".')
        key_cols = ['datapoint_id', 'section_id', 'geometry', 'datetime']
    else:
        key_cols = ['datapoint_id', 'geometry', 'datetime']

    if datapoint_id_col is not None:  # if a datapoint ID column is specified
        check_dtype(par='datapoint_id_col', obj=datapoint_id_col, dtypes=str)
        check_cols(df=datapoints, cols=datapoint_id_col)
        if datapoints[datapoint_id_col].nunique() < len(datapoints[datapoint_id_col]):  # check that all IDs are unique
            raise Exception('\n\n____________________'
                            '\nError: two or more datapoints have the same datapoint ID.'
                            f'\nPlease ensure that all values in "{datapoint_id_col}" are unique.'
                            '\nAlternatively, leave "datapoint_id_col" unspecified and datapoint IDs will be'
                            'generated automatically.'
                            '\n____________________')
        if datapoint_id_col != 'datapoint_id':  # if datapoint ID column not called 'datapoint_id'...
            datapoints.rename(columns={datapoint_id_col: 'datapoint_id'}, inplace=True)  # ...rename it
            print(f'Note: column "{datapoint_id_col}" renamed to "datapoint_id".')
    else:  # else if datapoint ID column is not specified
        datapoints['datapoint_id'] = ['d' + str(i).zfill(len(str(len(datapoints))))  # make datapoint IDs
                                      for i in range(1, len(datapoints) + 1)]
        print('Success: datapoint IDs generated.')

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

    """Make a GeoDataFrame containing sections from a GPKG or SHP file.

    Takes as input a GPKG or SHP file that contains the sections as shapely.LineStrings and reformats it for subsequent
     processing by: renaming and reordering essential columns; if necessary, reprojecting it to a projected CRS;
     assigning each section a unique ID.
    Sections can be made from CSV or XLSX files containing series of points by first making a DataPoints object and then
     using Sections.from_datapoints to make a Sections object.

    Parameters:
        filepath : str
            The path to the file containing the sections. Ensure that filepath includes the filename and the extension.
        crs_working : str | int | pyproj.CRS, optional, default None
            The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that, preferably,
             preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a format accepted by
             pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted by
             pyproj.CRS.from_user_input (e.g., 4326).
        datetime_col : str, optional, default None
            The name of the column containing the datetime of each section.
        datetime_format : str, optional, default None
            Optionally, the format of the datetimes as a string (e.g., "%Y-%m-%d %H:%M:%S").
            It is possible to use format="ISO8601" if the datetimes meet ISO8601 (units in greatest to least order,
             e.g., YYYY-MM-DD) or format="mixed" if the datetimes have different formats (although not recommended as
             slow and risky).
        tz_input : str | timezone | pytz.BaseTzInfo, optional, default None
            If datetime_col is specified, the timezone of the datetimes contained within the column. The timezone must
             be either: a datetime.timezone; a string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a
             timezone name accepted by pytz (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’).
        tz_working : str | timezone | pytz.BaseTzInfo, optional, default None
            The timezone to be used for the subsequent processing. The timezone must be either: a datetime.timezone; a
             string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a timezone name accepted by pytz
             (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’). Note that tz_input must be specified if tz_working is
             specified.
        section_id_col : str, optional, default None
            Optionally, the name of the column containing the section IDs. Each individual section must have its own
             unique ID. It is recommended that section IDs be codes consisting of letters and numbers and, optionally,
             underscores (e.g., ‘s001‘ or 20250710_s01‘).
    Returns:
        Sections
            Returns a GeoDataFrame containing sections.
    """
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
                        f'\nGeometry types include {", ".join(gtypes)}.'
                        '\nTo make sections from Points, first input the Points as DataPoints and then'
                        ' use Sections.from_datapoints() to make Sections from the DataPoints.')

    if crs_working is not None:  # if a working CRS is provided
        check_crs(par='crs_working', crs=crs_working)
        sections = reproject_crs(gdf=sections, crs_target=crs_working)  # reproject to CRS working

    check_projected(obj_name='sections', crs=sections.crs)  # check that the CRS is projected

    # temporal
    if datetime_col is not None:  # if datetime column specified
        check_dtype(par='datetime_col', obj=datetime_col, dtypes=str)
        check_cols(df=sections, cols=datetime_col)
        check_dtype(par='datetime_format', obj=datetime_format, dtypes=str, none_allowed=True)
        check_tz(par='tz_input', tz=tz_input, none_allowed=True)
        parse_dts(df=sections, datetime_col=datetime_col, datetime_format=datetime_format, tz=tz_input)  # parse datetimes and set TZ
        if tz_working is not None:  # if a working timezone is specified
            check_tz(par='tz_working', tz=tz_working)
            sections = convert_tz(df=sections, datetime_cols=datetime_col, tz_target=tz_working)  # convert to working TZ
        if datetime_col != 'datetime':  # if datetime column not already called 'datetime'...
            sections.rename(columns={datetime_col: 'datetime'}, inplace=True)  # ...rename datetime column
            print(f'Note: column "{datetime_col}" renamed to "datetime".')
    else:  # else if no datetime column specified...
        sections['datetime'] = None  # ...make dummy column with None

    if section_id_col is not None:  # if a section ID column is specified
        check_dtype(par='section_id_col', obj=section_id_col, dtypes=str)
        check_cols(df=sections, cols=section_id_col)
        if sections[section_id_col].nunique() < len(sections[section_id_col]):  # check that all IDs are unique
            raise Exception('\n\n____________________'
                            '\nError: two or more sections have the same section ID.'
                            f'\nPlease ensure that all values in "{section_id_col}" are unique.'
                            '\nAlternatively, leave "section_id_col" unspecified and unique section IDs will be'
                            'generated automatically.'
                            '\n____________________')
        if section_id_col != 'section_id':  # if section ID column not called 'section_id'...
            sections.rename(columns={section_id_col: 'section_id'}, inplace=True)  # ...rename it
            print(f'Note: column "{section_id_col}" renamed to "section_id".')
    else:  # else if section ID column is not specified
        sections['section_id'] = ['s' + str(i).zfill(len(str(len(sections))))  # make section IDs
                                  for i in range(1, len(sections) + 1)]
        print('Success: section IDs generated.')

    sections = sections[['section_id', 'geometry', 'datetime'] +  # reorder columns
                        [c for c in sections if c not in ['section_id', 'geometry', 'datetime']]]
    return sections


def sections_from_datapoints(
        datapoints: gpd.GeoDataFrame,
        cols: dict = None,
        sortby: str | list[str] = None,
        section_id_col: str = 'section_id'):

    """Make a GeoDataFrame containing sections from a GeoDataFrame containing datapoints.

    Takes as input a GeoDataFrame that contains sections as continuous series of Points and reformats it for
     subsequent processing by: converting each series of Points to a LineString; renaming and reordering essential
     columns. The CRS and timezone will be that of the datapoints GeoDataFrame.
    Note: should only be used with continuous datapoints and not with sporadic datapoints.

    Parameters:
        datapoints : GeoDataFrame
            The GeoDataFrame that contains sections as series of points.
        cols : dict | None, optional, default None
            A dictionary whose keys are the names of any columns to keep and whose values are corresponding functions
             specifying what to do with those columns. For example, if each section has a pre-set period in a column
             called 'season', cols could be specified as {'season': 'first'} to keep the first value of season for each
             section.
        sortby : str | list, optional, default None
            When converting each series of Points to a LineString, the Points are joined one to the next (like a
             dot-to-dot). If the Points are not in the right order, the resulting LineString will be incorrect. If
             sortby is not specified, the Points will be joined in the order that they are in. To change this order,
             specify sortby as the name of a column or columns (e.g., 'datetime') to sort the datapoints by before the
             Points are converted to LineStrings.
        section_id_col : str, optional, default 'section_id'
            The name of the column containing the section IDs. Each individual section must have its own unique ID. It
             is recommended that section IDs be codes consisting of letters and numbers and, optionally, underscores
             (e.g., ‘s001‘ or 20250710_s01‘).

    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing sections.
    """

    sections = datapoints.copy()  # copy datapoints GeoDataFrame

    check_dtype(par='section_id_col', obj=section_id_col, dtypes=str)
    check_cols(df=sections, cols=section_id_col)

    if sortby is not None:  # if there is column to sort by
        check_dtype(par='sortby', obj=sortby, dtypes=[str, list])
        check_cols(df=sections, cols=sortby)
        sortby = sortby if isinstance(sortby, list) else [sortby] if isinstance(sortby, str) else None  # sortby to list
        sortby = ['section_id'] + [col for col in sortby if col != 'section_id']  # add 'section_id' to sortby list
        sections.sort_values(sortby, inplace=True)  # sort by sortby list

    if cols is not None:  # if aggregation dict provided
        check_dtype(par='agg_dict', obj=cols, dtypes=dict)
        check_cols(df=sections, cols=list(cols.keys()))
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

    """Delimit temporal periods of a set number of units.

    From a given extent, number of units, and type of units, delimit temporal periods of regular length, e.g.,
     8 days, 2 months, or 1 year.
    Temporal periods of irregular length (e.g., seasons) should be predefined and contained within a column of the
     input data.

    Parameters:
        extent : pandas.DataFrame | tuple[list, str]
            An object detailing the temporal extent over which the periods will be limited. Must be one of:
                a pandas.DataFrame that has a 'datetime' column
                a tuple containing two elements: a list of two datetimes and a timezone as a string (or None if no
                 timezone is to be used)
        num : int | float
            The number of temporal units.
        unit : str
            The temporal units assigned with one of the following strings:
                'day': days ('d' also accepted)
                'month': months ('m' also accepted)
                'year': years ('y' also accepted)
        datetime_col : str, optional, default 'datetime'
            If extent is a DataFrame, the name of the column containing the datetimes.

    Returns:
        DataFrame
            Returns a DataFrame containing the periods.
    """

    check_dtype(par='extent', obj=extent, dtypes=[pd.DataFrame, tuple])
    check_dtype(par='num', obj=num, dtypes=[int, float])
    check_dtype(par='unit', obj=unit, dtypes=str)
    unit = unit.lower()
    check_opt(par='unit', opt=unit, opts=['day', 'd', 'month', 'm', 'year', 'y'])

    if isinstance(extent, tuple):  # if extent is a tuple...
        tz = extent[1]  # get timezone
        check_tz(par='extent timezone', tz=tz, none_allowed=True)
        extent = pd.DataFrame({'datetime': extent[0]})  # make DataFrame from extent list
        parse_dts(df=extent, datetime_col='datetime', tz=tz)  # parse datetimes
        datetime_col = 'datetime'  # set datetime column
    elif isinstance(extent, pd.DataFrame):  # if extent is a DataFrame
        check_dtype(par='datetime_col', obj=datetime_col, dtypes=str)
        check_cols(df=extent, cols=datetime_col)
        try:
            tz = str(extent[datetime_col].dtype.tz)  # get timezone if there is one
        except AttributeError:  # else, if there is no timezone...
            tz = None
    else:  # else unrecognised datatype (should never be reached)
        extent = None
        tz = None

    # get the begin date
    timecodes = {'d': 'd', 'm': 'MS', 'y': 'YS'}  # set time period codes
    timecode = str(int(num)) + timecodes[unit[0]]  # make time code for grouper by combining number and unit
    periods = extent.groupby(pd.Grouper(key=datetime_col, freq=timecode)).first().reset_index()  # group
    periods.rename(columns={datetime_col: 'date_beg'}, inplace=True)  # rename column

    # get the end date (different for days, months, and years)
    if unit in ['d', 'day']:  # days: add the number of days to the begin date and subtract 1 sec
        periods['date_end'] = periods['date_beg'].apply(lambda d: d + timedelta(days=num, seconds=-1))
    elif unit in ['m', 'month']:  # months: add years and months based on number of months and subtract 1 sec
        periods['date_end'] = periods['date_beg'].apply(lambda d: datetime(
            d.year + (d.month + num) // 12 if (d.month + num) % 12 != 0 else d.year + (d.month + num) // 12 - 1,
            (d.month + num) % 12 if (d.month + num) % 12 != 0 else 12,
            d.day) - timedelta(seconds=1))
        periods['date_end'] = periods['date_end'].dt.tz_localize(tz) if tz is not None else periods['date_end']  # set TZ
    elif unit in ['y', 'year']:  # years: add the number of years to the begin date and subtract 1 sec
        periods['date_end'] = periods['date_beg'].apply(lambda d: datetime(
            d.year + num, d.month, d.day) - timedelta(seconds=1))
        periods['date_end'] = periods['date_end'].dt.tz_localize(tz) if tz is not None else periods['date_end']  # set TZ

    periods['date_mid'] = periods.apply(  # get mid date by adding difference to begin date, floor to secs
        lambda r: (r['date_beg'] + (r['date_end'] - r['date_beg']) / 2).ceil('s'), axis=1)
    periods['period_id'] = periods['date_beg'].apply(  # make period IDs
        lambda d: 'p' + str(d)[:10] + '-' + str(int(num)) + unit[0])

    for col in ['date_beg', 'date_mid', 'date_end']:  # for each date col, remove hours, minutes, and seconds
        periods[col] = periods[col].apply(lambda dt: dt.replace(hour=0, minute=0, second=0))

    periods = periods[['period_id', 'date_beg', 'date_mid', 'date_end']]  # keep only necessary columns
    return periods


def cells_delimit(
        extent: gpd.GeoDataFrame | tuple[list, str | int | pyproj.crs.crs.CRS],
        var: str,
        side: int | float,
        buffer: int | float = None)\
        -> gpd.GeoDataFrame:

    """Delimit grid cells.

    From a given extent, variation, and side length, delimit rectangular or hexagonal grid cells of a regular size.

    Parameters:
        extent : geopandas.GeoDataFrame | tuple[list, str]
            An object detailing the spatial extent over which the periods will be limited. Must be one of:
                a geopandas.GeoDataFrame
                a tuple containing two elements: a list containing the x min, y min, x max, and y max and a CRS
        var : {'rectangular', 'hexagonal'}
            The variation used to generate the cells. Must be one of the following:
                'rectangular': make rectangular (square) cells ('r' also accepted)
                'hexagonal': make hexagonal cells ('h' also accepted)
        side : int | float
            The side length of the rectangles/hexagons in the units of the CRS.
        buffer : int | float, optional, default 0
            The width of a buffer to be created around the extent to enlarge it and ensure that all the surveyed
             area is covered by the cells.
    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the cells.
    """

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

    """Delimit segments.

    With a given variation and target length, cut sections into segments.
    Segments can be made with any one of three variations: the simple, joining, and redistribution variations. For
     all three variations, a target length is set. The variations differ in how they deal with the remainder — the
     length inevitably left over after dividing a section by the target length. Additionally, for the simple and
     joining variations, the location of the remainder / joined segment can be randomised (rather than always being
     at the end).

    Parameters:
    sections : GeoDataFrame
        The GeoDataFrame containing the sections from which the segments will be cut.
    var : {'simple', 'joining', 'redistribution'}
        The variation to use to make the segments. Must be one of the following:
            'simple': the remainder is left as an independent segment ('s' also accepted)
            'joining': the remainder, if under half the target length, is joined to another segment, otherwise it is
             left as an independent segment ('j' also accepted)
            'redistribution': the length of the remainder is redistributed among all segments ('r' also accepted)
    target : int | float
        The target length of the segments in the units of the CRS.
    rand : bool, optional, default False
        If using the simple or joining variations, whether to randomise the location of the remainder / joined
         segment or not.

    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the segments.
    """

    check_dtype(par='sections', obj=sections, dtypes=gpd.GeoDataFrame)
    check_projected(obj_name='sections', crs=sections.crs)
    check_cols(df=sections, cols=['datetime', 'section_id'])
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


def segments_datetimes(segments: gpd.GeoDataFrame, datapoints: gpd.GeoDataFrame) -> gpd.GeoDataFrame:

    """Get datetimes for the beginning, middle, and end of each segment.

    Get a datetime value for the beginning, middle, and end of each segment. This is only applicable to segments
     that were made from sections that were made from continuous datapoints.
    Additionally, it requires that those datapoints have datetime values.
    In the (likely) case that a segment begins/ends at some point between two datapoints, the begin/end time for
     that segment will be interpolated based on the distance from those two datapoints to the point at which the
     segment begins/ends assuming a constant speed.

    Parameters:
        segments : GeoDataFrame
            The GeoDataFrame containing the segments.
        datapoints : GeoDataFrame
            The GeoDataFrame, containing datetimes, that was used to make the sections that were used
             to make the segments.
    """

    # trackpoints
    trackpoints = datapoints.copy()  # copy datapoints to avoid modifying
    trackpoints = get_dfb(trackpoints=trackpoints, grouper=['section_id'], grouper_name='sec')  # get DFBSECs

    # get the begin datetime of each segment
    segments = pd.merge_asof(
        segments.sort_values('dfbsec_beg'),  # get datetime of last datapoint (x) before segment begins by...
        trackpoints[['section_id', 'dfbsec', 'datetime']].sort_values('dfbsec'),  # ...merging to datapoints...
        left_on='dfbsec_beg', right_on='dfbsec', direction='backward',  # ...by DFBSEC(beg), direction BACKWARD...
        by='section_id')  # ...provided within the same section
    segments = pd.merge_asof(
        segments.sort_values('dfbsec_beg'),  # get datetime of first datapoint (y) after segment begins by...
        trackpoints[['section_id', 'dfbsec', 'datetime']].sort_values('dfbsec'),  # ...merging to datapoints...
        left_on='dfbsec_beg', right_on='dfbsec', direction='forward',  # ...by DFBSEC(beg), direction FORWARD...
        by='section_id')  # ...provided within the same section
    segments.sort_values(['section_id', 'dfbsec_beg'], inplace=True)  # sort
    segments.reset_index(drop=True, inplace=True)  # reset index
    segments['fraction'] = ((segments['dfbsec_beg'] - segments['dfbsec_x']) /  # fraction: distance X to segment begin...
                            (segments['dfbsec_y'] - segments['dfbsec_x']))  # ...over distance X to Y
    segments['fraction'] = segments['fraction'].fillna(0)  # fill NAs with 0
    segments['datetime_beg'] = segments.apply(lambda r: r['datetime_x'] + timedelta(  # adjust time based on...
        seconds=int((r['datetime_y'] - r['datetime_x']).total_seconds() * r['fraction'])), axis=1)  # ...fraction
    remove_cols(segments, ['dfbsec_x', 'dfbsec_y', 'datetime_x', 'datetime_y', 'fraction'])

    # get the end datetime of each segment
    segments['datetime_end'] = segments['datetime_beg'].shift(-1)  # end datetime is begin datetime of next segment...
    segments = pd.merge_asof(  # ...except if the segment is the last of the section, so it is necessary to...
        segments.sort_values('dfbsec_end'),  # ...get end datetime for last segments in each section by merging to...
        trackpoints[['section_id', 'dfbsec', 'datetime']].sort_values('dfbsec'),  # ...datapoints...
        left_on='dfbsec_end', right_on='dfbsec', direction='backward',  # ...by DFBSEC(end), direction BACKWARD...
        by='section_id')  # ...provided within the same section
    segments.sort_values(['section_id', 'dfbsec_beg'], inplace=True)  # sort
    segments.reset_index(drop=True, inplace=True)  # reset index
    segments['section_san'] = segments['section_id'].eq(segments['section_id'].shift(-1))  # note last segments...
    segments['datetime_end'] = segments.apply(  # ...and change their end datetime to the merged one
        lambda r: r['datetime_end'] if r['section_san'] else r['datetime'], axis=1)
    remove_cols(segments, ['dfbsec', 'datetime', 'section_san'])  # clean up

    # get the mid datetime of each segment
    segments['datetime_mid'] = segments.apply(
        lambda r: (r['datetime_beg'] + (r['datetime_end'] - r['datetime_beg']) / 2).floor('s'), axis=1)

    segments = segments[['segment_id', 'line', 'midpoint', 'date', 'datetime_beg', 'datetime_mid', 'datetime_end',
                         'section_id', 'dfbsec_beg', 'dfbsec_end']]  # reorder
    return segments


def presences_delimit(
        datapoints: gpd.GeoDataFrame,
        presence_col: str | None = None,
        block: str = None)\
        -> gpd.GeoDataFrame:

    """Delimit presences.

    From datapoints, get presences.
    There are two options for the datapoints: all rows are presences, in which case there is no need to specify
     presence_col, or only some rows are presences, in which case presence_col must be specified.

    Parameters:
        datapoints :  GeoDataFrame
            The GeoDataFrame that contains the presences.
        presence_col : str, optional, default None
            The name of the column containing the values that determine which points are presences (e.g., a column
             containing a count of individuals). This column must contain only integers or floats. Only needs to be
             specified if the datapoints GeoDataFrame includes points that are not presences.
        block : str, optional, default None
            Optionally, the name of a column that contains unique values to be used to separate the presences into
             blocks. These blocks can then be used later when generating absences.
    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the presences.
    """

    check_dtype(par='datapoints', obj=datapoints, dtypes=gpd.GeoDataFrame)

    presences = datapoints.copy()  # copy the datapoints
    if presence_col is not None:  # if a presence column is specified
        check_dtype(par='presence_col', obj=presence_col, dtypes=str)
        check_cols(df=datapoints, cols=presence_col)
        try:
            presences = presences[presences[presence_col] > 0].reset_index(drop=True)  # select only presences
        except TypeError:  # except some values not numeric
            raise TypeError(
                '\n\n____________________'
                f'\nTypeError: The column "{presence_col}" (i.e., the presence column) contains invalid values.'
                '\nValues in the presence column must be integers or floats.'
                f'\nPlease check the values in "{presence_col}".'
                '\n____________________')

    presences.rename(columns={'geometry': 'point', 'datetime': 'date'}, inplace=True)  # rename columns
    presences['date'] = presences['date'].apply(  # get dates (if there are datetimes)
        lambda dt: pd.to_datetime(dt.date()) if isinstance(dt, (datetime, pd.Timestamp)) else dt)
    presences = gpd.GeoDataFrame(presences, geometry='point', crs=datapoints.crs)  # GeoDataFrame
    presences['point_id'] = ['p' + str(i).zfill(len(str(len(presences))))
                             for i in range(1, len(presences) + 1)]  # create point IDs
    if block is not None:
        check_dtype(par='block', obj=block, dtypes=str)
        check_cols(df=presences, cols=block)
        presences = presences[['point_id', 'point', 'date', 'datapoint_id', block]]  # select and reorder columns
    else:
        presences = presences[['point_id', 'point', 'date', 'datapoint_id']]  # select and reorder columns
    return presences


def presencezones_delimit(
        presences: gpd.GeoDataFrame,
        sections: gpd.GeoDataFrame,
        sp_threshold: int | float,
        tm_threshold: int | float | None = None,
        tm_unit: str | None = None)\
        -> gpd.GeoDataFrame:

    """Delimit presences zones.

    From the presences, use a spatial and, optionally, temporal threshold to make presences zones.
    Presence zones are zones around presences that are deemed to be ‘occupied’ by the animals. Absences will not be
     generated within the presence zones, thus they serve to ensure that absences are generated sufficiently far from
     presences.
    Spatial and temporal thresholds determine the extent of the presence zones. The spatial threshold represents the
     radius and the temporal threshold the number of units (e.g., days) before and after that of the presence. For
     example, a spatial threshold of 10 000 m and a temporal threshold of 5 days means that no absence will be
     generated within 10 000 m and 5 days of any presence.
    Note that the presence zones correspond to sections — specifically, the sections that they overlap spatially and,
     optionally, temporally with, as determined by the spatial and temporal thresholds.

    Parameters:
        presences : GeoDataFrame
            The GeoDataFrame containing the presences from which the presences zones are to be made.
        sections : GeoDataFrame
            The GeoDataFrame containing the sections to which the presences zones correspond.
        sp_threshold : int | float, optional, default None
            The spatial threshold to use for making the presences zones in the units of the CRS.
        tm_threshold : int | float, optional, default None
            The temporal threshold to use for making the presences zones in the units set with tm_unit.
        tm_unit : str, optional, default 'day'
            The temporal units to use for making the presences zones. One of the following:
                'year': year (all datetimes from the same year will be given the same value)
                'month': month (all datetimes from the same month and year will be given the same value)
                'day': day (all datetimes with the same date will be given the same value)
                'hour': hour (all datetimes in the same hour on the same date will be given the same value)
                'moy': month of the year (i.e., January is 1, December is 12 regardless of the year)
                'doy': day of the year (i.e., January 1st is 1, December 31st is 365 regardless of the year
    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the presence zones.
    """

    # presence zones
    check_dtype(par='sections', obj=sections, dtypes=gpd.GeoDataFrame)
    check_dtype(par='presences', obj=presences, dtypes=gpd.GeoDataFrame)
    check_dtype(par='sp_threshold', obj=sp_threshold, dtypes=[int, float])

    presences_pz = presences.copy()  # copy presences for making presence zones
    sections_pz = sections.copy()[['section_id', 'datetime', 'geometry']]  # copy sections for making presence zones
    sections_pz['date'] = sections_pz['datetime'].apply(  # get dates (if there are datetimes)
        lambda dt: pd.to_datetime(dt.date()) if isinstance(dt, (datetime, pd.Timestamp)) else dt)

    if tm_threshold is not None and tm_unit is not None:  # if there is a temporal threshold and temporal unit
        check_dtype(par='tm_threshold', obj=tm_threshold, dtypes=[int, float], none_allowed=True)
        check_dtype(par='tm_unit', obj=tm_unit, dtypes=str)
        tm_unit = tm_unit.lower()
        check_opt(par='tm_unit', opt=tm_unit, opts=['day', 'doy', 'year'])

        # convert datetimes to linear units (see auxiliary for more info)
        sections_pz['unit'] = get_units(datetimes=sections_pz['date'], tm_unit=tm_unit)  # for sections
        presences_pz['unit'] = get_units(datetimes=presences_pz['date'], tm_unit=tm_unit)  # for presences

        presencezones_list = []  # list for presence zones
        for section_unit in sections_pz['unit'].unique():  # for each unique unit of the presence zones
            presences_overlap = []  # list for presences that overlap temporally
            if tm_unit.lower() in ['year', 'day']:  # if the specified temporal unit is year or day
                for presence_unit, presence_point in zip(presences_pz['unit'], presences_pz['point']):  # for each pres
                    if abs(section_unit - presence_unit) <= tm_threshold:  # if the presence overlaps temporally...
                        presences_overlap.append(presence_point)  # ...append its geometry to the list
            elif tm_unit.lower() in ['doy']:  # if the specified temporal unit is day of year
                tm_threshold_complementary = 365 - tm_threshold  # calculate the complementary threshold
                for presence_unit, presence_point in zip(presences_pz['unit'], presences_pz['point']):  # for each pres
                    inner_diff = max(section_unit, presence_unit) - min(section_unit, presence_unit)  # inner difference
                    # if inner diff is less than or equal to threshold or greater than or equal to complementary...
                    if inner_diff <= tm_threshold or inner_diff >= tm_threshold_complementary:
                        presences_overlap.append(presence_point)  # ...append its geometry to the list
            presencezones_list.append({  # append to the presence zones list...
                'unit': section_unit,  # the unique unit of the presence zones
                'presencezones':  # the zones of the temporally overlapping presences (if there are any, else None)
                    gpd.GeoSeries(presences_overlap).buffer(sp_threshold).union_all()
                    if len(presences_overlap) > 0 else None})
        # merge sections to presence zones that they overlap temporally with
        presencezones = pd.merge(sections_pz, pd.DataFrame(presencezones_list), on='unit', how='left')
        # convert the presence zones to GeoSeries
        presencezones['presencezones'] = gpd.GeoSeries(presencezones['presencezones'], crs=presences_pz.crs)
        presencezones.drop('unit', axis=1, inplace=True)  # remove unit col
        presencezones.set_geometry('presencezones', inplace=True)  # set the presence zones as the geometry
        presencezones = presencezones[['section_id', 'presencezones']]  # necessary

    else:  # else if there is no temporal threshold or unit
        presencezones = gpd.GeoDataFrame(  # make a presence zones GeoDataFrame with single row containing...
            data={'section_id': ['all'],  # ...a dummy section ID value and...
                  'presencezones': [presences_pz['point'].buffer(sp_threshold).union_all()]},  # ...zones of all presences
            geometry='presencezones', crs=presences_pz.crs)

    return presencezones


def generate_absences(
        sections: gpd.GeoDataFrame,
        var: str,
        target: int | float,
        limit: int = 10,
        dfls: list[int | float] = None):
    """Generate absences.

    Function to generate absences according to the 'along-the-line' or 'from-the-line' variations. See under
     absences_delimit for more information and parameters.
    """

    # calculate distance from beginning of all sections for each section
    sections['dfbs'] = sections.geometry.length.cumsum().shift(1).replace(np.nan, 0)
    sections_all = sections.geometry.union_all()  # put all sections into single geometry
    absences_list = []  # list for the absences

    i = 0  # initialise i: absence count
    j = 0  # initialise j: attempt count

    # while absence count is less than target and attempt count is less than target x limit
    while i < target and j < target * limit:

        # generate an absence (depends on variation)
        if var in ['a', 'along']:  # along-the-line variation - randomly sample absence along sections
            dfbs = random.uniform(a=0, b=sections_all.length)  # randomly select distance from beginning of all sections
            point = sections_all.interpolate(dfbs)  # make point at that distance
            section = sections.iloc[sections[sections['dfbs'] <= dfbs]['dfbs'].idxmax()]  # get section along which point lies
            if not point.intersects(section['presencezones']):  # if point not in corresponding presence zones...
                absences_list.append({  # ...it is an absence, so append...
                    'point': point,  # ...point
                    'date': section['date'],  # ...date
                    'section_id': section['section_id'],  # ...section ID
                    'dfbs': dfbs})  # ...distance from beginning of sections to point
                i += 1  # increase absence count
        elif var in ['f', 'from']:  # from-the-line variation - randomly sample absence at a distance from sections
            dfbs = random.uniform(a=0, b=sections_all.length-0.001)  # randomly select distance from beginning of all sections
            point_a = sections_all.interpolate(dfbs)  # make point at that distance
            point_b = sections_all.interpolate(dfbs+0.001)  # make point at that distance plus a tiny (arbitrary) distance
            dfl = random.choice(dfls)  # randomly select distance from the line
            side = random.choice(['left', 'right'])  # randomly choose side
            # generate a point at the specified distance from the line by...
            #   ...making a tiny line from point a to point b - LineString([point_a, point_b])
            #   ...making a line parallel to the tiny line at the specified distance on the randomly chosen side -
            #       parallel_offset(distance=dfl, side=side)
            #   ...getting the first coordinate of the parallel - coords[0]
            point = Point(LineString([point_a, point_b]).parallel_offset(distance=dfl, side=side).coords[0])  # point
            section = sections.iloc[sections[sections['dfbs'] <= dfbs]['dfbs'].idxmax()]  # get section along which point a lies
            if not point.intersects(section['presencezones']):  # if point not in corresponding presence zones...
                absences_list.append({  # ...it is an absence, so append...
                    'point': point,  # ...point
                    'date': section['date'],  # ...date
                    'section_id': section['section_id'],  # ...section ID
                    'dfbs': dfbs,  # ...distance from beginning of sections to point
                    'point_al': point_a})   # ...point a
                i += 1  # increase absence count
        else:  # unrecognised variation (should not be reached given check_opt() above)
            raise Exception
        j += 1  # increase attempt count

    print(f'Target: {target} | Attempts: {j} | Successes: {i}')  # print summary
    if i > 0:  # if at least one absence generated
        absences = gpd.GeoDataFrame(absences_list, geometry='point', crs=sections.crs)  # GeoDataFrame
        return absences
    else:  # if no absences generated
        return None


def absences_delimit(
        sections: gpd.GeoDataFrame,
        presencezones: gpd.GeoDataFrame,
        var: str,
        target: int | float,
        limit: int = 10,
        dfls: list[int | float] = None,
        block: str = None,
        how: str = None,
        presences: gpd.GeoDataFrame = None)\
        -> gpd.GeoDataFrame:

    """Delimit the absences.

    Absences can be generated by one of two variations: the 'along-the-line' variation or the 'from-the-line'
     variation.
    In the along-the-line variation, each absence is generated by randomly placing a point along the survey track,
     provided it is not within the corresponding presences zones.
    In the from-the-line variation, each absence is generated by randomly placing a point along the survey track and
     then placing a second point a certain distance from the first point perpendicular to the track, provided that
     this second point is not within the corresponding presences zones. The distance from the track is selected from
     a list of candidate distances that can be generated in any way, including from a predefined distribution (e.g.,
     a detection function) by using the function generate_dfls.

    Parameters:
        sections : GeoDataFrame
            The GeoDataFrame containing the sections used to generate the absences.
        presencezones : GeoDataFrame
            The GeoDataFrame containing the presences zones used to generate the absences.
        var : {'along', 'from'}
            The variation to use to generate the absences. Must be one of the following:
                'along': along-the-line - the absences are generated by randomly placing a point along the surveyed
                 lines ('a' also accepted)
                'from': from-the-line - the absences are generated by, firstly, randomly placing a point along the
                 line and then, secondly, placing a point a certain distance from the first point perpendicular to
                 the line ('f' also accepted)
        target : int | float
            The target number of absences to be generated. Note that, during thinning (optionally conducted later),
             some absences may be removed so, to account for this, the target should be set higher than the number
             desired.
        limit : int, optional, default 10
            The value that is multiplied by the target to get the maximum potential number of points (e.g., if
             target=100 and limit=10, a maximum of 1000 points can be generated). If the maximum number is reached
             (or the target number of absences is reached), further absence generation is abandoned and those
             absences that have been made are returned.
        dfls : list[int | float], optional, default None
            If using the from-the-line variation, a list of candidate distances from the line to use when generating
             absences. For each absence, one of these distances will be chosen at random and used to place the
             absence at that distance from the survey line. These distances can be generated in any way, including
             from a predefined distribution (e.g., a detection function) with the function generate_dfls.
        block : str, optional, default None
            Optionally, the name of a column in the sections that contains unique values to be used to separate the
             generation of absences into blocks. For example, to generate absences on a yearly basis or on a
             regional basis. If using block, how must also be specified.
        how : str, optional, default None
            If using block, how the number of absences to be generated per block is calculated. Must be one of the
             following:
                'target' : the number of absences per block will be equal to the target
                'average': the number of absences for all blocks will be the target divided by the number of blocks
                 (rounded up if there is a remainder)
                'effort': the number of absences will be the target divided proportionally by the amount of survey
                 effort (measured as length of the sections) per block
                'presences': the number of absences per block will be equal to the corresponding number of presences
                 multiplied by the target (e.g., if a block has 19 presences and target=2, then 38 absences will be
                 generated for that block); note that presences must also be input if using this option
        presences : GeoDataFrame, optional, default None
            If using block and how='presences', the presences GeoDataFrame on which to base the number of absences. Note
             that the presences must contain the same block column as the sections.
    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the absences.
    """

    check_dtype(par='sections', obj=sections, dtypes=gpd.GeoDataFrame)
    check_dtype(par='presencezones', obj=presencezones, dtypes=gpd.GeoDataFrame)
    check_dtype(par='var', obj=var, dtypes=str)
    var = var.lower()
    check_opt(par='var', opt=var, opts=['along', 'a', 'from', 'f'])
    check_dtype(par='target', obj=target, dtypes=int)
    check_dtype(par='dfls', obj=dfls, dtypes=list, none_allowed=True)

    # assign presence zones to sections
    if len(presencezones) == 1:  # if all sections have the same presence zones (i.e., no temporal dimension)
        sections_pzs = sections.copy()  # copy the sections
        sections_pzs['presencezones'] = presencezones['presencezones'][0]  # add presence zones
    else:  # sections have different presence zones
        sections_pzs = pd.merge(left=sections,  # merge sections to...
                                right=presencezones,  # ...corresponding presence zones
                                on='section_id', how='left')  # ...by section ID
    sections_pzs['date'] = sections_pzs['datetime'].apply(  # get dates (if there are datetimes)
        lambda dt: pd.to_datetime(dt.date()) if isinstance(dt, (datetime, pd.Timestamp)) else dt)

    if block is not None and how is not None:  # if block specified
        check_dtype(par='block', obj=block, dtypes=str, none_allowed=True)
        check_cols(df=sections_pzs, cols=block)
        check_dtype(par='how', obj=how, dtypes=str, none_allowed=True)
        check_opt(par='how', opt=how, opts=['target', 'average', 'effort', 'presences'])
        if how in ['presences', 'p']:
            check_dtype(par='presences', obj=presences, dtypes=gpd.GeoDataFrame)

        rate = target / float(sections_pzs.length.sum())  # calculate the rate (only nec if how='effort')
        absences_list = []  # list for absences
        for uniq in sections_pzs[block].unique():  # for each block
            print(f'\nBlock: {str(uniq)}')  # print block value
            sections_block = sections_pzs.copy()[sections_pzs[block] == uniq].reset_index(drop=True)  # subset sections

            # calculate the target for the block
            if how in ['target', 't']:  # if how is target, block target is same as target
                target_block = target
            elif how in ['average', 'a']:  # if how is average, block target is target divided by number of blocks
                target_block = int(np.ceil(target / sections_pzs[block].nunique()))
            elif how in ['effort', 'e']:  # if how is effort, block target is length of track in block x rate
                target_block = int(np.ceil(sections_block.length.sum() * rate))
            elif how in ['presences', 'p']:  # if how is presences, block target is number of presences in block
                target_block = len(presences[presences[block] == uniq]) * target
            else:  # should never be reached given check_opt() above
                target_block = None

            if target_block > 0:  # if block target more than 0 (can be 0 if how='presences' and no presences in block)
                absences_block = generate_absences(  # generate absences
                    sections=sections_block,
                    var=var,
                    target=target_block,
                    dfls=dfls,
                    limit=limit)
                absences_block[block] = uniq  # add block value to absences
                absences_list.append(absences_block)  # append absences for block to list

        absences = pd.concat(absences_list).reset_index(drop=True)  # concat all absences

    else:  # if block not specified
        absences = generate_absences(  # generate absences
            sections=sections_pzs,
            var=var,
            target=target,
            dfls=dfls,
            limit=limit)

    absences = absences.sort_values(['date', 'dfbs']).reset_index(drop=True)  # sort by date and distance from beginning of sections
    absences['point_id'] = ['a' + str(i).zfill(len(str(len(absences)))) for i in range(1, len(absences) + 1)]  # create point IDs

    absences_cols = ['point_id', 'point', 'date', 'section_id', 'dfbs']  # columns to keep in order
    if block is not None:  # if using block...
        absences_cols = absences_cols + [block]  # ...add block to columns to keep
    if var in ['f', 'from']:  # if using from-the-line variation...
        absences_cols = absences_cols + ['point_al']  # ...add point_al to columns to keep
    absences = absences[absences_cols]  # keep only necessary columns
    return absences


##############################################################################################################
# Stage 3: Functions for Samples
def assign_periods(gdf: gpd.GeoDataFrame, periods: pd.DataFrame | str | None) -> gpd.GeoDataFrame:

    """Assign periods to datapoints or sections.

    Takes a GeoDataFrame containing datapoints or sections of survey track and one containing periods and determines
     which period each datapoint/section lies within by applying a merge_asof.

    Parameters:
        gdf : GeoDataFrame
            GeoDataFrame containing datapoints as shapely Points or sections as shapely LineStrings.
        periods : DataFrame
            One of the following:
                a DataFrame containing periods as delimited with periods_delimit()
                the name of the column in gdf that details which period each datapoint/section lies within
                None (if no periods are to be assigned)

    Returns:
        The GeoDataFrame gdf with an additional column, 'period_id', detailing which period each datapoint/section
         lies within.
    """

    geometry_col = gdf.geometry.name  # get name of geometry column
    crs = gdf.crs  # get CRS

    if isinstance(periods, pd.DataFrame):  # if periods were delimited with delimit_periods()
        remove_cols(df=gdf, cols=['period_id'])  # remove columns (if applicable)
        gdf = pd.merge_asof(gdf.sort_values('datetime'), periods[['period_id', 'date_beg']],  # temporal join
                            left_on='datetime', right_on='date_beg', direction='backward')
        remove_cols(df=gdf, cols='date_beg')
        gdf = gdf.sort_index()
    elif isinstance(periods, str):  # if periods are preset and the column name has been entered
        check_cols(df=gdf, cols=periods)
        if periods != 'period_id':  # if periods column not called 'period_id'...
            gdf['period_id'] = gdf[periods]  # ...duplicate it
    elif not periods:  # if there are no periods
        gdf['period_id'] = 'none'
    else:  # period is not of a recognised datatype
        raise TypeError('\nunable to assign periods. Periods of invalid datatype.')

    gdf = gpd.GeoDataFrame(gdf, geometry=geometry_col, crs=crs)
    return gdf


def assign_cells(gdf: gpd.GeoDataFrame, cells: gpd.GeoDataFrame) -> gpd.GeoDataFrame:

    """Assign cells to datapoints or sections.

    Takes a GeoDataFrame containing datapoints or sections of survey track and one containing grid cells and determines
     which cell(s) each datapoint/section lies within by applying a spatial join.

    Parameters:
        gdf : GeoDataFrame
            GeoDataFrame containing datapoints as shapely Points or sections as shapely LineStrings.
        cells : GeoDataFrame
            GeoDataFrame containing grid cells as shapely Polygons.

    Returns:
        The GeoDataFrame gdf with an additional column, 'cell_id', detailing which grid cell each datapoint/section
         lies within.
    """

    geometry_col = gdf.geometry.name  # get name of geometry column
    crs = gdf.crs  # get CRS

    remove_cols(df=gdf, cols=['cell_id', 'polygon'])  # remove columns (if applicable)
    gdf = gpd.sjoin(left_df=gdf, right_df=cells[['cell_id', 'polygon']], how='left')  # spatial join
    gdf = gdf.drop('index_right', axis=1)  # drop index_right (byproduct of spatial join)

    gdf = gpd.GeoDataFrame(gdf, geometry=geometry_col, crs=crs)
    return gdf


def assign_segments(gdf: gpd.GeoDataFrame, segments: gpd.GeoDataFrame, how: str) -> gpd.GeoDataFrame:

    """Assign segments to datapoints.

    Takes a GeoDataFrame containing datapoints and one containing segments and determines which segment each datapoint
     corresponds to.

    Parameters:
        gdf : GeoDataFrame
            GeoDataFrame containing datapoints as shapely Points.
        segments : GeoDataFrame
            GeoDataFrame containing segments as shapely LineStrings.
        how : str
            An option specifying how to determine which segment each datapoint corresponds to. Must be one of the
             following:
                line: each datapoint is matched to the nearest segment that has the same date
                midpoint: each datapoint is matched to the segment with the nearest midpoint that has the same date
                datetime: each datapoint is matched to a segment based on the datetime of the datapoint and the
                 beginning datetimes of the segments (note that Segments.datetimes must be run before; note also that,
                 if multiple surveys are run simultaneously, they will need to be processed separately to avoid
                 datapoints from one survey being allocated to segments from another due to temporal overlap)
                dfb: each datapoint is matched to a segment based on the distance it is located from the start of the
                 sections lines (only applicable for matching segments that were made from sections that were made from
                 datapoints with Sections.from_datapoints and those datapoints)

    Returns:
        The GeoDataFrame gdf with an additional column, 'segment_id', detailing which segment each datapoint corresponds
         to.
    """

    check_dtype(par='how', obj=how, dtypes=str)
    how = how.lower()
    check_opt(par='how', opt=how, opts=['line', 'midpoint', 'datetime', 'dfb'])

    geometry_col = gdf.geometry.name  # get name of geometry column
    crs = gdf.crs  # get CRS

    remove_cols(df=gdf, cols=['dfbsec_beg', 'segment_id'])  # remove columns, if present

    if how in ['line', 'midpoint']:  # if how is line or midpoint
        id_pairs_list = []  # a list for pairs of datapoint IDs and segment IDs
        if all(gdf['datetime']) and all(segments['date']):  # if GeoDataFrame has datetimes and segments have dates
            for datapoint_id, datapoint_datetime, datapoint_point in (  # for each datapoint, its datetime, and its geom
                    zip(gdf['datapoint_id'], gdf['datetime'], gdf['geometry'])):
                # determine which segments temporally overlap the datapoint (i.e., occur on the same date)
                segments['overlap'] = segments['date'].apply(
                    lambda d: 1 if d.strftime('%Y-%m-%d') == datapoint_datetime.strftime('%Y-%m-%d') else 0)
                if segments['overlap'].sum() == 0:  # if no segments temporally overlap...
                    print('\n\n____________________'  # ...raise warning
                          f'Warning: A datapoint (ID: {datapoint_id}) does not temporally overlap any segment.'
                          '\n____________________')
                elif segments['overlap'].sum() == 1:  # if only one segment temporally overlaps...
                    id_pairs_list.append(  # ...it is the nearest so add it to the list
                        {'datapoint_id': datapoint_id,
                         'segment_id': segments['segment_id'].iloc[segments['overlap'].idxmax()]})
                else:  # if multiple segments temporally overlap...
                    if how == 'line':  # if assigning by nearest line...
                        id_pairs_list.append(  # ...add the spatially nearest segment to the list
                            {'datapoint_id': datapoint_id,
                             'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                                 nearest_points(datapoint_point, segments[segments['overlap'] == 1].geometry)[1]).idxmin()]
                             })
                    elif how == 'midpoint':  # if assigning by nearest midpoint...
                        id_pairs_list.append(  # ...add the segment with the spatially nearest midpoint to the list
                            {'datapoint_id': datapoint_id,
                             'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                                 segments[segments['overlap'] == 1]['midpoint']).idxmin()]
                             })
        else:  # if one or both of the GeoDataFrame and segments do not contain datetimes or dates
            for datapoint_id, datapoint_point in (  # for each datapoint and its geom
                    zip(gdf['datapoint_id'], gdf['geometry'])):
                if how == 'line':  # if assigning by nearest line...
                    id_pairs_list.append(  # ...add the spatially nearest segment to the list
                        {'datapoint_id': datapoint_id,
                         'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                             nearest_points(datapoint_point, segments.geometry)[1]).idxmin()]
                         })
                elif how == 'midpoint':  # if assigning by nearest midpoint...
                    id_pairs_list.append(  # ...add the segment with the spatially nearest midpoint to the list
                        {'datapoint_id': datapoint_id,
                         'segment_id': segments['segment_id'].iloc[datapoint_point.distance(
                             segments['midpoint']).idxmin()]
                         })
        id_pairs = pd.DataFrame(id_pairs_list)  # make DataFrame of ID pairs
        remove_cols(df=segments, cols='overlap')  # clean up
        gdf = pd.merge(left=gdf, right=id_pairs, on='datapoint_id', how='left')  # merge pairs to datapoints

    elif how in ['datetime']:  # else if how is datetime
        if 'datetime_beg' in segments:  # if segments have a begin datetime col
            gdf = pd.merge_asof(  # merge...
                gdf.sort_values('datetime'),  # ...the datapoints to the...
                segments[['segment_id', 'datetime_beg']].sort_values('datetime_beg'),  # ...segments...
                left_on='datetime', right_on='datetime_beg', direction='backward')  # ...by datetime, backwards
            remove_cols(df=gdf, cols=['datetime_beg'])  # clean up
        else:
            raise Exception('\n\n____________________'
                            f'\nKeyError: column "datetime_beg" not found in segments.'
                            '\nPlease ensure that segments have been allocated datetimes before running.'
                            '\n____________________')

    elif how in ['dfb']:  # else if how is DFB
        gdf = get_dfb(trackpoints=gdf, grouper=['section_id'], grouper_name='sec')  # get the DFBSECs
        gdf = pd.merge_asof(gdf.sort_values('dfbsec'),  # merge the trackpoints to the...
                            segments[['section_id', 'dfbsec_beg', 'segment_id']].sort_values('dfbsec_beg'),  # ...segments...
                            left_on='dfbsec', right_on='dfbsec_beg', direction='backward',  # ...by DFBSEC, backwards...
                            by='section_id')  # ...provided within the same section
        gdf = gdf.sort_values(['section_id', 'dfbsec']).reset_index(drop=True)  # sort by section and DFBSEC
        gdf.drop(['dfbsec', 'dfbsec_beg'], axis=1, inplace=True)  # remove unnecessary

    gdf = gpd.GeoDataFrame(gdf, geometry=geometry_col, crs=crs)  # convert to GeoDataFrame
    return gdf


def samples_grid(cells: gpd.GeoDataFrame, periods: pd.DataFrame | str | None, datapoints: gpd.GeoDataFrame,
                 cols: dict, full: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:

    """Resample datapoints using the grid approach.

    Determines which cell and period each datapoint lies within and then groups together datapoints that lie within
     the same cell and period. As multiple datapoints may lie within the same cell and period, it is necessary to
     treat them in some way (e.g., average them, sum them). The parameter cols dictates how each column is to be
     treated.

    Parameters:
        datapoints : GeoDataFrame
            The GeoDataFrame containing the datapoints.
        cells : Cells
            The GeoDataFrame containing the cells.
        periods : Periods | str | None
            One of the following:
                a DataFrame containing the periods
                a string indicating the name of the column in datapoints containing pre-set periods
                None
        cols : dict
            A dictionary indicating how to treat each of the data columns. The dictionary should have the format:
                {'COLUMN': FUNCTION,
                'COLUMN': FUNCTION}
            ...where COLUMN is the name of a given column as a string (e.g., 'bss') and FUNCTION is a function to
             apply to the values in that column when they are grouped together (e.g., 'mean').
            Functions include those available for pandas.groupby plus some custom functions provided here. For
             example:
            'mean' - get the mean
            'min' - get the minimum
            'max' - get the maximum
            mode - get the mode
            'sum' - sum the values
            'count' - count how many have a value (0s counted, NAs ignored)
            count_nz - count how many have a value (0s not counted, NAs ignored)
            pa - convert numeric values to binary presence-absence (0s not counted, NAs ignored)
            list - list the values
            Note that some functions have quotation marks, while others do not. Note that some functions differ in
             how they treat NA values (missing values) and 0s. It is not necessary to specify all columns, but any
             columns not specified will not be retained. Each column can only be specified once.
        full : bool, optional, default False
            If False, only those cell-period combinations that have at least one datapoint will be included in
             samples. If True, all possible cell-period combinations will be included in samples (note that this
             may result in a large number of samples that have no data).

    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the samples.

    Examples:
        For a set of datapoints with a column of counts of individuals, 'individuals', and a column of values for
         Beaufort sea state (BSS), 'bss', the parameter cols could be set to the following in order to sum the
         individuals observed per sample and get the mean BSS per sample:
            cols={'individuals': 'sum', 'bss': 'mean'}
    """

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
                             'Options include: "mean", "sum", "count", and more.'
                             'Use help(Samples.grid) to see more options.',
                             '\n____________________')

    check_dtype(par='full', obj=full, dtypes=bool)
    if full:  # if full true, get all cell-period combos and merge them
        ids = [(cell, period) for cell in cells['cell_id'] for period in periods['period_id']]  # get all combos of IDs
        ids = pd.DataFrame({'cell_id': [i[0] for i in ids], 'period_id': [i[1] for i in ids]})  # make DataFrame
        samples = pd.merge(ids, samples, on=['cell_id', 'period_id'], how='left')  # merge to samples

    samples = pd.merge(left=periods, right=samples, on='period_id', how='right')  # add IDs and limits
    samples = pd.merge(left=cells, right=samples, on='cell_id', how='right')  # add IDs and limits
    return assigned, samples


def samples_segment(segments: gpd.GeoDataFrame, datapoints: gpd.GeoDataFrame,
                    cols: dict, how: str) -> tuple[pd.DataFrame, pd.DataFrame]:

    """Resample datapoints using the segment approach.

    Determines which segment each datapoint corresponds to and then groups together datapoints that correspond to
     the same segment. As multiple datapoints may correspond to the same segment, it is necessary to treat them in
     some way (e.g., average them, sum them). The parameter cols dictates how each column is to be treated.

    Parameters:
        datapoints : GeoDataFrame
            The GeoDataFrame containing the datapoints.
        segments : GeoDataFrame
            The GeoDataFrame containing the segments.
        cols : dict
            A dictionary indicating how to treat each of the data columns. The dictionary should have the format:
                {'COLUMN': FUNCTION,
                'COLUMN': FUNCTION}
            ...where COLUMN is the name of a given column as a string (e.g., 'bss') and FUNCTION is a function to
             apply to the values in that column when they are grouped together (e.g., 'mean').
            Functions include those available for pandas.groupby plus some custom functions provided here. For
             example:
                'mean' - get the mean
                'min' - get the minimum
                'max' - get the maximum
                mode - get the mode
                'sum' - sum the values
                'count' - count how many have a value (0s counted, NAs ignored)
                count_nz - count how many have a value (0s not counted, NAs ignored)
                pa - convert numeric values to binary presence-absence (0s not counted, NAs ignored)
                list - list the values
            Note that some functions have quotation marks, while others do not. Note that some functions differ in
             how they treat NA values (missing values) and 0s. It is not necessary to specify all columns, but any
             columns not specified will not be retained. Each column can only be specified once.
        how : { 'line', 'midpoint', 'datetime', 'dfb'}
            An option specifying how to determine which segment each datapoint corresponds to. Must be one of the
             following:
                line: each datapoint is matched to the nearest segment that has the same date
                midpoint: each datapoint is matched to the segment with the nearest midpoint that has the same date
                datetime: each datapoint is matched to a segment based on the datetime of the datapoint and the
                 beginning datetimes of the segments (note also that, if multiple surveys are run simultaneously, they
                 will need to be processed separately to avoid datapoints from one survey being allocated to segments
                 from another due to temporal overlap)
                dfb: each datapoint is matched to a segment based on the distance it is located from the start of
                 the sections lines (only applicable for matching segments that were made from sections that were
                 made from datapoints with Sections.from_datapoints and those datapoints)
    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the samples.
    Examples:
        For a set of datapoints that has a column of counts of individuals, 'individuals', and a column of values
         for Beaufort sea state (BSS), 'bss', the parameter cols could be set to the following in order to sum the
         individuals observed per sample and get the mean BSS per sample:
            cols={'individuals': 'sum',  'bss': 'mean'}
    """

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
                             'Options include: "mean", "sum", "count", and more.'
                             'Use help(Samples.grid) to see more options.'
                             '\n____________________')
    samples = pd.merge(left=segments, right=samples, on='segment_id', how='left')  # add IDs and limits ('left' to get all)
    return assigned, samples


def assign_datapoints(
        absences,
        datapoints,
        cols
):
    datapoints = get_dfb(trackpoints=datapoints, grouper=None, grouper_name='s')  # DFBS for each datapoint

    crs = absences.crs  # get absences CRS
    absences = pd.merge_asof(absences.sort_values('dfbs'),  # merge the absences...
                             datapoints[['dfbs', 'datapoint_id'] + cols].sort_values('dfbs'),  # ...with datapoints...
                             on='dfbs', direction='backward')  # ...by the nearest DFBS going backwards as...
    # ...backwards merge selects nearest point PRIOR to the absence
    #   assumption: conditions at absence are those of most recently recorded point, i.e., conditions remain those
    #    of most recently recorded point till another point says otherwise
    absences = gpd.GeoDataFrame(absences, geometry='point', crs=crs)  # GeoDataFrame
    remove_cols(df=datapoints, cols='dfbs')  # remove DFBS from datapoints
    return absences


def samples_point(presences: gpd.GeoDataFrame, absences: gpd.GeoDataFrame,
                  datapoints_p: gpd.GeoDataFrame = None, cols_p: list[str] = None,
                  datapoints_a: gpd.GeoDataFrame = None, cols_a: list[str] = None,
                  block: str = None) -> gpd.GeoDataFrame:

    """Resample datapoints using the point approach.

    Concatenates the presences and absences and assigns them presence-absence values of 1 and 0, respectively.
    Additionally, and optionally, for each presence, gets data from its corresponding datapoint (i.e., the datapoint
     from which the presence was derived).
    Additionally, and optionally, for each absence, gets the datapoint prior to it and assigns to the absence that
     datapoint’s data. The ID of the prior datapoint is also added to the datapoint_id column. Note that this is only
     applicable if absences were generated from sections that were, in turn, made from datapoints with
     Sections.from_datapoints and those corresponding datapoints.

    Parameters:
        presences : GeoDataFrame
            The GeoDataFrame containing the presences.
        absences : GeoDataFrame
            The GeoDataFrame containing the absences.
        datapoints_p : DataPoints, optional, default None
            If adding data to the presences, the DataPoints object containing the data. If specified, data will be added
             to the presences, if not specified, data will not be added to the presences.
        cols_p : list, optional, default None
            If adding data to the presences, a list indicating which data columns in datapoints_p to add to the
             presences.
        datapoints_a : DataPoints, optional, default None
            If adding data to the absences, the DataPoints object containing the data. If specified, data will be added
             to the absences, if not specified, data will not be added to the absences. Note that adding data to
             absences is only applicable for absences that were generated from sections that were made from datapoints
             and those datapoints.
        cols_a : list, optional, default None
            If adding data to the absences, a list indicating which data columns in datapoints_a to add to the absences.
        block : str, optional, default None
            If adding data to absences, optionally, the name of a column in the datapoints and absences that contains
             unique values to be used to separate the datapoints and absences into blocks in order to speed up the
             assigning of data to absences. If block was used to delimit absences, it must be used here, if adding data
             to absences.

    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the samples.
    """

    crs = presences.crs  # get presences CRS

    # datapoints to presences
    if datapoints_p is not None:
        check_dtype(par='datapoints_p', obj=datapoints_p, dtypes=gpd.GeoDataFrame)
        check_dtype(par='cols_p', obj=cols_p, dtypes=list)
        check_cols(df=datapoints_p, cols=cols_p)
        cols_p = [c for c in cols_p if c not in presences]  # remove cols already in presences

        presences = pd.merge(left=presences,  # merge the presences...
                             right=datapoints_p[['datapoint_id'] + cols_p],  # ...to selected columns of datapoints...
                             how='left', on='datapoint_id')  # ...by matching their datapoint IDs
        presences = gpd.GeoDataFrame(presences, geometry='point', crs=crs)  # GeoDataFrame

    # datapoints to absences
    if datapoints_a is not None:
        check_dtype(par='datapoints_a', obj=datapoints_a, dtypes=gpd.GeoDataFrame)
        check_dtype(par='cols_a', obj=cols_a, dtypes=list)
        check_cols(df=datapoints_a, cols=cols_a)
        cols_a = [c for c in cols_a if c not in absences]  # remove cols already in absences

        if block is not None:  # if block specified
            check_dtype(par='block', obj=block, dtypes=str, none_allowed=True)
            check_cols(df=datapoints_a, cols=block)
            check_cols(df=absences, cols=block)

            absences_list = []
            for uniq in absences[block].unique():  # for each unique block in the sections
                datapoints_block = datapoints_a.copy()[datapoints_a[block] == uniq].reset_index(drop=True)
                absences_block = absences.copy()[absences[block] == uniq].reset_index(drop=True)

                if len(absences_block) > 0:  # if there are any corresponding absences
                    absences_block = assign_datapoints(  # assign a datapoint to each absence
                        absences=absences_block,
                        datapoints=datapoints_block,
                        cols=cols_a)
                    absences_list.append(absences_block)

            absences = pd.concat(absences_list).reset_index(drop=True)

        else:
            absences = assign_datapoints(  # assign a datapoint to each absence
                absences=absences,
                datapoints=datapoints_a,
                cols=cols_a)

    # concat presences and absences
    presences['p-a'] = 1  # set presence-absence value
    absences['p-a'] = 0  # set presence-absence value
    samples = pd.concat([presences, absences]).reset_index(drop=True)  # concat presences and absences
    samples = samples[['point_id', 'point', 'date', 'datapoint_id', 'p-a'] +  # reorder columns
                      [c for c in samples if c not in ['point_id', 'point', 'date', 'datapoint_id', 'p-a',
                                                       'section_id', 'dfbs']] +
                      ['section_id', 'dfbs']]
    samples = gpd.GeoDataFrame(samples, geometry='point', crs=crs)  # GeoDataFrame
    return samples


def samples_grid_se(sections: gpd.GeoDataFrame, cells: gpd.GeoDataFrame, periods: pd.DataFrame | str | None,
                    length: bool = True, esw: int | float = None, euc_geo: str = 'euclidean', full: bool = False)\
        -> tuple[pd.DataFrame, pd.DataFrame]:

    """Measure survey effort using the grid approach.

    Measures the amount of survey track that lies within each cell-period combination to get a measure of survey
     effort. Survey effort per cell-period can be measured in two ways:
        length - length of the survey track in each cell-period
        area - area of the buffered survey track in each cell-period
    Moreover, each of these ways can be measured using Euclidean or geodesic measurements, as determined by the
     parameter euc_geo. Geodesic measurements will be more precise but take longer to run. Multiple measures of
     survey effort can be calculated simultaneously. If the parameter length is True, length will be measured. If
     the parameter esw is specified, area will be measured.

    Parameters:
        sections : GeoDataFrame
            The GeoDataFrame containing the sections.
        cells : GeoDataFrame
            The GeoDataFrame containing the cells.
        periods : DataFrame | str | None
            One of the following:
                a DataFrame containing the periods
                a string indicating the name of the column in datapoints containing pre-set periods
                None
        length : bool, optional, default True
            If True, the length of survey track in each cell-period combination will be measured.
        esw : int | float, optional, default None
            Optionally, the one-sided effective stripwidth (ESW). If a value is given, the area of survey track in
             each cell-period combination will be measured. Note that ESW is one-sided.
        euc_geo : {'euclidean', 'geodesic', 'both'}, optional, default 'euclidean'
            The type of measurement. Must be one of the following: 'euclidean', 'geodesic', or 'both'.
        full : bool, optional, default False
            If False, only those cell-period combinations that have at least some survey effort will be included in
             samples. If True, all possible cell-period combinations will be included in samples (note that this may
             result in a large number of samples that have no data).
    Returns
        GeoDataFrame
            Returns a GeoDataFrame containing the samples. The survey effort measures will be contained in the following
             columns (if applicable):
                se_length: survey effort measured as length with Euclidean distances
                se_area: survey effort measured as area with Euclidean distances
                se_length_geo: survey effort measured as length with geodesic distances
                se_area_geo: survey effort measured as area with geodesic distances
    """

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

        assigned = pd.merge(left=assigned,  # merge assigned skeleton to...
                            right=assigned_length,  # ...length measurements
                            on=['section_id', 'datetime', 'period_id', 'cell_id'], how='outer')
        samples_length = (assigned_length.copy().groupby(['cell_id', 'period_id']).  # group by cell-period...
                          agg(agg_dict).reset_index())  # ...and sum measurements
        samples = pd.merge(left=samples,  # merge samples skeleton...
                           right=samples_length,  # ...to length samples
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

        assigned = pd.merge(left=assigned,  # merge assigned skeleton to...
                            right=assigned_area,  # ...area measurements
                            on=['section_id', 'datetime', 'period_id', 'cell_id'], how='outer')
        samples_area = (assigned_area.copy().groupby(['cell_id', 'period_id']).  # group by cell-period...
                        agg(agg_dict).reset_index())  # ...and sum measurements
        samples = pd.merge(left=samples,  # merge samples skeleton...
                           right=samples_area,  # ...to area samples
                           on=['cell_id', 'period_id'], how='outer')

    check_dtype(par='full', obj=full, dtypes=bool)
    if full:  # if full true, get all cell-period combos and merge them
        ids = [(cell, period) for cell in cells['cell_id'] for period in periods['period_id']]  # get all combos of IDs
        ids = pd.DataFrame({'cell_id': [i[0] for i in ids], 'period_id': [i[1] for i in ids]})  # make DataFrame
        samples = pd.merge(left=ids, right=samples, on=['cell_id', 'period_id'], how='left')  # merge to samples

    samples = pd.merge(left=periods, right=samples, on='period_id', how='right')  # add IDs and limits
    samples = pd.merge(left=cells, right=samples, on='cell_id', how='right')  # add IDs and limits
    return assigned, samples


def samples_segment_se(segments: gpd.GeoDataFrame, length: bool = True, esw: int | float = None,
                       audf: int | float = None, euc_geo: str = 'euclidean') -> pd.DataFrame:

    """Measure survey effort using the segment approach.

    Measures the amount of survey effort per segment. Survey effort per segment can be measured in three ways:
        length - length of the segment
        area - length of the segment multiplied by a one-sided ESW multiplied by 2
        effective area - length of the segment multiplied by a one-sided area under a detection function multiplied by 2
    Moreover, each of these ways can be measured using Euclidean or geodesic measurements, as determined by the
     parameter euc_geo. Geodesic measurements will be more precise but take longer to run. Multiple measures of survey
     effort can be calculated simultaneously. If the parameter length is True, length will be measured. If the parameter
     esw is specified, area will be measured.

    Parameters:
        segments : GeoDataFrame
            The GeoDataFrame containing the segments.
        length : bool, optional, default True
            If True, the length of each segment will be measured.
        esw : int | float, optional, default None
            Optionally, the one-sided effective stripwidth (ESW). If a value is given, the area of each segment will be
             measured. Note that ESW is one-sided.
        audf : int | float, optional, default None
            Optionally, the one-sided area under detection function (AUDF). If a value is given, the effective area of
             each segment will be measured. Note that AUDF is one-sided.
        euc_geo : {'euclidean', 'geodesic', 'both'}, optional, default 'euclidean'
            The type of measurement. Must be one of the following: 'euclidean', 'geodesic', or 'both'.

    Returns
        GeoDataFrame
            Returns a GeoDataFrame containing the segments. The survey effort measures will be contained in the
             following columns (if applicable):
                se_length: survey effort measured as length with Euclidean distances
                se_area: survey effort measured as area with Euclidean distances
                se_effective: survey effort measured as effective area with Euclidean distances
                se_length_geo: survey effort measured as length with geodesic distances
                se_area_geo: survey effort measured as area with geodesic distances
                se_effective_geo: survey effort measured as effective area with geodesic distances
    """

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
        lengths_geo = np.array([Geod(ellps='WGS84').geometry_length(segment) for segment in
                                samples.geometry.to_crs('EPSG:4326')])  # ...measure lengths as geodesic distances
        if length:  # if lengths...
            samples['se_length_geo'] = lengths_geo  # ...add lengths
        if esw:  # if ESW...
            samples['se_area_geo'] = lengths_geo * esw * 2  # ...calculate and add area
        if audf:  # if AUDF...
            samples['se_effective_geo'] = lengths_geo * audf * 2  # ...calculate and add effective area

    return samples


def samples_merge(approach: str, **kwargs: pd.DataFrame):

    """Merge multiple GeoDataFrames containing samples together.

    Merge multiple GeoDataFrames containing samples into a single new GeoDataFrame. Each GeoDataFrame containing samples
     should be entered as a parameter with a unique name of the user’s choosing. Only samples made with the grid or
     segment approach can be merged.

    Parameters:
        **kwargs :
            Any number of Samples objects each entered as a parameter with a unique name of the user’s choosing.
        approach : str
            A string indicating the approach used to generate the samples. One of the following:
                'grid'
                'segment'
    Returns:
        GeoDataFrame
            Returns a GeoDataFrame containing the merged samples.
    """

    check_dtype(par='approach', obj=approach, dtypes=str)
    approach = approach.lower()
    check_opt(par='approach', opt=approach, opts=['g', 'grid', 's', 'segment'])

    if approach in ['g', 'grid']:  # grid approach
        merger_potential = ['cell_id', 'polygon', 'centroid',  # merge on cell details and...
                            'period_id', 'date_beg', 'date_mid', 'date_end']  # ...period details
    elif approach in ['s', 'segment']:  # segment approach
        merger_potential = ['segment_id', 'line', 'midpoint',  # merge on segment details
                            'date', 'datetime_beg', 'datetime_mid', 'datetime_end',
                            'section_id', 'dfbsec_beg', 'dfbsec_end']
    else:  # unknown approach (should never be reached given check_opt() above)
        raise ValueError

    # compare columns
    cols = []  # empty list for all cols from all samples
    for samples in kwargs.values():  # for each samples...
        cols += [col for col in samples]  # ...add cols
    shared = [k for k, v in Counter(cols).items() if v > 1]  # get cols present in multiple samples
    rename = [c for c in shared if c not in merger_potential]  # remove potential merging columns to get cols to rename
    merger = [c for c in shared if c in merger_potential]  # get potential merging columns that are shared

    # rename columns (if necessary)
    if len(rename) > 0:
        print(f'Warning: multiple samples contain one or more columns with the same name. '
              f'These columns will be renamed as follows:')
        for name, samples in kwargs.items():  # for each samples and its name
            renamer = {col: col + '_' + name for col in rename if col in samples}  # get cols to be renamed
            if len(renamer) > 0:  # if there are cols to be renamed...
                samples.rename(columns=renamer, inplace=True)  # ...rename them and...
                rename_print = [k + '" to "' + v + '"' for k, v in renamer.items()]
                print(f'  In samples "{name}":'  # ...print message
                      f'\n    "{" | ".join(rename_print)}')

    merged = reduce(lambda left, right: pd.merge(left, right, on=merger, how='outer'), kwargs.values())  # merge all
    return merged


##############################################################################################################
# Stage 3: Output
def extract_coords(samples: gpd.GeoDataFrame) -> gpd.GeoDataFrame:

    """
    Extracts the coordinates from the centroids, midpoints, or points and puts them in two new columns suffixed
     with '_lon' and '_lat' or '_x' and '_y'.
    """

    if samples.crs.axis_info[0].unit_name == 'degree':
        suffix_x, suffix_y = '_lon', '_lat'
    else:
        suffix_x, suffix_y = '_x', '_y'

    for geometry in ['centroid', 'midpoint', 'point']:
        if geometry in samples:  # if it is in samples
            remove_cols(df=samples, cols=[geometry + '_lon', geometry + '_lat', geometry + '_x', geometry + '_y'])
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
    cells.plot(ax=ax, edgecolor='#dedede', facecolor=colours['colours'], alpha=0.2, zorder=2)


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


def presencezones_plot(ax, zones):
    zones.dissolve().plot(ax=ax, color='#0055a3', alpha=0.1, zorder=4)


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


##############################################################################################################
# Additional functions

# Little functions for resampling
def pa(c):
    """Converts count (of individuals or sightings) to binary presence-absence value."""
    return 1 if np.nansum(list(c)) > 0 else 0


def count_nz(c):
    """Counts how many have a value (0s not counted)."""
    return len([ci for ci in list(c) if ci > 0])


def mode(c):
    """Returns the mode (most frequent value)."""
    return pd.Series.mode(c)


# Slightly larger functions for distance sampling
def generate_dfls(number: int | float, esw: int | float, interval: int | float, dfunc: typing.Callable = None)\
        -> list[int | float]:

    """Generates distances from a line.

    Generates distances from a line between 0 and the specified effective stripwidth (ESW) at intervals set by interval.
     If dfunc is specified, the distances will be based on probabilities set by dfunc, else probabilities will be even
     for all intervals.

    __________
    Parameters:
      number: int | float
        The number of distances to generate.
      esw: int | float
        The effective stripwidth (i.e., the maximum distance from the line).
      interval: int | float
        The minimum interval between potential distances. For example, if interval=0.1, potential distances will be: 0,
         0.1, 0.2, 0.3, etc...
      dfunc: typing.Callable, optional, default None
        Optionally, a callable function (e.g., a detection function), in which case, distances will be generated based on
         probabilities derived from the function. Function should be predefined then input to generate_dfls. If not
         specified, distances will be evenly distributed between 0 and the ESW.

    __________
    Example:
        number = 100000
        esw = 2000
        interval = 1
        def dfunc(x): return exp((-x**2) / (2*500**2))
        dfls = generate_dfls(number=number, esw=esw, interval=interval, dfunc=dfunc)

    __________
    Returns:
      The distances from the line as a list of integers or floats.
    """

    intervals = np.arange(0, esw + interval, interval)  # regular intervals from the line
    # probabilities for the distances at the regular intervals:
    #   an array of 1s (if dfunc is None)
    #   an array of varying values based on the function (if dfunc is a function)
    probabilities = [dfunc(x) for x in intervals] if isinstance(dfunc, typing.Callable) else np.ones(len(intervals))
    dfls = [float(dfl) for dfl in random.choices(intervals, probabilities, k=number)]  # sample selection of distances based on probabilities
    return dfls


def calculate_area_udf(esw: int | float, interval: int | float, dfunc: typing.Callable | int | float) -> int | float:

    """Calculate area under detection function.

    Calculates the area under a detection function between 0 and the specified effective stripwidth (ESW). If dfunc is
     specified, the area will be based on dfunc, else the area will be based on an even probability across intervals.

    __________
    Parameters:
      esw: int | float
        The effective stripwidth (i.e., the maximum distance from the line).
      interval: int | float
        The minimum interval between potential distances. For example, if interval=0.1, potential distances will be: 0,
         0.1, 0.2, 0.3, etc...
      dfunc: typing.Callable, optional, default None
        Optionally, a callable function (e.g., a detection function), in which case, distances will be generated based on
         probabilities derived from the function. Function should be predefined then input to generate_dfls. If not
         specified, distances will be evenly distributed between 0 and the ESW.

    __________
    Example:
        esw = 2000
        interval = 1
        def dfunc(x): return exp((-x**2) / (2*500**2))
        area = calculate_area_udf(esw=esw, interval=interval, dfunc=dfunc)

    __________
    Returns:
      The area under the detection function as an integer or float.
    """
    intervals = np.arange(0, esw + interval, interval)  # distances from the line at set intervals
    # probabilities for the distances at the regular intervals:
    #   an array of 1s (if dfunc is None)
    #   an array of varying values based on the function (if dfunc is a function)
    probabilities = [dfunc(x) for x in intervals] if isinstance(dfunc, typing.Callable) else np.ones(len(intervals))
    area_udf = (sum(probabilities[1:-1] * interval) +  # area equals probabilities multiplied by interval except...
                probabilities[0] * (interval / 2) +  # first and...
                probabilities[-1] * (interval / 2))  # last probabilities which are multiplied by half interval
    return area_udf
