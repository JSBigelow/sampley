# Various little functions for performing basic operations and checking

##############################################################################################################
# Imports
from datetime import datetime, timezone
import geopandas as gpd
import numpy as np
import pandas as pd
from pandas._libs.tslibs.parsing import DateParseError
import pyproj.exceptions
from pyproj import CRS
import pyogrio.errors
import pytz
import random
from shapely import wkt
import typing
import os


##############################################################################################################
# Checkers

# columns
def check_cols(df: pd.DataFrame, cols: str | list[str]):
    cols = [cols] if isinstance(cols, str) else cols
    for col in cols:
        if col not in df:
            raise Exception('\n\n____________________'
                            f'\nKeyError: column \'{col}\' not found in DataFrame.'
                            '\n____________________')


# options and datatypes
def check_opt(par: str, opt: str, opts: list[str]):
    if opt.lower() not in opts:
        raise Exception(
            '\n\n____________________'
            f'\nError: invalid value for \'{par}\'. The value is \'{opt}\'.'
            f'\nPlease ensure that the value for \'{par}\' is one of:'
            f'\n  {'\n  '.join([f'\'{opt}\'' for opt in opts])}'
            '\n____________________')


# datatypes
def check_dtype(par: str, obj, dtypes, none_allowed: bool = False):
    check = False
    if obj is None:
        if none_allowed:
            check = True
    else:
        dtypes = [dtypes] if not isinstance(dtypes, list) else dtypes
        for dtype in dtypes:
            if isinstance(obj, dtype):
                check = True

    if not check:
        raise TypeError(
            '\n\n____________________'
            f'\nTypeError: invalid datatype for the value of \'{par}\'. The datatype is {type(obj).__name__}.'
            f'\nPlease ensure that the value of \'{par}\' is of one of the following types:'
            f'\n  {'\n  '.join([dtype.__name__ for dtype in dtypes])}'
            '\n____________________')


# CRS
def check_crs(par: str, crs: str | int | pyproj.crs.crs.CRS, none_allowed: bool = False, projected: bool = False):
    check_dtype(par='crs', obj=crs, dtypes=[str, int, pyproj.crs.crs.CRS], none_allowed=none_allowed)
    if none_allowed and crs is None:
        crs_name = 'None'
        check = True
    else:
        if isinstance(crs, pyproj.crs.crs.CRS):
            crs_name = '\'' + str(crs) + '\''
            check = True
        elif isinstance(crs, (str, int)):
            crs_name = '\'' + crs + '\'' if isinstance(crs, str) else crs
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
            f'\nCRSError: Invalid value for \'{par}\' resulting in invalid CRS.'
            f'\n  The value for \'{par}\' is {crs_name}'
            f'\nPlease ensure that the value for \'{par}\' is one of:'
            '\n  a pyproj.crs.crs.CRS'
            '\n  a string or integer in a format accepted by pyproj.CRS.from_user_input(), for example:'
            '\n    \'EPSG:4326\''
            '\n    \'epsg:4326\''
            '\n    4326'
            '\n____________________')
    if projected:
        if not crs.is_projected:
            raise Exception('\n\n____________________'
                            '\nCRSError: CRS is not projected.'
                            f'\n  The value for \'{par}\' is {crs_name}'
                            f'\nPlease ensure that the value for \'{par}\' is a projected CRS.'
                            '\n____________________')


# timezone
tzs = (list(pytz.all_timezones) +
       [f'UTC-{str(i).zfill(2)}:00' for i in range(0, 24)] +
       [f'UTC-{str(i).zfill(2)}:30' for i in range(0, 24)] +
       [f'UTC+{str(i).zfill(2)}:00' for i in range(0, 24)] +
       [f'UTC+{str(i).zfill(2)}:30' for i in range(0, 24)])


def check_tz(par: str, tz: str | timezone | pytz.BaseTzInfo, none_allowed: bool = False):
    check_dtype(par='tz', obj=tz, dtypes=[str, timezone, pytz.BaseTzInfo], none_allowed=none_allowed)
    if none_allowed and tz is None:
        tz_name = 'None'
        check = True
    else:
        if isinstance(tz, (timezone, pytz.BaseTzInfo)):
            tz_name = str(tz)
            check = True
        elif isinstance(tz, str):
            tz_name = '\'' + tz + '\''
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
            f'\nTimezoneError: invalid value for \'{par}\' resulting in invalid timezone.'
            f'\n  The value for \'{par}\' is {tz_name}'
            f'\nPlease ensure that the value for \'{par}\' is one of:'
            '\n  a datetime.timezone'
            '\n  a string of a timezone name accepted by pytz (run pytz.all_timezones to see all options), for example:'
            '\n    \'Europe/Vilnius\''
            '\n    \'Pacific/Marquesas\''
            '\n  a string of a UTC code, for example:'
            '\n    \'UTC+02:00\''
            '\n    \'UTC-09:30\'')


##############################################################################################################
# Operations
def open_file(filepath: str) -> pd.DataFrame | gpd.GeoDataFrame:
    print('Opening file...')
    input_ext = os.path.splitext(filepath)[1].lower()
    try:
        if input_ext == '.csv':
            df = pd.read_csv(filepath)
        elif input_ext == '.xlsx':
            df = pd.read_excel(filepath)
        elif input_ext in ['.gpkg', '.shp']:
            df = gpd.read_file(filepath)
        else:
            raise TypeError('\n\n____________________'
                            '\nTypeError: the file is not of a valid type.'
                            f'\n  The file extension is {input_ext}'
                            '\nThe input file must be one of the following:'
                            '\n  .csv - CSV (for DataPoints only)'
                            '\n  .xlsx - Excel (for DataPoints only)'
                            '\n  .gpkg - GeoPackage (for DataPoints and Sections)'
                            '\n  .shp - ShapeFile (for DataPoints and Sections)'
                            '\n____________________')
        print('Success: file successfully input.')
        return df
    except (FileNotFoundError, pyogrio.errors.DataSourceError):
        raise FileNotFoundError('\n\n____________________'
                                '\nFileNotFoundError: file not found.'
                                '\nPlease check the filepath:'
                                f'\n  {filepath}'
                                '\n____________________')


def remove_cols(df: pd.DataFrame, cols: str | list[str]):
    cols = [cols] if isinstance(cols, str) else cols
    for col in cols:
        if col in df:
            df.drop(col, axis=1, inplace=True)


def parse_xy(df: pd.DataFrame, x_col: str, y_col: str, crs: str | int | pyproj.crs.crs.CRS) -> gpd.GeoDataFrame:
    print('Parsing x and y (lon/lat) coordinates...')
    try:
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[x_col], df[y_col]), crs=crs)
        gdf.drop([x_col, y_col], axis=1, inplace=True)
    except ValueError:
        raise ValueError('\n\n____________________'
                         f'\nValueError: the columns \'{x_col}\' and/or \'{y_col}\' contain one or more invalid values.'
                         f'\nPlease check the values in the columns \'{x_col}\' and \'{y_col}\'.'
                         '\n____________________')
    print('Success: x and y (lon/lat) coordinates successfully parsed.')
    return gdf


def parse_geoms(df: pd.DataFrame, geometry_col: str, crs: str | int | pyproj.crs.crs.CRS) -> gpd.GeoDataFrame:
    print('Parsing geometries...')
    try:
        df[geometry_col] = df[geometry_col].apply(wkt.loads)
    except TypeError:
        raise TypeError('\n\n____________________'
                        f'\nTypeError: the column \'{geometry_col}\' contains values that are not shapely geometries.'
                        f'\nPlease check the values in the column \'{geometry_col}\'.'
                        '\n____________________')
    gdf = gpd.GeoDataFrame(df, geometry=geometry_col, crs=crs)
    gdf.rename(columns={geometry_col: 'geometry'}, inplace=True)  # rename geometry column
    print('Success: geometries successfully parsed.')
    return gdf


def reproject_crs(gdf: gpd.GeoSeries | gpd.GeoDataFrame, crs_target: str | int | pyproj.crs.crs.CRS):
    if crs_target is not None:
        print('Reprojecting CRS...')
        crs_name = '\'' + crs_target + '\'' if isinstance(crs_target, str) else (
                '\'' + str(crs_target) + '\'') if isinstance(crs_target, pyproj.crs.crs.CRS) else crs_target
        if crs_target != gdf.crs:
            gdf = gdf.to_crs(crs_target)
            print(f'Success: reprojected to CRS {crs_name}')
        else:
            print(f'Note: reprojection to CRS {crs_name} not necessary as already in CRS {crs_name}.')
    return gdf


def parse_dts(df: pd.DataFrame, datetime_col: str, datetime_format: str | None = None, tz: str | timezone | pytz.BaseTzInfo | None = None):
    print('Parsing datetimes...')
    try:
        df[datetime_col] = df[datetime_col].astype(str)
        df[datetime_col] = pd.to_datetime(df[datetime_col], format=datetime_format)
        print(f'Success: the column \'{datetime_col}\' successfully reformatted to datetimes.')
    except DateParseError:
        raise DateParseError(
            '\n\n____________________'
            f'\nDateParseError: the column \'{datetime_col}\' contains one or more invalid values.'
            f'\nPlease ensure that the values in the column \'{datetime_col}\' are '
            'strings in a format that can be recognised as a datetime, for example:'
            '\n  \'2025-03-06 15:19:42\''
            '\n____________________')
    except ValueError:
        raise ValueError(
            '\n\n____________________'
            f'\nValueError: the datetime format \'{datetime_format}\' is invalid.'
            '\n____________________')
    try:
        tz_col = str(df[datetime_col].dtype.tz)  # get timezone if there is one
        print(f'Note: the timezone of column \'{datetime_col}\' is already set to \'{tz_col}\'.')
        if tz is not None:  # if there is already a timezone and a timezone is specified...
            if str(tz_col) != str(tz):  # ...and the two timezones are different, print a warning...
                print(f'Warning: the timezone of column \'{datetime_col}\' is not equal to the specified timezone. '
                      f'\n  column timezone: {str(tz_col)}'
                      f'\n  specified timezone: {str(tz)}'                      
                      f'\nThe column \'{datetime_col}\' will be converted to the specified timezone:')
                df[datetime_col] = df[datetime_col].dt.tz_convert(tz)
    except AttributeError:  # else, if there is no timezone...
        if tz is not None:
            df[datetime_col] = df[datetime_col].dt.tz_localize(tz)  # ...set timezone
            print(f'Success: the timezone of column \'{datetime_col}\' successfully set to \'{tz}\'.')
        else:
            print(f'Note: the timezone of column \'{datetime_col}\' was not set as no timezone was specified.')
    return df


def convert_tz(df: pd.DataFrame, datetime_col: str, tz_target: str | timezone | pytz.BaseTzInfo | None):
    if tz_target is not None:
        print('Converting timezone...')
        tz_name = str(tz_target) if isinstance(tz_target, (timezone, pytz.BaseTzInfo)) else tz_target
        try:
            tz_current = str(df[datetime_col].dtype.tz)
        except AttributeError:
            raise AttributeError(
                '\n\n____________________'
                f'\nAttributeError: the column \'{datetime_col}\' does not have a timezone.'
                f'\nPlease set the timezone before attempting to convert.'
                f'\nNote: tz_input must be set if setting tz_working.'
                '\n____________________')
        if str(tz_target) != str(tz_current):
            df[datetime_col] = df[datetime_col].dt.tz_convert(tz_target)
            print(f'Success: column \'{datetime_col}\' converted to timezone \'{tz_name}\'')
        else:
            print(f'Note: conversion of column \'{datetime_col}\' to timezone \'{tz_name}\' is not necessary '
                  f'as it is already in timezone \'{tz_name}\'.')
    return df


##############################################################################################################
# Little functions for resampling
def c_pa(c): return 1 if np.nansum(list(c)) > 0 else 0  # convert count (of individuals or sightings) to presence-absence
def count_nz(c): return len([ci for ci in list(c) if ci > 0])  # convert count of individuals to count of sightings


##############################################################################################################
# Functions that are not necessarily associated with the generation of samples
#   (i.e., convert each datetime into an integer or float in the specified temporal units)
def get_units(datetimes: list[datetime | pd.Timestamp], tm_unit: str = 'day'):
    date_min = pd.to_datetime('1970-01-01')  # set minimum date (does not matter when but 1970-01-01 is conventional)
    if tm_unit in ['year']:
        units = [date.year for date in datetimes]  # year
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
    name = 'dfb' + grouper_name if grouper_name else 'dfb'
    if name not in trackpoints:
        trackpoints['section_beg'] = ~trackpoints['section_id'].eq(trackpoints['section_id'].shift())  # section begins
        trackpoints['dfp'] = trackpoints.distance(trackpoints.shift())  # distance to trackpoint from previous (DFP)
        trackpoints.loc[trackpoints['section_beg'], 'dfp'] = 0  # for first trackpoint in section, reset DFP
        if isinstance(grouper, list):
            trackpoints[name] = trackpoints.groupby(grouper)['dfp'].cumsum()  # sum DFPs by section to get DFBSEC
        else:
            trackpoints[name] = trackpoints['dfp'].cumsum()  # sum DFPs
        remove_cols(trackpoints, ['section_beg', 'dfp'])  # remove unnecessary
    return trackpoints


def generate_dfls(number: int | float, esw: int | float, interval: int | float, dfunc: typing.Callable | int | float)\
        -> list[int | float]:
    intervals = np.arange(0, esw + interval, interval)  # distances from the line at set intervals
    probabilities = np.full(len(intervals), dfunc) \
        if isinstance(dfunc, int | float) else dfunc(intervals)  # probabilities for the distances at set intervals
    dfls = random.choices(intervals, probabilities, k=number)  # randomly sample a selection of distances from the line
    return dfls


def calculate_area_udf(esw: int | float, interval: int | float, dfunc: typing.Callable | int | float) -> int | float:
    intervals = np.arange(0, esw + interval, interval)  # distances from the line at set intervals
    probabilities = np.full(len(intervals), dfunc) if isinstance(dfunc, int | float) else dfunc(intervals)  # calculate probabilities for the distances from the line at set intervals
    area_udf = sum(probabilities[1:-1]*interval) + sum(probabilities[[0, -1]]*(interval/2))
    return area_udf

