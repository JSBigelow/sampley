# Various little functions for performing basic operations and checking

##############################################################################################################
# Imports
from datetime import datetime, timezone
import geopandas as gpd
import pandas as pd
from pandas._libs.tslibs.parsing import DateParseError
import pyproj.exceptions
from pyproj import CRS
import pyogrio.errors
import pytz
from shapely import wkt
import os


##############################################################################################################
# Checkers

#####
# General
def check_cols(df: pd.DataFrame, cols: str | list[str]):
    """Checks that columns are present in a DataFrame."""
    cols = [cols] if isinstance(cols, str) else cols
    for col in cols:
        if col not in df:
            raise Exception('\n\n____________________'
                            f'\nKeyError: column "{col}" not found in DataFrame.'
                            '\n____________________')


def check_opt(par: str, opt: str, opts: list[str]):
    """Checks that a specified value is a valid option."""
    if opt.lower() not in opts:
        opts_print = [f'"{opt}"' for opt in opts]
        raise Exception(
            '\n\n____________________'
            f'\nError: invalid value for "{par}". The value is "{opt}".'
            f'\nPlease ensure that the value for "{par}" is one of:'
            f'\n  {", ".join(opts_print)}'
            '\n____________________')


def check_dtype(par: str, obj, dtypes, none_allowed: bool = False):
    """Checks that the datatype of a specified value is valid."""
    check = False
    dtypes = [dtypes] if not isinstance(dtypes, list) else dtypes
    if obj is None:
        if none_allowed:
            check = True
    else:
        for dtype in dtypes:
            if isinstance(obj, dtype):
                check = True
    if not check:
        raise TypeError(
            '\n\n____________________'
            f'\nTypeError: invalid datatype for the value of "{par}". The datatype is {type(obj).__name__}.'
            f'\nPlease ensure that the value of "{par}" is of one of the following types:'
            f'\n  {", ".join([dtype.__name__ for dtype in dtypes])}'
            '\n____________________')


#####
# CRS
def check_crs(par: str, crs: str | int | pyproj.crs.crs.CRS, none_allowed: bool = False):
    """Checks that a specified value is a valid CRS."""
    check_dtype(par='crs', obj=crs, dtypes=[str, int, pyproj.crs.crs.CRS], none_allowed=none_allowed)
    if none_allowed and crs is None:
        crs_name = 'None'
        check = True
    else:
        if isinstance(crs, pyproj.crs.crs.CRS):
            crs_name = '"' + str(crs) + '"'
            check = True
        elif isinstance(crs, (str, int)):
            crs_name = '"' + crs + '"' if isinstance(crs, str) else crs
            try:
                crs = CRS(crs)
                check = True
            except pyproj.exceptions.CRSError:
                check = False
        else:
            crs_name = crs
            check = False
    if not check:
        raise pyproj.exceptions.CRSError(
            '\n\n____________________'
            f'\nCRSError: Invalid value for "{par}" resulting in invalid CRS.'
            f'\n  The value for "{par}" is {crs_name}'
            f'\n  Please ensure that the value for "{par}" is one of:'
            '\n    a pyproj.crs.crs.CRS'
            '\n    a string or integer in a format accepted by pyproj.CRS.from_user_input(), for example:'
            '\n      "EPSG:4326", "epsg:4326", or 4326'
            '\n____________________')


def check_projected(obj_name: str, crs: str | int | pyproj.crs.crs.CRS) -> None:
    """Checks that a CRS is projected (assumes that the validity of the CRS has already been checked)."""
    crs = CRS(crs) if isinstance(crs, (str, int)) else crs
    if not crs.is_projected:  # if the CRS is not projected
        if isinstance(crs, pyproj.crs.crs.CRS):
            crs_name = '"' + str(crs) + '"'  # get its name
        elif isinstance(crs, (str, int)):
            crs_name = '"' + crs + '"' if isinstance(crs, str) else crs  # get its name
        else:
            crs_name = crs
        print('____________________'  # raise warning
              '\nWarning: CRS is not projected.'
              f'\n  The CRS of {obj_name} is {crs_name}'
              f'\n  Use of a projected CRS is recommended in all cases '
              f'and essential for cases involving distance measurements.'
              '\n____________________')


#####
# Timezones

# list of UTC timezones
tzs = (list(pytz.all_timezones) +
       [f'UTC-{str(i).zfill(2)}:00' for i in range(0, 24)] +
       [f'UTC-{str(i).zfill(2)}:30' for i in range(0, 24)] +
       [f'UTC+{str(i).zfill(2)}:00' for i in range(0, 24)] +
       [f'UTC+{str(i).zfill(2)}:30' for i in range(0, 24)])


def check_tz(par: str, tz: str | timezone | pytz.BaseTzInfo, none_allowed: bool = False):
    """Checks that a specified value is a valid timezone."""
    check_dtype(par='tz', obj=tz, dtypes=[str, timezone, pytz.BaseTzInfo], none_allowed=none_allowed)
    if none_allowed and tz is None:
        tz_name = 'None'
        check = True
    else:
        if isinstance(tz, (timezone, pytz.BaseTzInfo)):
            tz_name = str(tz)
            check = True
        elif isinstance(tz, str):
            tz_name = '"' + tz + '"'
            if tz in tzs:
                check = True
            else:
                check = False
        else:
            tz_name = tz
            check = False
    if not check:
        raise TypeError(
            '\n\n____________________'
            f'\nTimezoneError: invalid value for "{par}" resulting in invalid timezone.'
            f'\n  The value for "{par}" is {tz_name}'
            f'\n  Please ensure that the value for "{par}" is one of:'
            '\n     a datetime.timezone'
            '\n     a string of a timezone name accepted by pytz (run pytz.all_timezones to see all options), for example:'
            '\n       "Europe/Vilnius"'
            '\n       "Pacific/Marquesas"'
            '\n     a string of a UTC code, for example:'
            '\n       "UTC+02:00"'
            '\n       "UTC-09:30"')


##############################################################################################################
# Operations

#####
# General
def open_file(filepath: str) -> pd.DataFrame | gpd.GeoDataFrame:
    """Opens a file."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.csv':
            df = pd.read_csv(filepath)
        elif ext == '.xlsx':
            df = pd.read_excel(filepath)
        elif ext in ['.gpkg', '.shp']:
            df = gpd.read_file(filepath)
        else:
            raise TypeError('\n\n____________________'
                            '\nTypeError: the file is not of a valid type.'
                            f'\n  The file extension is {ext}'
                            '\n  The imported file must be one of the following:'
                            '\n    .gpkg - GeoPackage (for DataPoints and Sections)'
                            '\n    .shp  - ShapeFile (for DataPoints and Sections)'
                            '\n    .csv  - CSV (for DataPoints only)'
                            '\n    .xlsx - Excel (for DataPoints only)'
                            '\n____________________')
        print('Success: file opened.')
        return df
    except (FileNotFoundError, pyogrio.errors.DataSourceError):
        raise FileNotFoundError('\n\n____________________'
                                '\nFileNotFoundError: file not found.'
                                '\n  Please check the filepath:'
                                f'\n    {filepath}'
                                '\n____________________')


def remove_cols(df: pd.DataFrame, cols: str | list[str]):
    """Removes columns from a DataFrame (if they are present)."""
    cols = [cols] if isinstance(cols, str) else cols
    for col in cols:
        if col in df:
            df.drop(col, axis=1, inplace=True)


#####
# Spatial
def parse_xy(df: pd.DataFrame, x_col: str, y_col: str, crs: str | int | pyproj.crs.crs.CRS) -> gpd.GeoDataFrame:
    """Converts a DataFrame to a GeoDataFrame based on two columns containing X and Y coordinates, respectively."""
    try:
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x_col], df[y_col]), crs=crs)
        gdf.drop([x_col, y_col], axis=1, inplace=True)
    except ValueError:
        raise ValueError('\n\n____________________'
                         f'\nValueError: the columns "{x_col}" and/or "{y_col}" contain one or more invalid values.'
                         f'\nPlease check the values in the columns "{x_col}" and "{y_col}".'
                         '\n____________________')
    print('Success: X and Y coordinates parsed.')
    return gdf


def parse_geoms(df: pd.DataFrame, geometry_col: str, crs: str | int | pyproj.crs.crs.CRS) -> gpd.GeoDataFrame:
    """Converts a DataFrame to a GeoDataFrame based on a column containing geometries."""
    try:
        df[geometry_col] = df[geometry_col].apply(wkt.loads)
    except TypeError:
        raise TypeError('\n\n____________________'
                        f'\nTypeError: the column "{geometry_col}" contains values that are not shapely geometries.'
                        f'\nPlease check the values in the column "{geometry_col}".'
                        '\n____________________')
    gdf = gpd.GeoDataFrame(df, geometry=geometry_col, crs=crs)
    gdf.rename(columns={geometry_col: 'geometry'}, inplace=True)
    print('Success: geometries parsed.')
    return gdf


def reproject_crs(gdf: gpd.GeoSeries | gpd.GeoDataFrame, crs_target: str | int | pyproj.crs.crs.CRS | None,
                  additional: str | list[str] = None):
    """Reprojects a GeoDataFrame (and any additional geometries) to a target CRS."""
    if crs_target is not None:
        crs_name = '"' + crs_target + '"' if isinstance(crs_target, str) else (
                '"' + str(crs_target) + '"') if isinstance(crs_target, pyproj.crs.crs.CRS) else crs_target
        if crs_target != gdf.crs:
            if additional is not None:
                additional = [additional] if isinstance(additional, str) else additional
                for geometry in additional:
                    if geometry not in gdf:
                        raise Exception('\n\n____________________'
                                        f'\nKeyError: additional geometry column "{geometry}" not found in GeoDataFrame.'
                                        '\n____________________')
                    else:
                        geometry_gs = gpd.GeoSeries(gdf[geometry]).set_crs(gdf.crs)  # get geometries as a GeoSeries
                        geometry_gs = geometry_gs.to_crs(crs_target)  # reproject
                        gdf[geometry] = geometry_gs  # return to samples GeoDataFrame
                        print(f'Success: additional geometry column "{geometry}" reprojected to CRS {crs_name}')
            gdf = gdf.to_crs(crs_target)
            print(f'Success: reprojected to CRS {crs_name}')
        else:
            print(f'Note: reprojection to CRS {crs_name} not necessary as already in CRS {crs_name}.')
    return gdf


#####
# Temporal
def parse_dts(df: pd.DataFrame, datetime_col: str, datetime_format: str | None = None,
              tz: str | timezone | pytz.BaseTzInfo | None = None):
    """Converts a column of datetime strings into datetimes and, if applicable, sets the timezone."""

    # convert datetime strings to datetimes
    try:
        df[datetime_col] = df[datetime_col].astype(str)  # to ensure consistent datetime formats, convert to string first
        df[datetime_col] = pd.to_datetime(df[datetime_col], format=datetime_format)  # convert to datetimes
        print(f'Success: column "{datetime_col}" reformatted to datetimes.')
    except DateParseError:
        raise DateParseError(
            '\n\n____________________'
            f'\nDateParseError: column "{datetime_col}" contains one or more invalid values.'
            f'\n  Please ensure that values in column "{datetime_col}" are '
            'strings in a format that can be recognised as a datetime, for example:'
            '\n    "2025-03-06 15:19:42"'
            '\n____________________')
    except ValueError:
        if datetime_format is not None:  # if a format is specified
            raise ValueError(
                '\n\n____________________'
                '\nValueError: the datetime format and one or more datetimes do not match.'
                f'\n  Please check the datetime format: "{datetime_format}".'
                '\n  Please ensure that all datetimes have the same format and that it matches the datetime format.'
                '\n  Alternatively:'
                '\n    use format="ISO8601" if the datetimes meet ISO8601 (in greatest to least order, e.g., YYYY-MM-DD)'
                '\n    use format="mixed" if the datetimes have different formats (not recommended as slow and risky).'
                '\n____________________')
        else:  # if no format specified (i.e., format inferred by pandas)
            raise ValueError(
                '\n\n____________________'
                '\nValueError: the datetimes do not all have the same format.'
                '\n  Please ensure that all datetimes have the same format.'
                '\n  Alternatively:'
                '\n    use format="ISO8601" if the datetimes meet ISO8601 (in greatest to least order, e.g., YYYY-MM-DD)'
                '\n    use format="mixed" if the datetimes have different formats (not recommended as slow and risky).'
                '\n____________________')

    # set timezone
    try:
        tz_inherent = str(df[datetime_col].dtype.tz)  # get inherent timezone (if there is one)
        print(f'Note: the inherent (contained within the datetimes) timezone of column "{datetime_col}" is "{tz_inherent}".')
        # if there is an inherent timezone...
        if tz is not None:  # ...and a timezone is specified...
            if str(tz_inherent) != str(tz):  # ...and the two timezones are different, print a warning...
                print(f'Warning: the inherent timezone of column "{datetime_col}" is not equal to the specified timezone. '
                      f'\n  inherent timezone: {str(tz_inherent)}'
                      f'\n  specified timezone: {str(tz)}'                      
                      f'\n  The column "{datetime_col}" will be converted to the specified timezone.')
                df[datetime_col] = df[datetime_col].dt.tz_convert(tz)  # convert to specified timezone
        # ...and no timezone is specified, do nothing
    except AttributeError:  # else, if there is no inherent timezone...
        if tz is not None:  # ...and a timezone is specified
            df[datetime_col] = df[datetime_col].dt.tz_localize(tz)  # set timezone
            print(f'Success: timezone of column "{datetime_col}" set to "{tz}".')
        else:  # ...and no timezone is specified
            print(f'Note: timezone of column "{datetime_col}" was not set as no timezone was specified.')
    return df


def convert_tz(df: pd.DataFrame, datetime_cols: str | list[str], tz_target: str | timezone | pytz.BaseTzInfo | None):
    """Converts datetime column(s) in a DataFrame to a target timezone."""
    if tz_target is not None:  # if a target timezone is specified
        tz_name = str(tz_target) if isinstance(tz_target, (timezone, pytz.BaseTzInfo)) else tz_target  # get name
        datetime_cols = [datetime_cols] if isinstance(datetime_cols, str) else datetime_cols  # ensure datetime_cols is list
        for datetime_col in datetime_cols:
            if datetime_col not in df:
                raise Exception('\n\n____________________'
                                f'\nKeyError: column "{datetime_col}" not found in DataFrame.'
                                '\n____________________')
            else:
                try:
                    tz_inherent = str(df[datetime_col].dtype.tz)  # get inherent timezone
                except AttributeError:
                    raise AttributeError(
                        '\n\n____________________'
                        f'\nAttributeError: the column "{datetime_col}" does not have a timezone.'
                        f'\n  Please set the timezone before attempting to convert.'
                        '\n____________________')
                if str(tz_target) != str(tz_inherent):
                    df[datetime_col] = df[datetime_col].dt.tz_convert(tz_target)  # convert to target timezone
                    print(f'Success: column "{datetime_col}" converted to timezone "{tz_name}"')
                else:
                    print(f'Note: conversion of column "{datetime_col}" to timezone "{tz_name}" not necessary '
                          f'as already in timezone "{tz_name}".')
    return df


##############################################################################################################
# Functions that are not necessarily associated with the generation of samples
def get_units(datetimes: list[datetime | pd.Timestamp], tm_unit: str = 'day'):
    """Converts each datetime into an integer or float in the specified temporal units."""
    date_min = pd.to_datetime('1970-01-01')  # set minimum date (does not matter when but 1970-01-01 is conventional)
    if tm_unit in ['year']:
        units = [date.year for date in datetimes]  # year (plain and simple)
    elif tm_unit in ['month']:
        units = [(date.year - 1970) * 12 + date.month for date in datetimes]  # number of months since 1970-01-01
    elif tm_unit in ['moy']:
        units = [date.month for date in datetimes]  # month of the year (1-12)
    elif tm_unit in ['day']:
        units = [(date - date_min).days for date in datetimes]  # number of days since 1970-01-01
    elif tm_unit in ['doy']:
        units = [min(365, int(date.strftime('%j'))) for date in datetimes]  # day of the year (1-365)
    elif tm_unit in ['hour']:
        units = [(date - date_min).days * 24 + (date - date_min).seconds / 3600 for date in datetimes]  # hours
    else:
        raise ValueError
    return units


def get_dfb(trackpoints: gpd.GeoDataFrame, grouper: list[str] = None, grouper_name: str = None) -> gpd.GeoDataFrame:
    """Gets the distance from the beginning of a line for a series of points."""
    name = 'dfb' + grouper_name if grouper_name else 'dfb'
    if name not in trackpoints:  # if DFB has not already been calculated
        trackpoints['section_beg'] = ~trackpoints['section_id'].eq(trackpoints['section_id'].shift())  # section begins
        trackpoints['dfp'] = trackpoints.distance(trackpoints.shift())  # distance to trackpoint from previous (DFP)
        trackpoints.loc[trackpoints['section_beg'], 'dfp'] = 0  # for first trackpoint, reset DFP
        if isinstance(grouper, list):
            trackpoints[name] = trackpoints.groupby(grouper)['dfp'].cumsum()  # sum DFPs by grouper to get DFB
        else:
            trackpoints[name] = trackpoints['dfp'].cumsum()  # sum DFPs
        remove_cols(trackpoints, ['section_beg', 'dfp'])  # remove unnecessary
    return trackpoints
