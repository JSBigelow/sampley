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
            tz_input: str | timezone | pytz.BaseTzInfo | None = None,
            tz_working: str | timezone | pytz.BaseTzInfo | None = None,
            datapoint_id_col: str = None,
            section_id_col: str = None):

        datapoints = datapoints_from_file(
            filepath=filepath,
            x_col=x_col,
            y_col=y_col,
            geometry_col=geometry_col,
            crs_input=crs_input,
            crs_working=crs_working,
            datetime_col=datetime_col,
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

    def plot(self, sections=None):
        fig, ax = plt.subplots(figsize=(16, 8))
        datapoints_plot(ax, self.datapoints)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None

    def save(self, folder, filetype: str = 'gpkg'):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        check_dtype(par='filetype', obj=filetype, dtypes=str)
        filetype = filetype.lower()
        check_opt(par='filetype', opt=filetype, opts=['csv', 'gpkg', 'both'])

        datapoints = self.datapoints.copy()
        datapoints['datetime'] = datapoints['datetime'].apply(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'None')
        datapoints.to_csv(folder + '/' + self.name + '.csv', index=False) if filetype in ['csv', 'both'] else None
        datapoints.to_file(folder + '/' + self.name + '.gpkg') if filetype in ['gpkg', 'both'] else None


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
            tz_input: str | timezone | pytz.BaseTzInfo | None = None,
            tz_working: str | timezone | pytz.BaseTzInfo | None = None,
            section_id_col: str | None = None):

        sections = sections_from_file(
            filepath=filepath,
            crs_working=crs_working,
            datetime_col=datetime_col,
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

        if 'section_id' not in datapoints.datapoints:
            raise Exception('\n\n____________________'
                            f'\nKeyError: the datapoints GeoDataFrame does not have a section ID column.'
                            f'\nPlease ensure that \'section_id_col\' is specified when making the DataPoints object'
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
                'sections_filepath': datapoints.parameters['datapoints_filepath'] + ' (via datapoints)',
                'sections_crs': datapoints.parameters['datapoints_crs'],
                'sections_tz': datapoints.parameters['datapoints_tz']})

    def plot(self, datapoints=None):
        fig, ax = plt.subplots(figsize=(16, 8))
        sections_plot(ax, self.sections)
        datapoints_plot(ax, datapoints.datapoints) if isinstance(datapoints, DataPoints) else None

    def save(self, folder, filetype: str = 'gpkg'):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        check_dtype(par='filetype', obj=filetype, dtypes=str)
        filetype = filetype.lower()
        check_opt(par='filetype', opt=filetype, opts=['csv', 'gpkg', 'both'])

        sections = self.sections.copy()
        sections['datetime'] = sections['datetime'].apply(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'None')
        sections.to_csv(folder + '/' + self.name + '.csv', index=False) if filetype in ['csv', 'both'] else None
        sections.to_file(folder + '/' + self.name + '.gpkg') if filetype in ['gpkg', 'both'] else None


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
            tz = str(periods['datetime_beg'].dtype.tz)
        except AttributeError:
            tz = None

        return cls(
            periods=periods,
            name='periods-' + str(int(num)) + unit[0],
            parameters={
                'periods_tz': tz,
                'periods_extent': periods['datetime_beg'].min().strftime('%Y-%m-%d %H:%M:%S') + '-' +
                                  periods['datetime_end'].max().strftime('%Y-%m-%d %H:%M:%S'),
                'periods_extent_source': source,
                'periods_number': num,
                'periods_unit': unit})

    def save(self, folder: str, tz_output: str | timezone | pytz.BaseTzInfo = None):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_periods = self.periods.copy()
        if tz_output is not None:
            check_tz(par='tz_output', tz=tz_output)
            output_periods = convert(output_periods, tz_output)
        for col in ['datetime_beg', 'datetime_mid', 'datetime_end']:
            if col in output_periods:
                output_periods[col] = output_periods[col].apply(lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'None')
        output_periods.to_csv(folder + '/' + self.name + '.csv', index=False)


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

    def plot(self, datapoints: DataPoints = None, sections: Sections = None):
        fig, ax = plt.subplots(figsize=(16, 8))
        cells_plot(ax, self.cells)
        datapoints_plot(ax, datapoints.datapoints) if isinstance(datapoints, DataPoints) else None
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_cells = self.cells.copy()
        if crs_output is not None:
            check_crs(par='crs_output', crs=crs_output)
            output_cells = reproject(output_cells, crs_output)

        output_cells[['cell_id', 'polygon']].to_file(folder + '/' + self.name + '-polygons.gpkg')
        output_cells[['cell_id', 'centroid']].to_file(folder + '/' + self.name + '-centroids.gpkg')


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
            randomise: bool = False):

        segments = segments_delimit(
            sections=sections.sections,
            var=var,
            target=target,
            rand=randomise)

        crs = segments.crs
        unit = crs.axis_info[0].unit_name
        return cls(
            segments=segments,
            name='segments-' + var[0] + str(target) + unit[0],
            parameters={
                'sections_name': sections.name,
                'segments_crs': str(crs),
                'segments_var': var,
                'segments_randomise': randomise,
                'segments_target': target,
                'segments_unit': unit})

    def plot(self, sections: Sections = None, datapoints: DataPoints = None):
        fig, ax = plt.subplots(figsize=(16, 8))
        segments_plot(ax, self.segments)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None
        datapoints_plot(ax, datapoints.datapoints) if isinstance(datapoints, DataPoints) else None

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_segments = self.segments.copy()
        if crs_output is not None:
            check_crs(par='crs_output', crs=crs_output)
            output_segments = reproject(output_segments, crs_output)

        output_segments[['segment_id', 'line']].to_file(folder + '/' + self.name + '-lines.gpkg')
        output_segments[['segment_id', 'midpoint']].to_file(folder + '/' + self.name + '-midpoints.gpkg')


class Presences:
    def __init__(self, full, name, parameters):
        self.full = full
        self.kept = None
        self.removed = None
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of presences_delimit()
            cls,
            datapoints: DataPoints,
            presence_col: str = None):

        full = presences_delimit(
            datapoints=datapoints.datapoints,
            presence_col=presence_col)

        crs = full.crs
        return cls(
            full=full,
            name='presences-' + datapoints.name[11:],
            parameters={'presences_crs': str(crs)})

    def thin(
            self,
            sp_threshold: int | float,
            tm_threshold: int | float,
            tm_unit: str = 'day',
            target: int = None):

        kept = thinst(
            df=self.full,
            points='point',
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
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_full = self.full.copy()
        if crs_output is not None:
            check_crs(par='crs_output', crs=crs_output)
            output_full = reproject(output_full, crs_output)
        output_full.to_file(folder + '/' + self.name + '-full.gpkg')

        if isinstance(self.kept, gpd.GeoDataFrame):
            output_kept = self.kept.copy()
            if crs_output is not None:
                output_kept = reproject(output_kept, crs_output)
            output_kept.to_file(folder + '/' + self.name + '-kept.gpkg')

        if isinstance(self.removed, gpd.GeoDataFrame):
            output_removed = self.removed.copy()
            if crs_output is not None:
                output_removed = reproject(output_removed, crs_output)
            output_removed.to_file(folder + '/' + self.name + '-removed.gpkg')


class AbsenceLines:
    def __init__(self, absencelines, name, parameters):
        self.absencelines = absencelines
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of absencelines_delimit()
            cls,
            sections: Sections,
            presences: Presences,
            sp_threshold: int | float = None,
            tm_threshold: int | float = None,
            tm_unit: str | None = None):

        absencelines = absencelines_delimit(
            sections=sections.sections,
            presences=presences.full,
            sp_threshold=sp_threshold,
            tm_threshold=tm_threshold,
            tm_unit=tm_unit)

        crs = absencelines.crs
        unit = crs.axis_info[0].unit_name

        if isinstance(tm_threshold, (int, float)) and isinstance(tm_unit, str):
            name = 'absencelines-' + str(sp_threshold) + unit[0] + '-' + str(tm_threshold) + tm_unit
        else:
            name = 'absencelines-' + str(sp_threshold) + unit[0] + '-none'

        return cls(
            absencelines=absencelines,
            name=name,
            parameters={
                'absences_crs': str(crs),
                'absences_sp_threshold': sp_threshold,
                'absences_tm_threshold': tm_threshold,
                'absences_tm_unit': tm_unit})

    def plot(self, sections: Sections = None, presences: Presences = None):
        fig, ax = plt.subplots(figsize=(16, 8))
        absencelines_plot(ax, self.absencelines)
        sections_plot(ax, sections.sections) if isinstance(sections, Sections) else None
        presences_plot(ax, presences.full, buffer=self.parameters['absences_sp_threshold']) if isinstance(presences, Presences) else None

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_lines = self.absencelines.copy()
        if crs_output is not None:
            check_crs(par='crs_output', crs=crs_output)
            output_lines = reproject(output_lines, crs_output)

        output_lines[['section_id', 'date', 'absencelines']].to_file(folder + '/' + self.name + '-absencelines.gpkg')
        output_lines[['section_id', 'date', 'presencezones']].to_file(folder + '/' + self.name + '-presencezones.gpkg')


class Absences:
    def __init__(self, full, name, parameters):
        self.full = full
        self.kept = None
        self.removed = None
        self.name = name
        self.parameters = parameters

    @classmethod
    def delimit(  # wrapper of absences_delimit()
            cls,
            absencelines: AbsenceLines,
            var: str,
            target: int | float,
            dfls: list[int | float] = None):

        full = absences_delimit(
            absencelines=absencelines.absencelines,
            var=var,
            target=target,
            dfls=dfls)

        return cls(
            full=full,
            name='absences-' + var[0] + absencelines.name[12:],
            parameters={'absences_var': var, 'absences_target': target} | absencelines.parameters)

    def thin(
            self,
            sp_threshold: int | float,
            tm_threshold: int | float,
            tm_unit: str = 'day',
            target: int = None):

        kept = thinst(
            df=self.full,
            points='point',
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

    def plot(self, sp_threshold: int | float = None, which: str = 'full', absencelines: AbsenceLines = None):
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
        absencelines_plot(ax=ax, lines=absencelines.absencelines) if isinstance(absencelines, AbsenceLines) else None

    def save(self, folder: str, crs_output: str | int | pyproj.crs.crs.CRS = None):
        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        output_full = self.full.copy()
        if crs_output is not None:
            check_crs(par='crs_output', crs=crs_output)
            output_full = reproject(output_full, crs_output)
        output_full.to_file(folder + '/' + self.name + '-full.gpkg')

        if isinstance(self.kept, gpd.GeoDataFrame):
            output_kept = self.kept.copy()
            if crs_output is not None:
                output_kept = reproject(output_kept, crs_output)
            output_kept.to_file(folder + '/' + self.name + '-kept.gpkg')

        if isinstance(self.removed, gpd.GeoDataFrame):
            output_removed = self.removed.copy()
            if crs_output is not None:
                output_removed = reproject(output_removed, crs_output)
            output_removed.to_file(folder + '/' + self.name + '-removed.gpkg')


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

        # make a DataFrame of all the parameters and their values from all input Samples
        parameters_list = []  # list for parameters
        for samples in kwargs.values():  # for each samples, append its parameters to list
            parameters_list.append(pd.DataFrame({key: [samples.parameters[key]] for key in samples.parameters.keys()}))
        parameters_df = pd.concat(parameters_list).reset_index(drop=True)  # parameters DataFrame

        # check the approach
        approach = parameters_df['approach'].unique()
        if len(approach) > 1:  # if more than one approach used to get samples
            raise Exception('\n\n____________________'
                            'Error: samples generated with different approaches and should not be merged.'
                            f'\nApproaches are: {', '.join(approach)}'
                            '\n____________________')
        else:  # else only one approach used
            approach = approach[0]  # get approach
            if approach in ['grid', 'segment']:
                print(f'\nNote: samples generated with the {approach} approach')
            elif approach in ['point']:
                raise Exception('\n\n____________________'
                                'Error: samples generated with point approach cannot be merged.'
                                '\n____________________')
            else:
                raise ValueError('\n\n____________________'
                                 'ValueError: Samples generated with unrecognised approach.'
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
                              'segments_var', 'segments_randomise', 'segments_target', 'segments_unit']
        else:  # unknown approach (should never be reached)
            raise ValueError
        for parameter_key in parameters_key:  # for each key parameter
            if parameter_key in parameters_df:  # if it is present in the parameters dataframe
                if len(parameters_df[parameter_key].unique()) > 1:  # if there is more than one unique value...
                    print(f'Warning: The samples have different parameter values for \'{parameter_key}\'. '
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

    def save(
            self,
            folder: str,
            filetype: str = 'both',
            crs_output: str | int | pyproj.crs.crs.CRS = None,
            tz_output: str | timezone | pytz.BaseTzInfo = None,
            coords: bool = True):

        check_dtype(par='folder', obj=folder, dtypes=str)
        folder = folder + '/' if folder[-1] != '/' else folder

        check_dtype(par='filetype', obj=filetype, dtypes=str)
        filetype = filetype.lower()
        check_opt(par='filetype', opt=filetype, opts=['csv', 'gpkg'])

        output_samples = self.samples.copy()
        output_parameters = self.parameters.copy()

        if crs_output is not None:  # if CRS provided
            check_crs(par='crs_output', crs=crs_output)
            output_samples = reproject(output_samples, crs_output)  # reproject
            output_parameters['samples_crs'] = str(crs_output)  # update parameter
        output_samples = extract(samples=output_samples) if coords else output_samples  # extract coords (if coords)

        if tz_output is not None:  # if TZ provided
            check_tz(par='tz_output', tz=tz_output)
            output_samples = convert(output_samples, tz_output)  # convert
            output_parameters['samples_tz'] = str(tz_output)  # update parameter
        for col in ['datetime', 'datetime_beg', 'datetime_mid', 'datetime_end']:  # for each potential datetime col...
            if col in output_samples:  # ...if present...
                output_samples[col] = output_samples[col].apply(  # convert datetime to string if there is datetime
                    lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'None')

        if filetype in ['csv', 'both']:  # if CSV
            output_samples.to_csv(folder + '/' + self.name + '.csv', index=False)  # output
        if filetype in ['gpkg', 'both']:  # if GPKG
            for col in ['centroid', 'midpoint']:  # ...for each extra geometry col...
                if col in output_samples:  # ...if present...
                    output_samples[col] = output_samples[col].to_wkt()  # ...convert to wkt
            output_samples.to_file(folder + '/' + self.name + '.gpkg')  # output

        parameters = pd.DataFrame({key: [value] for key, value in output_parameters.items()}).T  # parameters dataframe
        parameters.to_csv(folder + '/' + self.name + '-parameters.csv')  # output parameters

