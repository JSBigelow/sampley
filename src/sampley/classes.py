# Classes

##############################################################################################################
# Imports
import matplotlib.pyplot as plt
from thinst import *

from .functions import *


##############################################################################################################
# Stage 1: Data containers
class DataPoints:
    def __init__(self, datapoints, name, parameters):
        self.datapoints = datapoints
        self.name = name
        self.parameters = parameters

    @classmethod
    def from_file(
            cls,
            filepath: str,
            x_col: str = 'lon',
            y_col: str = 'lat',
            geometry_col: str = None,
            crs_import: str | int | pyproj.crs.crs.CRS = None,
            crs_working: str | int | pyproj.crs.crs.CRS = None,
            datetime_col: str | None = None,
            datetime_format: str = None,
            tz_import: str | timezone | pytz.BaseTzInfo | None = None,
            tz_working: str | timezone | pytz.BaseTzInfo | None = None,
            datapoint_id_col: str = None,
            section_id_col: str = None):

        """Make a DataPoints object from a GPKG, SHP, CSV, or XLSX file.

        Takes a GPKG, SHP, CSV, or XLSX file that contains the datapoints and reformats it for subsequent processing by:
         renaming and reordering essential columns; if necessary, reprojecting it to a projected CRS; assigning each
         datapoint a unique ID.
        If loading data from a CSV or XLSX, locations of datapoints must be stored in one of two ways:
          two columns (x_col and y_col) containing x and y (e.g., longitude and latitude) coordinates
          one column (geometry_col) containing points as WKT geometry objects
        Parameters:
            filepath : str
                The path to the file containing the datapoints. Ensure that filepath includes the filename and the extension.
            x_col : str, optional, default 'lon'
                If importing a CSV or XLSX with x and y coordinates, the name of the column containing the x coordinate
                 (e.g., longitude) of each datapoint.
            y_col : str, optional, default 'lat'
                If importing a CSV or XLSX with x and y coordinates, the name of the column containing the y coordinate
                 (e.g., latitude) of each datapoint.
            geometry_col : str, optional, default None
                If importing a CSV or XLSX with points as WKT geometry objects, the name of the column containing the WKT
                 geometry objects.
            crs_import : str | int | pyproj.CRS, optional, default None
                If importing a CSV or XLSX, the CRS of the coordinates/geometries. The CRS must be either: a pyproj.CRS; a
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
            tz_import : str | timezone | pytz.BaseTzInfo, optional, default None
                If datetime_col is specified, the timezone of the datetimes contained within the column. The timezone must
                 be either: a datetime.timezone; a string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a
                 timezone name accepted by pytz (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’).
            tz_working : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to be used for the subsequent processing. The timezone must be either: a datetime.timezone; a
                 string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a timezone name accepted by pytz
                 (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’). Note that tz_import must be specified if tz_working is
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
            DataPoints
                Returns a DataPoints object with three attributes: name, parameters, and datapoints.
        """

        datapoints = datapoints_from_file(
            filepath=filepath,
            x_col=x_col,
            y_col=y_col,
            geometry_col=geometry_col,
            crs_import=crs_import,
            crs_working=crs_working,
            datetime_col=datetime_col,
            datetime_format=datetime_format,
            tz_import=tz_import,
            tz_working=tz_working,
            datapoint_id_col=datapoint_id_col,
            section_id_col=section_id_col)
        data_cols = ', '.join([c for c in datapoints if c not in ['datapoint_id', 'geometry', 'datetime']])

        try:
            tz = str(datapoints['datetime'].dtype.tz)
        except AttributeError:
            tz = None

        return cls(
            datapoints=datapoints,
            name='datapoints-' + os.path.splitext(os.path.basename(filepath))[0],
            parameters={
                'datapoints_filepath': filepath,
                'datapoints_crs': str(datapoints.crs),
                'datapoints_tz': tz,
                'datapoints_data_cols': data_cols})

    @classmethod
    def open(cls, folder: str, basename: str,
             crs_working: str | int | pyproj.crs.crs.CRS = None,
             tz_working: str | timezone | pytz.BaseTzInfo | None = None):

        """Open a saved Sections object.

        Open a DataPoints object that has previously been saved with DataPoints.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the DataPoints object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
            tz_working : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to be used for the subsequent processing. The timezone must be either: a datetime.timezone;
                 a string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a timezone name accepted by
                 pytz (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        datapoints = open_file(folder + basename + '.gpkg')
        datapoints = datapoints[['datapoint_id', 'geometry', 'datetime'] +
                                            [c for c in datapoints if c not in
                                             ['datapoint_id', 'geometry', 'datetime']]]
        try:
            parameters = open_file(folder + basename + '-parameters.csv')
            parameters = parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            datapoints = reproject_crs(gdf=datapoints, crs_target=crs_working)  # reproject
            parameters['datapoints_crs'] = str(crs_working)  # update parameter

        if isinstance(datapoints['datetime'].iloc[0], str):
            parse_dts(datapoints, 'datetime')
            if tz_working is not None:  # if TZ provided
                check_tz(par='tz_working', tz=tz_working)
                datapoints = convert_tz(df=datapoints, datetime_cols='datetime', tz_target=tz_working)  # convert
                parameters['datapoints_tz'] = str(tz_working)  # update parameter

        return cls(datapoints=datapoints, name=basename, parameters=parameters)

    def plot(self, sections=None):

        """Plot the datapoints.

        Makes a basic matplotlib plot of the datapoints in greyscale.

        Parameters:
        sections : Sections, optional, default None
            Optionally, a Sections object with sections to be plotted with the datapoints.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        datapoints_plot(ax, self.datapoints)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None

    def save(self, folder,
             crs_export: str | int | pyproj.crs.crs.CRS = None,
             tz_export: str | timezone | pytz.BaseTzInfo = None):

        """Save the datapoints.

        Saves the datapoints GeoDataFrame as a GPKG. The name of the saved file will be the name of the DataPoints
         object. Additionally, the parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the datapoints to before saving (only reprojects the datapoints that are saved and
                 not the DataPoints object).
            tz_export : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to convert the datapoints to before saving (only converts the datapoints that are saved and
                 not the DataPoints object).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        datapoints = self.datapoints.copy()  # copy datapoints GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if CRS provided
            check_crs(par='crs_export', crs=crs_export)
            datapoints = reproject_crs(gdf=datapoints, crs_target=crs_export)  # reproject
            parameters['datapoints_crs'] = str(crs_export)  # update parameter
        if tz_export is not None:  # if TZ provided
            check_tz(par='tz_export', tz=tz_export)
            datapoints = convert_tz(df=datapoints, datetime_cols='datetime', tz_target=tz_export)  # convert
            parameters['datapoints_tz'] = str(tz_export)  # update parameter
        datapoints['datetime'] = datapoints['datetime'].apply(  # convert datetime to string if datetime
            lambda dt: str(dt) if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        datapoints.to_file(folder + '/' + self.name + '.gpkg')  # exported datapoints as GPKG

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


class Sections:
    def __init__(self, sections, name, parameters):
        self.sections = sections
        self.name = name
        self.parameters = parameters

    @classmethod
    def from_file(
            cls,
            filepath: str,
            crs_working: str | int | pyproj.crs.crs.CRS = None,
            datetime_col: str | None = None,
            datetime_format: str = None,
            tz_import: str | timezone | pytz.BaseTzInfo | None = None,
            tz_working: str | timezone | pytz.BaseTzInfo | None = None,
            section_id_col: str | None = None):

        """Make a Sections object from a GPKG or SHP file.

        Takes a GPKG or SHP file that contains the sections as shapely.LineStrings and reformats it for subsequent
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
            tz_import : str | timezone | pytz.BaseTzInfo, optional, default None
                If datetime_col is specified, the timezone of the datetimes contained within the column. The timezone must
                 be either: a datetime.timezone; a string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a
                 timezone name accepted by pytz (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’).
            tz_working : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to be used for the subsequent processing. The timezone must be either: a datetime.timezone; a
                 string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a timezone name accepted by pytz
                 (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’). Note that tz_import must be specified if tz_working is
                 specified.
            section_id_col : str, optional, default None
                Optionally, the name of the column containing the section IDs. Each individual section must have its own
                 unique ID. It is recommended that section IDs be codes consisting of letters and numbers and, optionally,
                 underscores (e.g., ‘s001‘ or 20250710_s01‘).
        Returns:
            Sections
                Returns a Sections object with three attributes: name, parameters, and sections.
        """

        sections = sections_from_file(
            filepath=filepath,
            crs_working=crs_working,
            datetime_col=datetime_col,
            datetime_format=datetime_format,
            tz_import=tz_import,
            tz_working=tz_working,
            section_id_col=section_id_col)

        try:
            tz = str(sections['datetime'].dtype.tz)
        except AttributeError:
            tz = None

        return cls(
            sections=sections,
            name='sections-' + os.path.splitext(os.path.basename(filepath))[0],
            parameters={
                'sections_filepath': filepath,
                'sections_crs': str(sections.crs),
                'sections_tz': tz})

    @classmethod
    def from_datapoints(
            cls,
            datapoints: DataPoints,
            cols: dict | None = None,
            sortby: str | list[str] = None):

        """Make a Sections object from a DataPoints object.

        Takes a DataPoints object that contains sections as continuous series of Points and reformats it for subsequent
         processing by: converting each series of Points to a LineString; renaming and reordering essential columns. The
         CRS and timezone will be that of the DataPoints object.
        Note that, when making the DataPoints object, it is necessary to specify section_id_col. Please see the
         documentation for Sections or for the section_id_col parameter under DataPoints.from_file for more information on 
         section IDs and how they should be formatted.
        Note that Sections.from_datapoints should only be used with continuous datapoints and not with sporadic datapoints
         (please see under DataPoints for details on continuous and sporadic datapoints).

        Parameters:
            datapoints : DataPoints
                The DataPoints object that contains sections as series of points.
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

        Returns:
            Sections
                Returns a Sections object with three attributes: name, parameters, and sections.
        """
        
        if 'section_id' not in datapoints.datapoints:
            raise Exception('\n\n____________________'
                            f'\nKeyError: the datapoints GeoDataFrame does not have a section ID column.'
                            f'\nPlease ensure that "section_id_col" is specified when making the DataPoints object'
                            f' with DataPoints.from_file().'
                            '\n____________________')

        sections = sections_from_datapoints(
            datapoints=datapoints.datapoints,
            section_id_col='section_id',
            cols=cols,
            sortby=sortby)

        return cls(
            sections=sections,
            name='sections-' + datapoints.name[11:],
            parameters={
                'sections_filepath': datapoints.parameters['datapoints_filepath'] + ' (via datapoints)' if 'datapoints_filepath' in datapoints.parameters else None,
                'sections_crs': datapoints.parameters['datapoints_crs'] if 'datapoints_crs' in datapoints.parameters else None,
                'sections_tz': datapoints.parameters['datapoints_tz'] if 'datapoints_tz' in datapoints.parameters else None})

    @classmethod
    def open(cls, folder: str, basename: str,
             crs_working: str | int | pyproj.crs.crs.CRS = None,
             tz_working: str | timezone | pytz.BaseTzInfo | None = None):

        """Open a saved Sections object.

        Open a Sections object that has previously been saved with Sections.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the Sections object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
            tz_working : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to be used for the subsequent processing. The timezone must be either: a datetime.timezone;
                 a string of a UTC code (e.g., ‘UTC+02:00’, ‘UTC-09:30’); or a string of a timezone name accepted by
                 pytz (e.g., ‘Europe/Vilnius’ or ‘Pacific/Marquesas’).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        sections = open_file(folder + basename + '.gpkg')
        sections = sections[['section_id', 'geometry', 'datetime'] +
                                        [c for c in sections if c not in ['section_id', 'geometry', 'datetime']]]
        try:
            parameters = open_file(folder + basename + '-parameters.csv')
            parameters = parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            sections = reproject_crs(gdf=sections, crs_target=crs_working)  # reproject
            parameters['sections_crs'] = str(crs_working)  # update parameter

        if isinstance(sections['datetime'].iloc[0], str):
            parse_dts(sections, 'datetime')
            if tz_working is not None:  # if TZ provided
                check_tz(par='tz_working', tz=tz_working)
                sections = convert_tz(df=sections, datetime_cols='datetime', tz_target=tz_working)  # convert
                parameters['sections_tz'] = str(tz_working)  # update parameter

        return cls(sections=sections, name=basename, parameters=parameters)

    def plot(self, datapoints=None):

        """Plot the sections.

        Makes a basic matplotlib plot of the sections in greyscale.

        Parameters:
            datapoints : DataPoints, optional, default None
                Optionally, a DataPoints object with datapoints to be plotted with the sections.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        sections_plot(ax, self.sections)
        datapoints_plot(ax, datapoints.datapoints) if isinstance(datapoints, DataPoints) else None

    def save(self, folder,
             crs_export: str | int | pyproj.crs.crs.CRS = None,
             tz_export: str | timezone | pytz.BaseTzInfo = None):

        """Save the sections.

        Saves the sections GeoDataFrame as a GPKG. The name of the saved file will be the name of the Sections object.
         Additionally, the parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the sections to before saving (only reprojects the sections that are saved and not
                 the Sections object).
            tz_export : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to convert the sections to before saving (only converts the sections that are saved and not
                 the Sections object).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        sections = self.sections.copy()  # copy sections GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if CRS provided
            check_crs(par='crs_export', crs=crs_export)
            sections = reproject_crs(gdf=sections, crs_target=crs_export)  # reproject
            parameters['sections_crs'] = str(crs_export)  # update parameter
        if tz_export is not None:  # if TZ provided
            check_tz(par='tz_export', tz=tz_export)
            sections = convert_tz(df=sections, datetime_cols='datetime', tz_target=tz_export)  # convert
            parameters['sections_tz'] = str(tz_export)  # update parameter
        sections['datetime'] = sections['datetime'].apply(  # convert datetime to string if datetime
            lambda dt: str(dt) if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        sections.to_file(folder + '/' + self.name + '.gpkg')  # export sections as GPKG

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


##############################################################################################################
# Stage 2: Delimiters
class Periods:
    def __init__(self, periods, name, parameters):
        self.periods = periods
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of periods_delimit()
            cls,
            extent: Sections | DataPoints | pd.DataFrame | tuple[list, str],
            num: int | float,
            unit: str):

        """Delimit temporal periods of a set number of units.

        From a given extent, number of units, and type of units, delimit temporal periods of regular length, e.g.,
         8 days, 2 months, or 1 year.
        Temporal periods of irregular length (e.g., seasons) should be predefined and contained within a column of the
         imported data.

        Parameters:
            extent : Sections | DataPoints | pandas.DataFrame | tuple[list, str]
                An object detailing the temporal extent over which the periods will be limited. Must be one of:
                    a Sections object whose sections GeoDataFrame has a 'datetime' column
                    a DataPoints object whose datapoints GeoDataFrame has a 'datetime' column
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

        Returns:
            Periods
                Returns a Periods object with three attributes: name, parameters, and periods.
        """
        check_dtype(par='extent', obj=extent, dtypes=[Sections, DataPoints, pd.DataFrame, tuple])

        if isinstance(extent, Sections):
            source = 'Sections - ' + extent.name
            extent = extent.sections
        elif isinstance(extent, DataPoints):
            source = 'DataPoints - ' + extent.name
            extent = extent.datapoints
        elif isinstance(extent, gpd.GeoDataFrame):
            source = 'DataFrame'
        elif isinstance(extent, tuple):
            source = 'tuple'
        else:
            raise TypeError

        periods = periods_delimit(
            extent=extent,
            num=num,
            unit=unit,
            datetime_col='datetime')

        try:
            tz = str(periods['date_beg'].dtype.tz)
        except AttributeError:
            tz = None

        return cls(
            periods=periods,
            name='periods-' + str(int(num)) + unit[0],
            parameters={
                'periods_tz': tz,
                'periods_extent': periods['date_beg'].min().strftime('%Y-%m-%d') + '-' + periods['date_end'].max().strftime('%Y-%m-%d'),
                'periods_extent_source': source,
                'periods_number': num,
                'periods_unit': unit})

    @classmethod
    def open(cls, folder: str, basename: str):

        """Open a saved Periods object.

        Open a Periods object that has previously been saved with Periods.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the Periods object that was saved (without the extension).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        import_periods = open_file(folder + basename + '.csv')
        import_periods['date_beg'] = pd.to_datetime(import_periods['date_beg'])
        import_periods['date_mid'] = pd.to_datetime(import_periods['date_mid'])
        import_periods['date_end'] = pd.to_datetime(import_periods['date_end'])

        try:
            import_parameters = open_file(folder + basename + '-parameters.csv')
            import_parameters = import_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            import_parameters = {}

        return cls(periods=import_periods, name=basename, parameters=import_parameters)

    def save(self, folder: str):

        """Save the periods.

        Saves the periods DataFrame as a CSV. The name of the saved file will be the name of the Periods object.
         Additionally, the parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        periods = self.periods.copy()  # copy dataframe
        parameters = self.parameters.copy()  # copy parameters

        for col in ['date_beg', 'date_mid', 'date_end']:  # for each potential datetime col...
            periods[col] = periods[col].apply(  # convert datetime to string if there is datetime
                lambda dt: str(dt) if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        periods.to_csv(folder + '/' + self.name + '.csv', index=False)  # export to CSV

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


class Cells:
    def __init__(self, cells, name, parameters):
        self.cells = cells
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of cells_delimit()
            cls,
            extent: Sections | DataPoints | gpd.GeoDataFrame | tuple[list, str],
            var: str,
            side: int | float,
            buffer: int | float = None):

        """Delimit grid cells.

        From a given extent, variation, and side length, delimit rectangular or hexagonal grid cells of a regular size.

        Parameters:
            extent : Sections | DataPoints | geopandas.GeoDataFrame | tuple[list, str]
                An object detailing the spatial extent over which the periods will be limited. Must be one of:
                    a Sections object
                    a DataPoints object
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
            Cells
                Returns a Cells object with three attributes: name, parameters, and cells.
        """

        source = 'Sections - ' + extent.name if isinstance(extent, Sections) \
            else 'DataPoints - ' + extent.name if isinstance(extent, DataPoints) \
            else 'GeoDataFrame' if isinstance(extent, gpd.GeoDataFrame) \
            else 'tuple'
        extent = extent.sections if isinstance(extent, Sections) \
            else extent.datapoints if isinstance(extent, DataPoints) \
            else extent

        cells = cells_delimit(
            extent=extent,
            var=var,
            side=side,
            buffer=buffer)

        crs = cells.crs
        unit = crs.axis_info[0].unit_name
        return cls(
            cells=cells,
            name='cells-' + var[0] + str(side) + unit[0],
            parameters={
                'cells_crs': str(crs),
                'cells_extent': ', '.join(str(bound) for bound in list(cells.total_bounds)),
                'cells_extent_source': source,
                'cells_var': var,
                'cells_side': side,
                'cells_unit': unit,
                'cells_buffer': buffer})

    @classmethod
    def open(cls, folder: str, basename: str, crs_working: str | int | pyproj.crs.crs.CRS = None):

        """Open a saved Cells object.

        Open a Cells object that has previously been saved with Cells.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the Cells object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        polygons = open_file(folder + basename + '-polygons.gpkg')
        polygons.rename_geometry('polygon', inplace=True)
        try:
            centroids = open_file(folder + basename + '-centroids.gpkg')
            centroids.rename_geometry('centroid', inplace=True)
            import_cells = pd.merge(polygons, centroids, on='cell_id')
        except FileNotFoundError:
            print('Warning: centroids not found. Cells object will be made without centroids.')
            import_cells = polygons
            import_cells['centroid'] = None

        try:
            import_parameters = open_file(folder + basename + '-parameters.csv')
            import_parameters = import_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            import_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            import_cells = reproject_crs(gdf=import_cells, crs_target=crs_working, additional='centroid')  # reproject
            import_parameters['cells_crs'] = str(crs_working)  # update parameter

        return cls(cells=import_cells, name=basename, parameters=import_parameters)

    def plot(self, datapoints: DataPoints = None, sections: Sections = None):

        """Plot the cells.

        Makes a basic matplotlib plot of the cells.

        Parameters:
            datapoints : DataPoints, optional, default None
                Optionally, a DataPoints object with datapoints to be plotted with the cells.
            sections : Sections, optional, default None
                Optionally, a Sections object with sections to be plotted with the cells.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        cells_plot(ax, self.cells)
        datapoints_plot(ax, datapoints.datapoints) if isinstance(datapoints, DataPoints) else None
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None

    def save(self, folder: str, crs_export: str | int | pyproj.crs.crs.CRS = None):

        """Save the cells.

        Saves the cells GeoDataFrame as two GPKGs: one of the polygons and one of the centroids. The names of the saved
         files will be the name of the Cells object plus '-polygons' and '-centroids', respectively. Additionally, the
         parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the cells to before saving (only reprojects the cells that are saved and not the
                 Cells object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        cells = self.cells.copy()  # copy cells GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if CRS provided
            check_crs(par='crs_export', crs=crs_export)
            cells = reproject_crs(gdf=cells, crs_target=crs_export, additional='centroid')  # reproject
            parameters['cells_crs'] = str(crs_export)  # update parameter

        cells[['cell_id', 'polygon']].to_file(folder + '/' + self.name + '-polygons.gpkg')  # export polygons
        cells[['cell_id', 'centroid']].to_file(folder + '/' + self.name + '-centroids.gpkg')  # export centroids

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


class Segments:
    def __init__(self, segments, name, parameters):
        self.segments = segments
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of segments_delimit()
            cls,
            sections: Sections,
            var: str,
            target: int | float,
            rand: bool = False):

        """Delimit segments.

        With a given variation and target length, cut sections into segments.
        Segments can be made with any one of three variations: the simple, joining, and redistribution variations. For
         all three variations, a target length is set. The variations differ in how they deal with the remainder — the
         length inevitably left over after dividing a section by the target length. Additionally, for the simple and
         joining variations, the location of the remainder / joined segment can be randomised (rather than always being
         at the end).

        Parameters:
        sections : Sections
            The Sections object containing the sections from which the segments will be cut.
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
            Segments
                Returns a Segments object with three attributes: name, parameters, and segments.
        """

        segments = segments_delimit(
            sections=sections.sections,
            var=var,
            target=target,
            rand=rand)

        crs = segments.crs
        unit = crs.axis_info[0].unit_name
        return cls(
            segments=segments,
            name='segments-' + var[0] + str(target) + unit[0],
            parameters={
                'sections_name': sections.name,
                'segments_crs': str(crs),
                'segments_var': var,
                'segments_rand': rand,
                'segments_target': target,
                'segments_unit': unit})

    @classmethod
    def open(cls, folder: str, basename: str, crs_working: str | int | pyproj.crs.crs.CRS = None):

        """Open a saved Segments object.

        Open a Segments object that has previously been saved with Segments.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the Segments object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        lines = open_file(folder + basename + '-lines.gpkg')
        lines.rename_geometry('line', inplace=True)
        try:
            midpoints = open_file(folder + basename + '-midpoints.gpkg')
            midpoints.rename_geometry('midpoint', inplace=True)
            import_segments = pd.merge(lines, midpoints, on='segment_id')
        except FileNotFoundError:
            print('Warning: midpoints not found. Segments object will be made without midpoints.')
            import_segments = lines
            import_segments['midpoint'] = None

        try:
            import_parameters = open_file(folder + basename + '-parameters.csv')
            import_parameters = import_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            import_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            import_segments = reproject_crs(gdf=import_segments, crs_target=crs_working, additional='midpoint')  # reproject
            import_parameters['cells_crs'] = str(crs_working)  # update parameter

        return cls(segments=import_segments, name=basename, parameters=import_parameters)

    def datetimes(self, datapoints: DataPoints):

        """Get datetimes for the beginning, middle, and end of each segment.

        Get a datetime value for the beginning, middle, and end of each segment. This is only applicable to segments
         that were made from sections that were made from continuous datapoints with Sections.from_datapoints.
        Additionally, it requires that those datapoints have datetime values.
        In the (likely) case that a segment begins/ends at some point between two datapoints, the begin/end time for
         that segment will be interpolated based on the distance from those two datapoints to the point at which the
         segment begins/ends assuming a constant speed.

        Parameters:
            datapoints : DataPoints
                The DataPoints object, containing datetimes, that was used to make the Sections object that was used
                 to make the Segments object.
        """

        self.segments = segments_datetimes(segments=self.segments, datapoints=datapoints.datapoints)

    def plot(self, sections: Sections = None, datapoints: DataPoints = None):

        """Plot the segments.

        Makes a basic matplotlib plot of the segments.

        Parameters:
            datapoints : DataPoints, optional, default None
                Optionally, a DataPoints object with datapoints to be plotted with the segments.
            sections : Sections, optional, default None
                Optionally, a Sections object with sections to be plotted with the segments.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        segments_plot(ax, self.segments)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None
        datapoints_plot(ax, datapoints.datapoints) if isinstance(datapoints, DataPoints) else None

    def save(self, folder: str, crs_export: str | int | pyproj.crs.crs.CRS = None):

        """Save the segments.

        Saves the segments GeoDataFrame as two GPKGs: one of the lines and one of the midpoints. The names of the saved
         files will be the name of the Segments object plus '-lines' and '-midpoints', respectively. Additionally, the
         parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the segments to before saving (only reprojects the segments that are saved and not
                 the Segments object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        segments = self.segments.copy()  # copy segments GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if CRS provided
            check_crs(par='crs_export', crs=crs_export)
            segments = reproject_crs(gdf=segments, crs_target=crs_export, additional='midpoint')  # reproject
            parameters['segments_crs'] = str(crs_export)  # update parameter

        segments[['segment_id', 'line']].to_file(folder + '/' + self.name + '-lines.gpkg')  # export lines
        segments[['segment_id', 'midpoint']].to_file(folder + '/' + self.name + '-midpoints.gpkg')  # export midpoints

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


class Presences:
    def __init__(self, presences, name, parameters):
        self.presences = presences
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of presences_delimit()
            cls,
            datapoints: DataPoints,
            presence_col: str = None,
            block: str = None):

        """Delimit presences.

        From a DataPoints object, make a Presences object.
        There are two options for the datapoints: all rows are presences, in which case there is no need to specify
         presence_col, or only some rows are presences, in which case presence_col must be specified.

        Parameters:
            datapoints :  DataPoints
                The DataPoints object that contains the presences.
            presence_col : str, optional, default None
                The name of the column containing the values that determine which points are presences (e.g., a column
                 containing a count of individuals). This column must contain only integers or floats. Only needs to be
                 specified if the DataPoints object includes points that are not presences.
            block : str, optional, default None
                Optionally, the name of a column that contains unique values to be used to separate the presences into
                 blocks. These blocks can then be used later when generating absences.

        Returns:
            Presences
                Returns a Presences object with three attributes: name, parameters and presences.
        """

        presences = presences_delimit(
            datapoints=datapoints.datapoints,
            presence_col=presence_col,
            block=block)

        crs = presences.crs
        return cls(
            presences=presences,
            name='presences-' + datapoints.name[11:],
            parameters={'presences_crs': str(crs)})

    @classmethod
    def open(cls, folder: str, basename: str, crs_working: str | int | pyproj.crs.crs.CRS = None):

        """Open a saved Presences object.

        Open a Presences object that has previously been saved with Presences.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the Presences object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        points = open_file(folder + basename + '-points.gpkg')
        points.rename_geometry('point', inplace=True)

        try:
            import_parameters = open_file(folder + basename + '-parameters.csv')
            import_parameters = import_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            import_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            points = reproject_crs(gdf=points, crs_target=crs_working)  # reproject
            import_parameters['presences_crs'] = str(crs_working)  # update parameter

        return cls(presences=points, name=basename, parameters=import_parameters)

    def plot(self):

        """Plot the presences.

        Makes a basic matplotlib plot of the presences.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        presences_plot(ax=ax, points=self.presences, buffer=None)

    def save(self, folder: str, crs_export: str | int | pyproj.crs.crs.CRS = None):

        """Save the presences.

        Saves the presences as a GPKG file. The name of the saved file will be the name of the Presences object plus
         '-point'. Additionally, the parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the presences to before saving (only reprojects the presences that are saved and
                 not the Presences object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        presences = self.presences.copy()  # copy presences GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if an export CRS is provided
            check_crs(par='crs_export', crs=crs_export)
            presences = reproject_crs(gdf=presences, crs_target=crs_export)  # reproject
            parameters['presences_crs'] = str(crs_export)  # update parameter
        presences['date'] = presences['date'].apply(  # convert date to string if datetime
            lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        presences.to_file(folder + '/' + self.name + '-points.gpkg')  # export presences

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


class PresenceZones:
    def __init__(self, presencezones, name, parameters):
        self.presencezones = presencezones
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of presencezones_delimit()
            cls,
            presences: Presences | list[Presences],
            sections: Sections,
            sp_threshold: int | float = None,
            tm_threshold: int | float = None,
            tm_unit: str | None = None):

        """Delimit presence zones.

        From the presences, use a spatial and, optionally, temporal threshold to make presences zones.
        Presence zones are zones around presences that are deemed to be ‘occupied’ by the animals. Absences will not be
         generated within the presence zones, thus they serve to ensure that absences are generated sufficiently far
         from presences.
        Spatial and temporal thresholds determine the extent of the presence zones. The spatial threshold represents
         the radius and the temporal threshold the number of units (e.g., days) before and after that of the presence.
         For example, a spatial threshold of 10 000 m and a temporal threshold of 5 days means that no absence will be
         generated within 10 000 m and 5 days of any presence.
        Note that the presence zones correspond to sections — specifically, the sections that they overlap spatially
         and, optionally, temporally with, as determined by the spatial and temporal thresholds.

        Parameters:
            presences : Presences
                The Presences object containing the presences from which the presence zones are to be made.
            sections : Sections
                The Sections object containing the sections to which the presence zones correspond.
            sp_threshold : int | float, optional, default None
                The spatial threshold to use for making the presence zones in the units of the CRS.
            tm_threshold : int | float, optional, default None
                The temporal threshold to use for making the presence zones in the units set with tm_unit.
            tm_unit : str, optional, default 'day'
                The temporal units to use for making the presence zones. One of the following:
                    'year': year (all datetimes from the same year will be given the same value)
                    'month': month (all datetimes from the same month and year will be given the same value)
                    'day': day (all datetimes with the same date will be given the same value)
                    'hour': hour (all datetimes in the same hour on the same date will be given the same value)
                    'moy': month of the year (i.e., January is 1, December is 12 regardless of the year)
                    'doy': day of the year (i.e., January 1st is 1, December 31st is 365 regardless of the year
        Returns:
            PresenceZones
                Returns a PresenceZones object with three attributes: name, parameters, and presencezones.
        """

        presencezones = presencezones_delimit(
            sections=sections.sections,
            presences=pd.concat([p.presences for p in presences]) if isinstance(presences, list) else presences.presences,
            sp_threshold=sp_threshold,
            tm_threshold=tm_threshold,
            tm_unit=tm_unit)

        crs = presencezones.crs
        unit = crs.axis_info[0].unit_name

        if isinstance(tm_threshold, (int, float)) and isinstance(tm_unit, str):
            name = 'presencezones-' + str(sp_threshold) + unit[0] + '-' + str(tm_threshold) + tm_unit
        else:
            name = 'presencezones-' + str(sp_threshold) + unit[0] + '-none'

        return cls(
            presencezones=presencezones,
            name=name,
            parameters={
                'presencezones_crs': str(crs),
                'presencezones_sp_threshold': sp_threshold,
                'presencezones_tm_threshold': tm_threshold,
                'presencezones_tm_unit': tm_unit})

    @classmethod
    def open(cls, folder: str, basename: str, crs_working: str | int | pyproj.crs.crs.CRS = None):

        """Open a saved PresenceZones object.

        Open an PresenceZones object that has previously been saved with PresenceZones.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the PresenceZones object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        import_presencezones = open_file(folder + basename + '.gpkg')
        import_presencezones.rename_geometry('presencezones', inplace=True)

        try:
            import_parameters = open_file(folder + basename + '-parameters.csv')
            import_parameters = import_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            import_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            import_presencezones = reproject_crs(gdf=import_presencezones, crs_target=crs_working)  # reproject
            import_parameters['presencezones_crs'] = str(crs_working)  # update parameter

        return cls(presencezones=import_presencezones, name=basename, parameters=import_parameters)

    def plot(self, sections: Sections = None, presences: Presences = None):

        """Plot the presence zones.

        Makes a basic matplotlib plot of the presence zones.

        Parameters:
            sections : Sections, optional, default None
                Optionally, a Sections object with sections to be plotted with the presence zones.
            presences : Presences, optional, default None
                Optionally, a Presences object with presences to be plotted with the presence zones.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        presencezones_plot(ax, self.presencezones)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None
        presences_plot(ax, presences.presences) if isinstance(presences, Presences) else None

    def save(self, folder: str, crs_export: str | int | pyproj.crs.crs.CRS = None):

        """Save the presence zones.

        Saves the presence zones GeoDataFrame as a GPKG. The name of the saved file will be the name of the
         PresenceZones object. Additionally, the parameters will be exported as a CSV with the same name plus
         '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the presence zones to before saving (only reprojects the presence zones that are
                 saved and not the PresenceZones object). The CRS must be either: a pyproj.CRS; a string in a format
                 accepted by pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        presencezones = self.presencezones.copy()  # copy presence zones GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if an export CRS is provided
            check_crs(par='crs_export', crs=crs_export)
            presencezones = reproject_crs(gdf=presencezones, crs_target=crs_export)  # reproject
            parameters['presencezones_crs'] = str(crs_export)  # update parameter

        presencezones.to_file(folder + '/' + self.name + '.gpkg')  # export presence zones

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


class Absences:
    def __init__(self, absences, name, parameters):
        self.absences = absences
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of absences_delimit()
            cls,
            sections: Sections,
            presencezones: PresenceZones,
            var: str,
            target: int | float,
            limit: int = 10,
            dfls: list[int | float] = None,
            block: str = None,
            how: str = None,
            presences: Presences = None
    ):

        """Delimit the absences.

        Absences can be generated by one of two variations: the 'along-the-line' variation or the 'from-the-line'
         variation.
        In the along-the-line variation, each absence is generated by randomly placing a point along the survey track,
         provided it is not within the corresponding presence zones.
        In the from-the-line variation, each absence is generated by randomly placing a point along the survey track and
         then placing a second point a certain distance from the first point perpendicular to the track, provided that
         this second point is not within the corresponding presence zones. The distance from the track is selected from
         a list of candidate distances that can be generated in any way, including from a predefined distribution (e.g.,
         a detection function) by using the function generate_dfls.

        Parameters:
            sections : Sections
                The Sections object containing the sections used to generate the absences.
            presencezones : PresenceZones
                The PresenceZones object containing the presence zones used to generate the absences.
            var : {'along', 'from'}
                The variation to use to generate the absences. Must be one of the following:
                    'along': along-the-line - the absences are generated by randomly placing a point along the surveyed
                     lines ('a' also accepted)
                    'from': from-the-line - the absences are generated by, firstly, randomly placing a point along the
                     line and then, secondly, placing a point a certain distance from the first point perpendicular to
                     the line ('f' also accepted)
            target : int | float
                The total number of absences to be generated.
                Note that if using block, the number of absences generated will likely be slightly higher than the
                 target due to rounding.
                Note that if using block and how='presences', the target is a factor to multiply the number of presences
                 by.
                Note that, during thinning (optionally conducted later on a Samples object), some absences may be
                 removed so, to account for this, the target should be set higher than the final number desired.
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
                     generated for that block); note that presences must also be entered if using this option
            presences : Presences, optional, default None
                If using block and how='presences', the Presences object on which to base the number of absences. Note
                 that the presences must contain the same block column as the sections.
        Returns:
            Absences
                Returns an Absences object with three attributes: name, parameters and absences.
        """

        absences = absences_delimit(
            sections=sections.sections,
            presencezones=presencezones.presencezones,
            var=var,
            target=target,
            limit=limit,
            dfls=dfls,
            block=block,
            how=how,
            presences=presences.presences if isinstance(presences, Presences) else None)

        return cls(
            absences=absences,
            name='absences-' + var[0] + presencezones.name[12:],
            parameters={'absences_var': var, 'absences_target': target} | presencezones.parameters)

    @classmethod
    def open(cls, folder: str, basename: str, crs_working: str | int | pyproj.crs.crs.CRS = None):

        """Open a saved Absences object.

        Open a Absences object that has previously been saved with Absences.save().

        Parameters:
            folder : str
                The path to the folder containing the saved files.
            basename : str
                The name of the Absences object that was saved (without the extension).
            crs_working : str | int | pyproj.CRS, optional, default None
                The CRS to be used for the subsequent processing. In most cases, must be a projected CRS that,
                 preferably, preserves distance and uses metres. The CRS must be either: a pyproj.CRS; a string in a
                 format accepted by pyproj.CRS.from_user_input (e.g., ‘EPSG:4326’); or an integer in a format accepted
                 by pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        points = open_file(folder + basename + '-points.gpkg')
        points.rename_geometry('point', inplace=True)

        try:
            import_parameters = open_file(folder + basename + '-parameters.csv')
            import_parameters = import_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            import_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            points = reproject_crs(gdf=points, crs_target=crs_working)  # reproject
            import_parameters['absences_crs'] = str(crs_working)  # update parameter

        return cls(absences=points, name=basename, parameters=import_parameters)

    def plot(self, presencezones: PresenceZones = None):

        """Plot the absences.

        Makes a basic matplotlib plot of the absences.

        Parameters:
            presencezones : PresenceZones, optional, default None
                Optionally, a PresenceZones object with presence zones to be plotted with the absences.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        absences_plot(ax=ax, points=self.absences, buffer=None)
        presencezones_plot(ax, presencezones.presencezones) if isinstance(presencezones, PresenceZones) else None

    def save(self, folder: str, crs_export: str | int | pyproj.crs.crs.CRS = None):

        """Save the absences.

        Saves the absences as a GPKG file. The name of the saved file will be the name of the Absences object plus
         '-point'. Additionally, the parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            crs_export : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the absences to before saving (only reprojects the absences that are saved and
                 not the Presences object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        absences = self.absences.copy()  # copy absences GeoDataFrame
        parameters = self.parameters.copy()  # copy parameters

        if crs_export is not None:  # if an export CRS is provided
            check_crs(par='crs_export', crs=crs_export)
            absences = reproject_crs(gdf=absences, crs_target=crs_export)  # reproject
            parameters['absences_crs'] = str(crs_export)  # update parameter
        absences['date'] = absences['date'].apply(  # convert date to string if datetime
            lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        absences.to_file(folder + '/' + self.name + '-points.gpkg')  # export absences

        parameters = pd.DataFrame(
            {key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters


##############################################################################################################
# Stage 3: Samples
class Samples:

    def __init__(
            self,
            samples,
            name,
            parameters,
    ):
        self.samples = samples
        self.name = name
        self.parameters = parameters
        self.assigned = None
        self.removed = None

    @classmethod
    def grid(  # wrapper around samples_grid()
            cls,
            datapoints: DataPoints,
            cols: dict,
            cells: Cells,
            periods: Periods | str | None = None,
            full: bool = False):

        """Resample datapoints using the grid approach.

        Determines which cell and period each datapoint lies within and then groups together datapoints that lie within
         the same cell and period. As multiple datapoints may lie within the same cell and period, it is necessary to
         treat them in some way (e.g., average them, sum them). The parameter cols dictates how each column is to be
         treated.

        Parameters:
            datapoints : DataPoints
                The DataPoints object.
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
            cells : Cells
                The Cells object.
            periods : Periods | str | None, optional, default None
                One of the following:
                    a Periods object
                    a string indicating the name of the column in datapoints containing pre-set periods
                    None
            full : bool, optional, default False
                If False, only those cell-period combinations that have at least one datapoint will be included in
                 samples. If True, all possible cell-period combinations will be included in samples (note that this
                 may result in a large number of samples that have no data).

        Returns:
            Samples
                Returns a Samples object with four attributes: name, parameters, samples, and assigned.

        Examples:
            For a set of datapoints with a column of counts of individuals, 'individuals', and a column of values for
             Beaufort sea state (BSS), 'bss', the parameter cols could be set to the following in order to sum the
             individuals observed per sample and get the mean BSS per sample:
                cols={'individuals': 'sum', 'bss': 'mean'}
        """

        if isinstance(periods, Periods):
            periods_name = periods.name
            periods_parameters = periods.parameters
            periods = periods.periods
        elif isinstance(periods, str):
            periods_name = 'periods-' + periods
            periods_parameters = {'periods_column': periods}
        else:
            periods_name = 'periods-none'
            periods_parameters = {'periods': 'none'}

        assigned, samples = samples_grid(
            datapoints=datapoints.datapoints,
            cells=cells.cells,
            periods=periods,
            cols=cols,
            full=full)

        instance = cls(
            samples=samples,
            name='samples-' + datapoints.name + '-x-' + cells.name + '-x-' + periods_name,
            parameters={'approach': 'grid', 'resampled': 'datapoints'} |
                       {'datapoints_name': datapoints.name} | datapoints.parameters |
                       {'cells_name': cells.name} | cells.parameters |
                       {'periods_name': periods_name} | periods_parameters |
                       {'cols': str(cols)})
        instance.assigned = assigned
        return instance

    @classmethod
    def segment(  # wrapper around sample_segment()
            cls,
            datapoints: DataPoints,
            segments: Segments,
            cols: dict,
            how: str):

        """Resample datapoints using the segment approach.

        Determines which segment each datapoint corresponds to and then groups together datapoints that correspond to
         the same segment. As multiple datapoints may correspond to the same segment, it is necessary to treat them in
         some way (e.g., average them, sum them). The parameter cols dictates how each column is to be treated.

        Parameters:
            datapoints : DataPoints
                The DataPoints object.
            segments : Segment
                The Segments object.
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
                     beginning datetimes of the segments (note that Segments.datetimes must be run before; note also
                     that, if multiple surveys are run simultaneously, they will need to be processed separately to
                     avoid datapoints from one survey being allocated to segments from another due to temporal overlap)
                    dfb: each datapoint is matched to a segment based on the distance it is located from the start of
                     the sections lines (only applicable for matching segments that were made from sections that were
                     made from datapoints with Sections.from_datapoints and those datapoints)
        Returns:
            Samples
                Returns a Samples object with four attributes: name, parameters, samples, and assigned.
        Examples:
            For a set of datapoints that has a column of counts of individuals, 'individuals', and a column of values
             for Beaufort sea state (BSS), 'bss', the parameter cols could be set to the following in order to sum the
             individuals observed per sample and get the mean BSS per sample:
                cols={'individuals': 'sum',  'bss': 'mean'}
        """

        assigned, samples = samples_segment(
            datapoints=datapoints.datapoints,
            segments=segments.segments,
            cols=cols,
            how=how)

        instance = cls(
            samples=samples,
            name='samples-' + datapoints.name + '-x-' + segments.name,
            parameters={'approach': 'segment', 'resampled': 'datapoints'} |
                       {'datapoints_name': datapoints.name} | datapoints.parameters |
                       {'segments_name': segments.name} | segments.parameters |
                       {'cols': str(cols)})
        instance.assigned = assigned
        return instance

    @classmethod
    def point(  # wrapper around sample_point()
            cls,
            presences: Presences,
            absences: Absences,
            datapoints_p: DataPoints = None,
            cols_p: list[str] = None,
            datapoints_a: DataPoints = None,
            cols_a: list[str] = None,
            block: str = None):

        """Resample datapoints using the point approach.

        Concatenates the presences and absences and assigns them presence-absence values of 1 and 0, respectively.
        Additionally, and optionally, for each presence, gets data from its corresponding datapoint (i.e., the datapoint
         from which the presence was derived).
        Additionally, and optionally, for each absence, gets the datapoint prior to it and assigns to the absence that
         datapoint’s data. The ID of the prior datapoint is also added to the datapoint_id column. Note that this is
         only applicable if absences were generated from sections that were, in turn, made from datapoints with
         Sections.from_datapoints and those corresponding datapoints.

        Parameters:
            presences : Presences
                The Presences object.
            absences : Absences
                The Absences object.
            datapoints_p : DataPoints, optional, default None
                If adding data to the presences, the DataPoints object containing the data. If specified, data will be
                 added to the presences, if not specified, data will not be added to the presences.
            cols_p : list, optional, default None
                If adding data to the presences, a list indicating which data columns in datapoints_p to add to the
                 presences.
            datapoints_a : DataPoints, optional, default None
                If adding data to the absences, the DataPoints object containing the data. If specified, data will be
                 added to the absences, if not specified, data will not be added to the absences. Note that adding data
                 to absences is only applicable for absences that were generated from sections that were made from
                 datapoints and those datapoints.
            cols_a : list, optional, default None
                If adding data to the absences, a list indicating which data columns in datapoints_a to add to the
                 absences.
            block : str, optional, default None
                If adding data to absences, optionally, the name of a column in the datapoints and absences that
                 contains unique values to be used to separate the datapoints and absences into blocks in order to speed
                 up the assigning of data to absences. If block was used to delimit absences, it must be used here, if
                 adding data to absences.
        Returns:
            Samples
                Returns a Samples object with three attributes: name, parameters, and samples.
        """

        samples = samples_point(
            presences=presences.presences,
            absences=absences.absences,
            datapoints_p=datapoints_p.datapoints if isinstance(datapoints_p, DataPoints) else None,
            cols_p=cols_p,
            datapoints_a=datapoints_a.datapoints if isinstance(datapoints_a, DataPoints) else None,
            cols_a=cols_a,
            block=block)

        return cls(
            samples=samples,
            name='samples-' + presences.name + '-+-' + absences.name,
            parameters={'approach': 'point', 'resampled': 'datapoints'} |
                       {'presences_name': presences.name} | presences.parameters |
                       {'absences_name': absences.name} | absences.parameters)

    @classmethod
    def grid_se(  # wrapper around sample_grid_se()
            cls,
            sections: Sections,
            cells: Cells,
            periods: Periods | str | None = None,
            length: bool = True,
            esw: int | float = None,
            euc_geo: str = 'euclidean',
            full: bool = False):

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
            sections : Sections
                The Sections object.
            cells : Cells
                The Cells object.
            periods : Periods | str | None, optional, default None
                One of the following:
                    a Periods object
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
            Samples
                Returns a Samples object with four attributes: name, parameters, samples, and assigned. Within the
                 samples attribute, the survey effort measures will be contained in the following columns (if
                 applicable):
                    se_length: survey effort measured as length with Euclidean distances
                    se_area: survey effort measured as area with Euclidean distances
                    se_length_geo: survey effort measured as length with geodesic distances
                    se_area_geo: survey effort measured as area with geodesic distances
        """

        if isinstance(periods, Periods):
            periods_name = periods.name
            periods_parameters = periods.parameters
            periods = periods.periods
        elif isinstance(periods, str):
            periods_name = 'periods-' + periods
            periods_parameters = {'periods_column': periods}
        else:
            periods_name = 'periods-none'
            periods_parameters = {'periods': 'none'}

        assigned, samples = samples_grid_se(
            sections=sections.sections,
            cells=cells.cells,
            periods=periods,
            length=length,
            esw=esw,
            euc_geo=euc_geo,
            full=full)

        instance = cls(
            samples=samples,
            name='samples-' + sections.name + '-x-' + cells.name + '-x-' + periods_name,
            parameters={'approach': 'grid', 'resampled': 'effort'} |
                       {'sections_name': sections.name} | sections.parameters |
                       {'cells_name': cells.name} | cells.parameters |
                       {'periods_name': periods_name} | periods_parameters |
                       {'effort_esw': esw, 'effort_euc-geo': euc_geo})
        instance.assigned = assigned
        return instance

    @classmethod
    def segment_se(  # wrapper around sample_segment_se()
            cls,
            segments: Segments,
            length: bool = True,
            esw: int | float = None,
            audf: int | float = None,
            euc_geo: str = 'euclidean'):

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
            segments : Segments
                The Segments object.
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
            Samples
                Returns a Samples object with three attributes: name, parameters, and samples. Within the samples attribute,
                 the survey effort measures will be contained in the following columns (if applicable):
                    se_length: survey effort measured as length with Euclidean distances
                    se_area: survey effort measured as area with Euclidean distances
                    se_effective: survey effort measured as effective area with Euclidean distances
                    se_length_geo: survey effort measured as length with geodesic distances
                    se_area_geo: survey effort measured as area with geodesic distances
                    se_effective_geo: survey effort measured as effective area with geodesic distances
        """

        samples = samples_segment_se(
            segments=segments.segments,
            length=length,
            esw=esw,
            audf=audf,
            euc_geo=euc_geo)

        return cls(
            samples=samples,
            name='samples-' + segments.parameters['sections_name'] + '-x-' + segments.name,
            parameters={'approach': 'segment', 'resampled': 'effort'} |
                       {'segments_name': segments.name} | segments.parameters |
                       {'effort_esw': esw, 'effort_audf': audf, 'effort_euc-geo': euc_geo})

    @classmethod
    def merge(cls, **kwargs):

        """Merge multiple Samples objects together.

        Merge multiple Samples objects into a single new Samples object. Each Samples object should be entered as a
         parameter with a unique name of the user’s choosing (note that this name will be used to name the merged
         Samples object). Only Samples objects made with the grid or segment approach can be merged (i.e., Samples
         objects must be generated by one or more of Samples.grid, Samples.segment, Samples.grid_se, or
         Samples.segment_se, but not Samples.point).

        Parameters:
            **kwargs :
                Any number of Samples objects each entered as a parameter with a unique name of the user’s choosing.

        Returns:
            Samples
                Returns a Samples object with three attributes: name, parameters, and samples.
        """

        # make a DataFrame of all the parameters and their values from all Samples
        parameters_list = []  # list for parameters
        for samples in kwargs.values():  # for each samples, append its parameters to list
            parameters_list.append(pd.DataFrame({key: [samples.parameters[key]] for key in samples.parameters.keys()}))
        parameters_df = pd.concat(parameters_list).reset_index(drop=True)  # parameters DataFrame

        # check the approach
        approach = parameters_df['approach'].unique()
        if len(approach) > 1:  # if more than one approach used to get samples
            raise Exception('\n\n____________________'
                            '\nError: samples generated with different approaches and should not be merged.'
                            f'\nApproaches are: {", ".join(approach)}'
                            '\n____________________')
        else:  # else only one approach used
            approach = approach[0]  # get approach
            if approach in ['grid', 'segment']:
                print(f'\nNote: samples generated with the {approach} approach')
            elif approach in ['point']:
                raise Exception('\n\n____________________'
                                '\nError: samples generated with point approach cannot be merged.'
                                '\n____________________')
            else:
                raise ValueError('\n\n____________________'
                                 '\nValueError: Samples generated with unrecognised approach.'
                                 f'\nApproach is: {approach}'
                                 '\n____________________')

        # check that the samples have matching values for key parameters
        if approach == 'grid':  # grid approach
            parameters_key = ['cells_name', 'cells_crs', 'cells_extent', 'cells_extent_source',
                              'cells_var', 'cells_side', 'cells_unit', 'cells_buffer',
                              'periods_name', 'periods_column', 'periods_tz', 'periods_extent',
                              'periods_extent_source', 'periods_number', 'periods_unit']
        elif approach == 'segment':  # segment approach
            parameters_key = ['sections_name', 'segments_crs',
                              'segments_var', 'segments_rand', 'segments_target', 'segments_unit']
        else:  # unknown approach (should never be reached)
            raise ValueError
        for parameter_key in parameters_key:  # for each key parameter
            if parameter_key in parameters_df:  # if it is present in the parameters dataframe
                if len(parameters_df[parameter_key].unique()) > 1:  # if there is more than one unique value...
                    print(f'Warning: The samples have different parameter values for "{parameter_key}". '
                          f'This may make them incompatible.')  # print warning

        # merge samples
        merged = samples_merge(approach=approach, **{kw: arg.samples for kw, arg in kwargs.items()})

        # make a dictionary of the parameters
        parameters = {}
        for parameter in parameters_df:  # for each parameter, join the unique values (NaNs not included)
            parameters[parameter] = '; '.join([str(value) for value in list(parameters_df[parameter].unique())])

        # make name
        if approach == 'grid':  # grid approach
            name = ('samples-' + '+'.join([name for name in kwargs.keys()]) + '-x-' +  # joined names plus...
                    parameters['cells_name'] + '-x-' + parameters['periods_name'])  # ...cells and periods names
        elif approach == 'segment':  # segment approach
            name = ('samples-' + '+'.join([name for name in kwargs.keys()]) + '-x-' +  # joined names plus...
                    parameters['segments_name'])  # ...segments names
        else:  # unknown approach (should never be reached)
            raise ValueError

        return cls(
            samples=merged,
            name=name,
            parameters={'name': name, 'names': '+'.join([sample.name for sample in kwargs.values()])} | parameters)

    def thin(
            self,
            coords: str = None,
            sp_threshold: int | float = None,
            datetimes: str = None,
            tm_threshold: int | float = None,
            tm_unit: str = 'day',
            block: str = None):

        """Spatially, temporally, or spatiotemporally thin the samples.

        Spatially, temporally, or spatiotemporally thin the samples so that no two samples are within some spatial
         threshold and/or within some temporal threshold of each other.
        If only a spatial threshold is specified, spatial thinning will be conducted. If only a temporal threshold is
         specified, temporal thinning will be conducted. If both a spatial and a temporal threshold are specified,
         spatiotemporal thinning will be conducted.
        Modifies the attribute Samples.samples to contain only those samples kept after thinning. Those samples removed
         after thinning are placed in a new attribute: Samples.removed.

        Parameters:
            coords : str, optional, default None
                The name of the column in the samples containing the geometries to use for thinning. Depending on the
                 approach used to generate the samples, this column should be one of the following:
                    grid approach: 'centroid'
                    segment approach: 'midpoint'
                    point approach: 'point'
            sp_threshold : int | float, optional, default None
                The spatial threshold to use for spatial and spatiotemporal thinning in the units of the CRS.
            datetimes : str, optional, default None
                The name of the column in the samples containing the datetimes to use for thinning. This column should
                 be 'datetimes'.
            tm_threshold : int | float, optional, default None
                The temporal threshold to use for temporal and spatiotemporal thinning in the units set with tm_unit.
            tm_unit : str, optional, default 'day'
                The temporal units to use for temporal and spatiotemporal thinning. One of the following:
                    'year': year (all datetimes from the same year will be given the same value)
                    'month': month (all datetimes from the same month and year will be given the same value)
                    'day': day (all datetimes with the same date will be given the same value)
                    'hour': hour (all datetimes in the same hour on the same date will be given the same value)
                    'moy': month of the year (i.e., January is 1, December is 12 regardless of the year)
                    'doy': day of the year (i.e., January 1st is 1, December 31st is 365 regardless of the year
            block : str, optional, default None
                Optionally, the name of a column that contains unique values to be used to separate the samples into
                 blocks that will be thinned independently.
        """

        full = self.samples.copy()
        full['sample_id'] = ['s' + str(i).zfill(len(str(len(full)))) for i in range(1, len(full) + 1)]  # create IDs

        check_dtype(par='block', obj=block, dtypes=str, none_allowed=True)
        if isinstance(block, str):
            check_cols(df=full, cols=block)

        kept = thinst(
            df=full,
            coords=coords,
            sp_threshold=sp_threshold,
            datetimes=datetimes,
            tm_threshold=tm_threshold,
            tm_unit=tm_unit,
            block=block)
        kept = kept.sort_values('sample_id').reset_index(drop=True)
        removed = full.copy().loc[~full['sample_id'].isin(kept['sample_id'])].reset_index(drop=True)

        remove_cols(removed, 'sample_id')
        remove_cols(kept, 'sample_id')

        self.samples = kept
        self.removed = removed
        self.parameters = self.parameters | {'sp_threshold': sp_threshold,
                                             'tm_threshold': tm_threshold,
                                             'tm_unit': tm_unit}


    def reproject(self, crs_target: str | int | pyproj.crs.crs.CRS = 'EPSG:4326'):

        """Reprojects the samples GeoDataFrame to a target CRS.

        Parameters:
            crs_target : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the samples to.
        """

        check_crs(par='crs_target', crs=crs_target)
        self.samples = reproject_crs(gdf=self.samples,
                                     crs_target=crs_target,
                                     additional=[c for c in ['centroid', 'midpoint'] if c in self.samples])  # reproject
        self.parameters['samples_crs'] = str(crs_target)  # update parameter

    def coords(self):

        """
        Extracts the coordinates from the centroids, midpoints, or points and puts them in two new columns suffixed
         with '_lon' and '_lat' or '_x' and '_y'.
        """

        self.samples = extract_coords(samples=self.samples)  # extract coords

    def save(
            self,
            folder: str,
            filetype: str = 'both',
            crs_export: str | int | pyproj.crs.crs.CRS = None,
            coords: bool = False):

        """Save the samples.

        Saves the samples GeoDataFrame as a GPKG, a CSV, or both. The name of the saved file(s) will be the name of the
         Samples object. Additionally, the parameters will be exported as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the export folder where the exported files will be saved
            filetype : {'gpkg', 'csv', 'both'}, optional, default 'gpkg'
                The type of file that the sections will be saved as.
                    gpkg: GeoPackage
                    csv: CSV
                    both: GeoPackage and CSV
            crs_export : str | int | pyproj.CRS, optional, default None
                Optionally, the CRS to reproject the samples to before saving (only reprojects the samples that are
                 saved and not the Samples object).
            coords : bool, optional, default False
                If True, x and y coordinates will be extracted from the centroid, midpoint, or point geometries and put
                 in separate columns. This may facilitate subsequent extraction of data from external sources.
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        check_dtype(par='filetype', obj=filetype, dtypes=str)
        filetype = filetype.lower()
        check_opt(par='filetype', opt=filetype, opts=['both', 'csv', 'gpkg'])

        samples = self.samples.copy()
        parameters = self.parameters.copy()

        if crs_export is not None:  # if CRS provided
            check_crs(par='crs_export', crs=crs_export)
            samples = reproject_crs(gdf=samples, crs_target=crs_export, additional=[c for c in ['centroid', 'midpoint'] if c in samples])  # reproject
            parameters['samples_crs'] = str(crs_export)  # update parameter
        samples = extract_coords(samples=samples) if coords else samples  # extract coords (if coords)

        for col in ['date', 'date_beg', 'date_mid', 'date_end']:  # for each potential date col...
            if col in samples:  # ...if present...
                samples[col] = samples[col].apply(  # convert date to string if there is date
                    lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)

        if filetype in ['csv', 'both']:  # if CSV
            samples.to_csv(folder + '/' + self.name + '.csv', index=False)  # export
        if filetype in ['gpkg', 'both']:  # if GPKG
            for col in ['centroid', 'midpoint']:  # ...for each extra geometry col...
                if col in samples:  # ...if present...
                    samples[col] = samples[col].to_wkt()  # ...convert to wkt
            samples.to_file(folder + '/' + self.name + '.gpkg')  # export

        parameters = pd.DataFrame({key: [value] for key, value in parameters.items()}).T.reset_index()  # parameters dataframe
        parameters.columns = ['parameter', 'value']  # rename columns
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # export parameters
