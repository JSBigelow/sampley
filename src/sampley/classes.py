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
            crs_input: str | int | pyproj.crs.crs.CRS = None,
            crs_working: str | int | pyproj.crs.crs.CRS = None,
            datetime_col: str | None = None,
            datetime_format: str = None,
            tz_input: str | timezone | pytz.BaseTzInfo | None = None,
            tz_working: str | timezone | pytz.BaseTzInfo | None = None,
            datapoint_id_col: str = None,
            section_id_col: str = None):

        """Make a DataPoints object from a GPKG, SHP, CSV, or XLSX file.

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
            DataPoints
                Returns a DataPoints object with three attributes: name, parameters, and datapoints.
        """

        datapoints = datapoints_from_file(
            filepath=filepath,
            x_col=x_col,
            y_col=y_col,
            geometry_col=geometry_col,
            crs_input=crs_input,
            crs_working=crs_working,
            datetime_col=datetime_col,
            datetime_format=datetime_format,
            tz_input=tz_input,
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

        input_datapoints = open_file(folder + basename + '.gpkg')
        input_datapoints = input_datapoints[['datapoint_id', 'geometry', 'datetime'] +
                                            [c for c in input_datapoints if c not in
                                             ['datapoint_id', 'geometry', 'datetime']]]
        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            input_datapoints = reproject_crs(gdf=input_datapoints, crs_target=crs_working)  # reproject
            input_parameters['datapoints_crs'] = str(crs_working)  # update parameter

        if isinstance(input_datapoints['datetime'].iloc[0], str):
            parse_dts(input_datapoints, 'datetime')
            if tz_working is not None:  # if TZ provided
                check_tz(par='tz_working', tz=tz_working)
                input_datapoints = convert_tz(df=input_datapoints, datetime_cols='datetime', tz_target=tz_working)  # convert
                input_parameters['datapoints_tz'] = str(tz_working)  # update parameter

        return cls(datapoints=input_datapoints, name=basename, parameters=input_parameters)

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
             crs_output: str | int | pyproj.crs.crs.CRS = None,
             tz_output: str | timezone | pytz.BaseTzInfo = None):

        """Save the datapoints.

        Saves the datapoints GeoDataFrame as a GPKG. The name of the saved file will be the name of the DataPoints
         object. Additionally, the parameters will be output as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the datapoints to before saving (only reprojects the datapoints that are saved and
                 not the DataPoints object).
            tz_output : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to convert the datapoints to before saving (only converts the datapoints that are saved and
                 not the DataPoints object).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_datapoints = self.datapoints.copy()  # copy datapoints GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if CRS provided
            check_crs(par='crs_output', crs=crs_output)
            output_datapoints = reproject_crs(gdf=output_datapoints, crs_target=crs_output)  # reproject
            output_parameters['datapoints_crs'] = str(crs_output)  # update parameter
        if tz_output is not None:  # if TZ provided
            check_tz(par='tz_output', tz=tz_output)
            output_datapoints = convert_tz(df=output_datapoints, datetime_cols='datetime', tz_target=tz_output)  # convert
            output_parameters['datapoints_tz'] = str(tz_output)  # update parameter
        output_datapoints['datetime'] = output_datapoints['datetime'].apply(  # convert datetime to string if datetime
            lambda dt: str(dt) if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        output_datapoints.to_file(folder + '/' + self.name + '.gpkg')  # output datapoints as GPKG

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


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
            tz_input: str | timezone | pytz.BaseTzInfo | None = None,
            tz_working: str | timezone | pytz.BaseTzInfo | None = None,
            section_id_col: str | None = None):

        """Make a Sections object from a GPKG or SHP file.

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
                Returns a Sections object with three attributes: name, parameters, and sections.
        """

        sections = sections_from_file(
            filepath=filepath,
            crs_working=crs_working,
            datetime_col=datetime_col,
            datetime_format=datetime_format,
            tz_input=tz_input,
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

        Takes as input a DataPoints object that contains sections as continuous series of Points and reformats it for
         subsequent processing by: converting each series of Points to a LineString; renaming and reordering essential 
         columns. The CRS and timezone will be that of the DataPoints object.
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

        input_sections = open_file(folder + basename + '.gpkg')
        input_sections = input_sections[['section_id', 'geometry', 'datetime'] +
                                        [c for c in input_sections if c not in ['section_id', 'geometry', 'datetime']]]
        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            input_sections = reproject_crs(gdf=input_sections, crs_target=crs_working)  # reproject
            input_parameters['sections_crs'] = str(crs_working)  # update parameter

        if isinstance(input_sections['datetime'].iloc[0], str):
            parse_dts(input_sections, 'datetime')
            if tz_working is not None:  # if TZ provided
                check_tz(par='tz_working', tz=tz_working)
                input_sections = convert_tz(df=input_sections, datetime_cols='datetime', tz_target=tz_working)  # convert
                input_parameters['sections_tz'] = str(tz_working)  # update parameter

        return cls(sections=input_sections, name=basename, parameters=input_parameters)

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
             crs_output: str | int | pyproj.crs.crs.CRS = None,
             tz_output: str | timezone | pytz.BaseTzInfo = None):

        """Save the sections.

        Saves the sections GeoDataFrame as a GPKG. The name of the saved file will be the name of the Sections object.
         Additionally, the parameters will be output as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the sections to before saving (only reprojects the sections that are saved and not
                 the Sections object).
            tz_output : str | timezone | pytz.BaseTzInfo, optional, default None
                The timezone to convert the sections to before saving (only converts the sections that are saved and not
                 the Sections object).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_sections = self.sections.copy()  # copy sections GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if CRS provided
            check_crs(par='crs_output', crs=crs_output)
            output_sections = reproject_crs(gdf=output_sections, crs_target=crs_output)  # reproject
            output_parameters['sections_crs'] = str(crs_output)  # update parameter
        if tz_output is not None:  # if TZ provided
            check_tz(par='tz_output', tz=tz_output)
            output_sections = convert_tz(df=output_sections, datetime_cols='datetime', tz_target=tz_output)  # convert
            output_parameters['sections_tz'] = str(tz_output)  # update parameter
        output_sections['datetime'] = output_sections['datetime'].apply(  # convert datetime to string if datetime
            lambda dt: str(dt) if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        output_sections.to_file(folder + '/' + self.name + '.gpkg')  # output sections as GPKG

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


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
         input data.

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
                'periods_extent': periods['date_beg'].min().strftime('%Y-%m-%d') + '-' +
                                  periods['date_end'].max().strftime('%Y-%m-%d'),
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

        input_periods = open_file(folder + basename + '.csv')
        input_periods['date_beg'] = pd.to_datetime(input_periods['date_beg'])
        input_periods['date_mid'] = pd.to_datetime(input_periods['date_mid'])
        input_periods['date_end'] = pd.to_datetime(input_periods['date_end'])

        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        return cls(periods=input_periods, name=basename, parameters=input_parameters)

    def save(self, folder: str):

        """Save the periods.

        Saves the periods DataFrame as a CSV. The name of the saved file will be the name of the Periods object.
         Additionally, the parameters will be output as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_periods = self.periods.copy()  # copy dataframe
        output_parameters = self.parameters.copy()  # copy parameters

        for col in ['date_beg', 'date_mid', 'date_end']:  # for each potential datetime col...
            output_periods[col] = output_periods[col].apply(  # convert datetime to string if there is datetime
                lambda dt: str(dt) if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        output_periods.to_csv(folder + '/' + self.name + '.csv', index=False)  # output to CSV

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


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
            input_cells = pd.merge(polygons, centroids, on='cell_id')
        except FileNotFoundError:
            print('Warning: centroids not found. Cells object will be made without centroids.')
            input_cells = polygons
            input_cells['centroid'] = None

        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            input_cells = reproject_crs(gdf=input_cells, crs_target=crs_working, additional='centroid')  # reproject
            input_parameters['cells_crs'] = str(crs_working)  # update parameter

        return cls(cells=input_cells, name=basename, parameters=input_parameters)


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

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):

        """Save the cells.

        Saves the cells GeoDataFrame as two GPKGs: one of the polygons and one of the centroids. The names of the saved
         files will be the name of the Cells object plus '-polygons' and '-centroids', respectively. Additionally, the
         parameters will be output as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the cells to before saving (only reprojects the cells that are saved and not the
                 Cells object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_cells = self.cells.copy()  # copy cells GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if CRS provided
            check_crs(par='crs_output', crs=crs_output)
            output_cells = reproject_crs(gdf=output_cells, crs_target=crs_output, additional='centroid')  # reproject
            output_parameters['cells_crs'] = str(crs_output)  # update parameter

        output_cells[['cell_id', 'polygon']].to_file(folder + '/' + self.name + '-polygons.gpkg')  # output polygons
        output_cells[['cell_id', 'centroid']].to_file(folder + '/' + self.name + '-centroids.gpkg')  # output centroids

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


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
            input_segments = pd.merge(lines, midpoints, on='segment_id')
        except FileNotFoundError:
            print('Warning: midpoints not found. Segments object will be made without midpoints.')
            input_segments = lines
            input_segments['midpoint'] = None

        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            input_segments = reproject_crs(gdf=input_segments, crs_target=crs_working, additional='midpoint')  # reproject
            input_parameters['cells_crs'] = str(crs_working)  # update parameter

        return cls(segments=input_segments, name=basename, parameters=input_parameters)

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

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):

        """Save the segments.

        Saves the segments GeoDataFrame as two GPKGs: one of the lines and one of the midpoints. The names of the saved
         files will be the name of the Segments object plus '-lines' and '-midpoints', respectively. Additionally, the
         parameters will be output as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the segments to before saving (only reprojects the segments that are saved and not
                 the Segments object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_segments = self.segments.copy()  # copy segments GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if CRS provided
            check_crs(par='crs_output', crs=crs_output)
            output_segments = reproject_crs(gdf=output_segments, crs_target=crs_output, additional='midpoint')  # reproject
            output_parameters['segments_crs'] = str(crs_output)  # update parameter

        output_segments[['segment_id', 'line']].to_file(folder + '/' + self.name + '-lines.gpkg')  # output lines
        output_segments[['segment_id', 'midpoint']].to_file(folder + '/' + self.name + '-midpoints.gpkg')  # output midpoints

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


class Presences:
    def __init__(self, full, kept, removed, name, parameters):
        self.full = full
        self.kept = kept
        self.removed = removed
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of presences_delimit()
            cls,
            datapoints: DataPoints,
            presence_col: str = None):

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

        Returns:
            Presences
                Returns a Presences object with three attributes: name, parameters and full.
        """

        full = presences_delimit(
            datapoints=datapoints.datapoints,
            presence_col=presence_col)

        crs = full.crs
        return cls(
            full=full,
            kept=None,
            removed=None,
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

        full = open_file(folder + basename + '-full.gpkg')
        full.rename_geometry('point', inplace=True)
        full = full[['point_id', 'point', 'date', 'datapoint_id']]
        try:
            kept = open_file(folder + basename + '-kept.gpkg')
            kept.rename_geometry('point', inplace=True)
            kept = kept[['point_id', 'point', 'date', 'datapoint_id']]
        except FileNotFoundError:
            print('Warning: kept points not found. Presences object will be made without kept attribute.')
            kept = None
        try:
            removed = open_file(folder + basename + '-removed.gpkg')
            removed.rename_geometry('point', inplace=True)
            removed = removed[['point_id', 'point', 'date', 'datapoint_id']]
        except FileNotFoundError:
            print('Warning: removed points not found. Presences object will be made without removed attribute.')
            removed = None

        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            full = reproject_crs(gdf=full, crs_target=crs_working)  # reproject
            kept = reproject_crs(gdf=kept, crs_target=crs_working) if isinstance(kept, gpd.GeoDataFrame) else None
            removed = reproject_crs(gdf=removed, crs_target=crs_working) if isinstance(removed, gpd.GeoDataFrame) else None
            input_parameters['presences_crs'] = str(crs_working)  # update parameter

        return cls(full=full, kept=kept, removed=removed, name=basename, parameters=input_parameters)

    def thin(
            self,
            sp_threshold: int | float,
            tm_threshold: int | float,
            tm_unit: str = 'day',
            target: int = None):

        """Spatiotemporally thin the presences.

        Spatiotemporally thin the presences so that no two presences are within some spatial threshold and/or within
         some temporal threshold of each other.
        If only a spatial threshold is specified, spatial thinning will be conducted. If only a temporal threshold is
         specified, temporal thinning will be conducted. If both a spatial and a temporal threshold are specified,
         spatiotemporal thinning will be conducted.
        Adds to the Presences object two attributes — Presences.kept and Presences.removed — that are both
         geopandas.GeoDataFrame containing the points that were kept and those that were removed after spatiotemporal
         thinning, respectively.

        Parameters:
            sp_threshold : int | float, optional, default None
                The spatial threshold to use for spatial and spatiotemporal thinning in the units of the CRS.
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
            target : int, optional, default None
                The target number of presences. If, after thinning, the number of presences is greater than the target,
                 the kept presences will be randomly sampled to reduce their number to the target.
        """

        kept = thinst(
            df=self.full,
            coords='point',
            sp_threshold=sp_threshold,
            datetimes='date',
            tm_threshold=tm_threshold,
            tm_unit=tm_unit)

        if target is not None:
            check_dtype(par='target', obj=target, dtypes=int)
            if len(kept) > target:
                kept = kept.sample(target)
        kept = kept.sort_values('point_id')

        self.kept = kept
        self.removed = self.full.copy().loc[~self.full['point_id'].isin(self.kept['point_id'])]
        self.parameters = self.parameters | {'presences_sp_threshold': sp_threshold,
                                             'presences_tm_threshold': tm_threshold,
                                             'presences_tm_unit': tm_unit}

    def plot(self, sp_threshold: int | float = None, which: str = 'full'):

        """Plot the presences.

        Makes a basic matplotlib plot of the presences.

        Parameters:
            sp_threshold : int | float, optional, default None
                The spatial threshold used for spatial and spatiotemporal thinning in the units of the CRS. If
                 specified, the plot will add a circle around each point to represent the spatial threshold.
            which : { 'full', 'kept', 'removed', 'thinned'}, optional, default 'full'
                A keyword to indicate which set of points to plot. Must be one of the following:
                    'full': all the presences (in blue)
                    'kept': the presences kept after thinning (in blue)
                    'removed': the presences removed after thinning (in yellow)
                    'thinned': the presences kept after thinning (in blue) and those removed after thinning  (in yellow)
        """

        check_dtype(par='sp_threshold', obj=sp_threshold, dtypes=[int, float], none_allowed=True)
        check_dtype(par='which', obj=which, dtypes=str)
        check_opt(par='which', opt=which, opts=['full', 'kept', 'removed', 'thinned'])

        fig, ax = plt.subplots(figsize=(16, 8))
        buffer = sp_threshold/2 if isinstance(sp_threshold, (int, float)) else None
        if which == 'full':
            presences_plot(ax=ax, points=self.full, buffer=buffer)
        elif which == 'kept':
            presences_plot(ax=ax, points=self.kept, buffer=buffer)
        elif which == 'removed':
            presences_removed_plot(ax=ax, points=self.removed, buffer=buffer)
        elif which == 'thinned':
            presences_plot(ax=ax, points=self.kept, buffer=buffer)
            presences_removed_plot(ax=ax, points=self.removed, buffer=buffer)
        else:
            pass

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):

        """Save the presences.

        Saves the full, kept, and removed presences as GPKG files. The name of the saved files will be the name of the
         Presences object plus '-full', '-kept', and '-removed', respectively. Note that the kept and removed presences
         will only be saved if they have been made with Presences.thin. Additionally, the parameters will be output as
         a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the presences to before saving (only reprojects the presences that are saved and
                 not the Presences object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_full = self.full.copy()  # copy full presences GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if an output CRS is provided
            check_crs(par='crs_output', crs=crs_output)
            output_full = reproject_crs(gdf=output_full, crs_target=crs_output)  # reproject
            output_parameters['presences_crs'] = str(crs_output)  # update parameter
        output_full['date'] = output_full['date'].apply(  # convert date to string if datetime
            lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        output_full.to_file(folder + '/' + self.name + '-full.gpkg')  # output full presences

        if isinstance(self.kept, gpd.GeoDataFrame):  # if kept presences...
            output_kept = self.kept.copy()  # copy kept presences GeoDataFrame
            if crs_output is not None:  # if an output CRS is provided
                output_kept = reproject_crs(gdf=output_kept, crs_target=crs_output)  # reproject
            output_kept['date'] = output_kept['date'].apply(  # convert date to string if datetime
                lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
            output_kept.to_file(folder + '/' + self.name + '-kept.gpkg')  # output kept presences

        if isinstance(self.removed, gpd.GeoDataFrame):  # if removed presences...
            output_removed = self.removed.copy()  # copy removed presences GeoDataFrame
            if crs_output is not None:  # if an output CRS is provided
                output_removed = reproject_crs(gdf=output_removed, crs_target=crs_output)  # reproject
            output_removed['date'] = output_removed['date'].apply(  # convert date to string if datetime
                lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
            output_removed.to_file(folder + '/' + self.name + '-removed.gpkg')  # output removed presences

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


class PresenceZones:
    def __init__(self, presencezones, name, parameters):
        self.presencezones = presencezones
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of presencezones_delimit()
            cls,
            presences: Presences,
            sections: Sections,
            sp_threshold: int | float = None,
            tm_threshold: int | float = None,
            tm_unit: str | None = None):

        """Delimit presences zones.

        From the presences, use a spatial and, optionally, temporal threshold to make presences zones.
        Presence zones are zones around presences that are deemed to be ‘occupied’ by the animals. Spatial and temporal
         thresholds determine the extent of these occupied zones.
        Additionally, the presence zones correspond to sections — specifically, the sections that they overlap spatially
         and, optionally, temporally with, as determined by the spatial and temporal thresholds.

        Parameters:
            presences : Presences
                The Presences object containing the presences from which the presences zones are to be made.
            sections : Sections
                The Sections object containing the sections to which the presences zones correspond.
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
            PresenceZones
                Returns a PresenceZones object with three attributes: name, parameters, and presencezones.
        """

        presencezones = presencezones_delimit(
            sections=sections.sections,
            presences=presences.full,
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

        input_presencezones = open_file(folder + basename + '.gpkg')
        input_presencezones.rename_geometry('presencezones', inplace=True)

        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            input_presencezones = reproject_crs(gdf=input_presencezones, crs_target=crs_working)  # reproject
            input_parameters['presencezones_crs'] = str(crs_working)  # update parameter

        return cls(presencezones=input_presencezones, name=basename, parameters=input_parameters)

    def plot(self, sections: Sections = None, presences: Presences = None):

        """Plot the presences zones.

        Makes a basic matplotlib plot of the presences zones.

        Parameters:
            sections : Sections, optional, default None
                Optionally, a Sections object with sections to be plotted with the presences zones.
            presences : Presences, optional, default None
                Optionally, a Presences object with presences to be plotted with the presences zones.
        """

        fig, ax = plt.subplots(figsize=(16, 8))
        presencezones_plot(ax, self.presencezones)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None
        presences_plot(ax, presences.full, buffer=self.parameters['absences_sp_threshold']) if isinstance(presences, Presences) else None

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):

        """Save the presences zones.

        Saves the presences zones GeoDataFrame as a GPKG. The name of the saved file will be the name of the
         PresenceZones object. Additionally, the parameters will be output as a CSV with the same name plus
         '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the presences zones to before saving (only reprojects the presences zones that are
                 saved and not the PresenceZones object). The CRS must be either: a pyproj.CRS; a string in a format
                 accepted by pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_presencezones = self.presencezones.copy()  # copy presence zones GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if an output CRS is provided
            check_crs(par='crs_output', crs=crs_output)
            output_presencezones = reproject_crs(gdf=output_presencezones, crs_target=crs_output)  # reproject
            output_parameters['presencezones_crs'] = str(crs_output)  # update parameter

        output_presencezones.to_file(folder + '/' + self.name + '.gpkg')  # output presence zones

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


class Absences:
    def __init__(self, full, kept, removed, name, parameters):
        self.full = full
        self.kept = kept
        self.removed = removed
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of absences_delimit()
            cls,
            sections: Sections,
            presencezones: PresenceZones,
            var: str,
            target: int | float,
            dfls: list[int | float] = None):

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
            sections : Sections
                The Sections object containing the sections used to generate the absences.
            presencezones : PresenceZones
                The PresenceZones object containing the presences zones used to generate the absences.
            var : {'along', 'from'}
                The variation to use to generate the absences. Must be one of the following:
                    'along': along-the-line - the absences are generated by randomly placing a point along the surveyed
                     lines ('a' also accepted)
                    'from': from-the-line - the absences are generated by, firstly, randomly placing a point along the
                     line and then, secondly, placing a point a certain distance from the first point perpendicular to
                     the line ('f' also accepted)
            target : int | float
                The target number of absences to be generated. Note that, during thinning, some absences may be removed
                 so, to account for this, the target should be set higher than the number desired.
            dfls : list[int | float], optional, default None
                If using the from-the-line variation, a list of candidate distances from the line to use when generating
                 absences. For each absence, one of these distances will be chosen at random and used to place the
                 absence at that distance from the survey line. These distances can be generated in any way, including
                 from a predefined distribution (e.g., a detection function) with the function generate_dfls.

        Returns:
            Absences
                Returns an Absences object with three attributes: name, parameters and full.
        """

        full = absences_delimit(
            sections=sections.sections,
            presencezones=presencezones.presencezones,
            var=var,
            target=target,
            dfls=dfls)

        return cls(
            full=full,
            kept=None,
            removed=None,
            name='absences-' + var[0] + presencezones.name[12:],
            parameters={'absences_var': var, 'absences_target': target} | presencezones.parameters)

    @classmethod
    def open(cls, folder: str, basename: str, crs_working: str | int | pyproj.crs.crs.CRS = None):

        """Open a saved Absences object.

        Open an Absences object that has previously been saved with Absences.save().

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

        full = open_file(folder + basename + '-full.gpkg')
        full.rename_geometry('point', inplace=True)
        full = full[['point_id', 'point', 'date']]
        try:
            kept = open_file(folder + basename + '-kept.gpkg')
            kept.rename_geometry('point', inplace=True)
            kept = kept[['point_id', 'point', 'date']]
        except FileNotFoundError:
            print('Warning: kept points not found. Absences object will be made without kept attribute.')
            kept = None
        try:
            removed = open_file(folder + basename + '-removed.gpkg')
            removed.rename_geometry('point', inplace=True)
            removed = removed[['point_id', 'point', 'date']]
        except FileNotFoundError:
            print('Warning: removed points not found. Absences object will be made without removed attribute.')
            removed = None

        try:
            input_parameters = open_file(folder + basename + '-parameters.csv')
            input_parameters = input_parameters.set_index('parameter').T.to_dict('records')[0]
        except FileNotFoundError:
            print('Warning: parameters not found. An empty parameters attribute will be made.')
            input_parameters = {}

        if crs_working is not None:  # if CRS provided
            check_crs(par='crs_working', crs=crs_working)
            full = reproject_crs(gdf=full, crs_target=crs_working)  # reproject
            kept = reproject_crs(gdf=kept, crs_target=crs_working) if isinstance(kept, gpd.GeoDataFrame) else None
            removed = reproject_crs(gdf=removed, crs_target=crs_working) if isinstance(removed, gpd.GeoDataFrame) else None
            input_parameters['absences_crs'] = str(crs_working)  # update parameter

        return cls(full=full, kept=kept, removed=removed, name=basename, parameters=input_parameters)

    def thin(
            self,
            sp_threshold: int | float,
            tm_threshold: int | float,
            tm_unit: str = 'day',
            target: int = None):

        """Spatiotemporally thin the absences.

        Spatiotemporally thin the absences so that no two absences are within some spatial threshold and/or within some
         temporal threshold of each other.
        If only a spatial threshold is specified, spatial thinning will be conducted. If only a temporal threshold is
         specified, temporal thinning will be conducted. If both a spatial and a temporal threshold are specified,
         spatiotemporal thinning will be conducted.
        Adds to the Absences object two attributes — Absences.kept and Absences.removed — that are both
         geopandas.GeoDataFrame containing the points that were kept and those that were removed after spatiotemporal
         thinning, respectively.

        Parameters:
            sp_threshold : int | float, optional, default None
                The spatial threshold to use for spatial and spatiotemporal thinning in the units of the CRS.
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
            target : int, optional, default None
                The target number of absences. If, after thinning, the number of absences is greater than the target,
                 the kept absences will be randomly sampled to reduce their number to the target.
        """

        kept = thinst(
            df=self.full,
            coords='point',
            sp_threshold=sp_threshold,
            datetimes='date',
            tm_threshold=tm_threshold,
            tm_unit=tm_unit)

        if target is not None:
            check_dtype(par='target', obj=target, dtypes=int)
            if len(kept) > target:
                kept = kept.sample(target)
        kept = kept.sort_values('point_id')

        self.kept = kept
        self.removed = self.full.copy().loc[~self.full['point_id'].isin(self.kept['point_id'])]
        self.parameters = self.parameters | {'absences_sp_threshold': sp_threshold,
                                             'absences_tm_threshold': tm_threshold,
                                             'absences_tm_unit': tm_unit}

    def plot(self, sp_threshold: int | float = None, which: str = 'full', presencezones: PresenceZones = None):

        """Plot the absences.

        Makes a basic matplotlib plot of the absences.

        Parameters:
            sp_threshold : int | float, optional, default None
                The spatial threshold used for spatial and spatiotemporal thinning in the units of the CRS. If
                 specified, the plot will add a circle around each point to represent the spatial threshold.
            which : { 'full', 'kept', 'removed', 'thinned'}, optional, default 'full'
                A keyword to indicate which set of points to plot. Must be one of the following:
                    'full': all the absences (in red)
                    'kept': the absences kept after thinning (in red)
                    'removed': the absences removed after thinning (in yellow)
                    'thinned': the absences kept after thinning (in red) and those removed after thinning (in yellow)
            presencezones : PresenceZones, optional, default None
                Optionally, an PresenceZones object with presences zones to be plotted with the absences.
        """

        check_dtype(par='sp_threshold', obj=sp_threshold, dtypes=[int, float], none_allowed=True)
        check_dtype(par='which', obj=which, dtypes=str)
        check_opt(par='which', opt=which, opts=['full', 'kept', 'removed', 'thinned'])

        fig, ax = plt.subplots(figsize=(16, 8))
        buffer = sp_threshold/2 if isinstance(sp_threshold, (int, float)) else None
        if which == 'full':
            absences_plot(ax=ax, points=self.full, buffer=buffer)
        elif which == 'kept':
            absences_plot(ax=ax, points=self.kept, buffer=buffer)
        elif which == 'removed':
            absences_removed_plot(ax=ax, points=self.removed, buffer=buffer)
        elif which == 'thinned':
            absences_plot(ax=ax, points=self.kept, buffer=buffer)
            absences_removed_plot(ax=ax, points=self.removed, buffer=buffer)
        else:
            pass
        presencezones_plot(ax=ax, zones=presencezones.presencezones) if isinstance(presencezones, PresenceZones) else None

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):

        """Save the absences.

        Saves the full, kept, and removed absences as GPKG files. The name of the saved files will be the name of the
         Absences object plus '-full', '-kept', and '-removed', respectively. Note that the kept and removed absences
         will only be saved if they have been made with Absences.thin. Additionally, the parameters will be output as a
         CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            crs_output : str | int | pyproj.CRS, optional, default None
                The CRS to reproject the absences to before saving (only reprojects the absences that are saved and not
                 the Absences object). The CRS must be either: a pyproj.CRS; a string in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 'EPSG:4326'); or an integer in a format accepted by
                 pyproj.CRS.from_user_input (e.g., 4326).
        """

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_full = self.full.copy()  # copy full presences GeoDataFrame
        output_parameters = self.parameters.copy()  # copy parameters

        if crs_output is not None:  # if an output CRS is provided
            check_crs(par='crs_output', crs=crs_output)
            output_full = reproject_crs(gdf=output_full, crs_target=crs_output)  # reproject
            output_parameters['absences_crs'] = str(crs_output)  # update parameter
        output_full['date'] = output_full['date'].apply(  # convert date to string if datetime
            lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
        output_full.to_file(folder + '/' + self.name + '-full.gpkg')  # output full presences

        if isinstance(self.kept, gpd.GeoDataFrame):  # if kept presences...
            output_kept = self.kept.copy()  # copy kept presences GeoDataFrame
            if crs_output is not None:  # if an output CRS is provided
                output_kept = reproject_crs(gdf=output_kept, crs_target=crs_output)  # reproject
            output_kept['date'] = output_kept['date'].apply(  # convert date to string if datetime
                lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
            output_kept.to_file(folder + '/' + self.name + '-kept.gpkg')  # output kept presences

        if isinstance(self.removed, gpd.GeoDataFrame):  # if removed presences...
            output_removed = self.removed.copy()  # copy removed presences GeoDataFrame
            if crs_output is not None:  # if an output CRS is provided
                output_removed = reproject_crs(gdf=output_removed, crs_target=crs_output)  # reproject
            output_removed['date'] = output_removed['date'].apply(  # convert date to string if datetime
                lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)
            output_removed.to_file(folder + '/' + self.name + '-removed.gpkg')  # output removed presences

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters


##############################################################################################################
# Stage 3: Samples
class Samples:

    def __init__(
            self,
            samples,
            name,
            parameters,
            assigned
    ):
        self.samples = samples
        self.name = name
        self.parameters = parameters
        self.assigned = assigned

    @classmethod
    def grid(  # wrapper around samples_grid()
            cls,
            datapoints: DataPoints,
            cells: Cells,
            periods: Periods | str | None,
            cols: dict,
            full: bool = False):

        """Resample datapoints using the grid approach.

        Determines which cell and period each datapoint lies within and then groups together datapoints that lie within
         the same cell and period. As multiple datapoints may lie within the same cell and period, it is necessary to
         treat them in some way (e.g., average them, sum them). The parameter cols dictates how each column is to be
         treated.

        Parameters:
            datapoints : DataPoints
                The DataPoints object.
            cells : Cells
                The Cells object.
            periods : Periods | str | None
                One of the following:
                    a Periods object
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

        return cls(
            samples=samples,
            name='samples-' + datapoints.name + '-x-' + cells.name + '-x-' + periods_name,
            parameters={'approach': 'grid', 'resampled': 'datapoints'} |
                       {'datapoints_name': datapoints.name} | datapoints.parameters |
                       {'cells_name': cells.name} | cells.parameters |
                       {'periods_name': periods_name} | periods_parameters |
                       {'cols': str(cols)},
            assigned=assigned)

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

        return cls(
            samples=samples,
            name='samples-' + datapoints.name + '-x-' + segments.name,
            parameters={'approach': 'segment', 'resampled': 'datapoints'} |
                       {'datapoints_name': datapoints.name} | datapoints.parameters |
                       {'segments_name': segments.name} | segments.parameters |
                       {'cols': str(cols)},
            assigned=assigned)

    @classmethod
    def point(  # wrapper around sample_point()
            cls,
            datapoints: DataPoints,
            presences: Presences,
            absences: Absences,
            cols: list[str],
            sections: Sections = None):

        """Resample datapoints using the point approach.

        For each presence, gets data from its corresponding datapoint (i.e., the datapoint from which the presence was
         derived).
        Optionally, for each absence, gets the datapoint prior to it and assigns to the absence that datapoint’s data.
         The ID of the prior datapoint is also added to the datapoint_id column. Note that this is only applicable if
         presences zones were made from sections that were, in turn, made from datapoints with Sections.from_datapoints
         and those datapoints.
        Concatenates the presences and absences and assigns them presence-absence values of 1 and 0, respectively.

        Parameters:
            datapoints : DataPoints
                The DataPoints object.
            presences : Presences
                The Presences object.
            absences : Absences
                The Absences object.
            cols : list
                A list indicating which data columns to add to the Presences and, if applicable, the Absences.
            sections : Sections, optional, default None
                If adding data to the absences, the Sections object from which the PresenceZones were derived (only
                applicable for sections that were made from datapoints with Sections.from_datapoints and those
                datapoints).

        Returns:
            Samples
                Returns a Samples object with three attributes: name, parameters, and samples.
        """

        samples = samples_point(
            datapoints=datapoints.datapoints,
            presences=presences.kept,
            absences=absences.kept,
            cols=cols,
            sections=sections.sections if sections is not None else None)

        return cls(
            samples=samples,
            name='samples-' + presences.name + '-+-' + absences.name,
            parameters={'approach': 'point', 'resampled': 'datapoints'} |
                       {'presences_name': presences.name} | presences.parameters |
                       {'absences_name': absences.name} | absences.parameters,
            assigned=None)

    @classmethod
    def grid_se(  # wrapper around sample_grid_se()
            cls,
            sections: Sections,
            cells: Cells,
            periods: Periods | str | None,
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
            periods : Periods | str | None
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

        return cls(
            samples=samples,
            name='samples-' + sections.name + '-x-' + cells.name + '-x-' + periods_name,
            parameters={'approach': 'grid', 'resampled': 'effort'} |
                       {'sections_name': sections.name} | sections.parameters |
                       {'cells_name': cells.name} | cells.parameters |
                       {'periods_name': periods_name} | periods_parameters |
                       {'effort_esw': esw, 'effort_euc-geo': euc_geo},
            assigned=assigned)

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
                       {'effort_esw': esw, 'effort_audf': audf, 'effort_euc-geo': euc_geo},
            assigned=None)

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

        # make a DataFrame of all the parameters and their values from all input Samples
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
            name = ('samples-' + '+'.join([name for name in kwargs.keys()]) + '-x-' +  # joined input names plus...
                    parameters['cells_name'] + '-x-' + parameters['periods_name'])  # ...cells and periods names
        elif approach == 'segment':  # segment approach
            name = ('samples-' + '+'.join([name for name in kwargs.keys()]) + '-x-' +  # joined input names plus...
                    parameters['segments_name'])  # ...segments names
        else:  # unknown approach (should never be reached)
            raise ValueError

        return cls(
            samples=merged,
            name=name,
            parameters={'name': name, 'names': '+'.join([sample.name for sample in kwargs.values()])} | parameters,
            assigned=None)

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
            crs_output: str | int | pyproj.crs.crs.CRS = None,
            coords: bool = False):

        """Save the samples.

        Saves the samples GeoDataFrame as a GPKG, a CSV, or both. The name of the saved file(s) will be the name of the
         Samples object. Additionally, the parameters will be output as a CSV with the same name plus '-parameters'.

        Parameters:
            folder : str
                The path to the output folder where the output files will be saved
            filetype : {'gpkg', 'csv', 'both'}, optional, default 'gpkg'
                The type of file that the sections will be saved as.
                    gpkg: GeoPackage
                    csv: CSV
                    both: GeoPackage and CSV
            crs_output : str | int | pyproj.CRS, optional, default None
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

        output_samples = self.samples.copy()
        output_parameters = self.parameters.copy()

        if crs_output is not None:  # if CRS provided
            check_crs(par='crs_output', crs=crs_output)
            output_samples = reproject_crs(gdf=output_samples, crs_target=crs_output, additional=[c for c in ['centroid', 'midpoint'] if c in output_samples])  # reproject
            output_parameters['samples_crs'] = str(crs_output)  # update parameter
        output_samples = extract_coords(samples=output_samples) if coords else output_samples  # extract coords (if coords)

        for col in ['date', 'date_beg', 'date_mid', 'date_end']:  # for each potential date col...
            if col in output_samples:  # ...if present...
                output_samples[col] = output_samples[col].apply(  # convert date to string if there is date
                    lambda dt: dt.strftime('%Y-%m-%d') if isinstance(dt, (datetime | pd.Timestamp)) else dt)

        if filetype in ['csv', 'both']:  # if CSV
            output_samples.to_csv(folder + '/' + self.name + '.csv', index=False)  # output
        if filetype in ['gpkg', 'both']:  # if GPKG
            for col in ['centroid', 'midpoint']:  # ...for each extra geometry col...
                if col in output_samples:  # ...if present...
                    output_samples[col] = output_samples[col].to_wkt()  # ...convert to wkt
            output_samples.to_file(folder + '/' + self.name + '.gpkg')  # output

        output_parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T.reset_index()  # parameters dataframe
        output_parameters.columns = ['parameter', 'value']  # rename columns
        output_parameters.to_csv(folder + '/' + self.name + '-parameters.csv', index=False)  # output parameters

