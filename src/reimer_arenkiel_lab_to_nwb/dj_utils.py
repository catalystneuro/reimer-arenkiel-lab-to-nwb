import numpy as np
from pynwb import NWBFile
from pynwb.behavior import SpatialSeries
from pynwb.file import Subject
from pynwb.image import GrayscaleImage
from pynwb.ophys import ImageSegmentation, OpticalChannel, ImagingPlane, Fluorescence, RoiResponseSeries, \
    PlaneSegmentation
from scipy.interpolate import interp1d
from pynwb.base import TimeSeries, Images
import datajoint as dj
from neuroconv.tools.nwb_helpers import configure_and_write_nwbfile


dj.conn()

odor = dj.create_virtual_module('odor', 'pipeline_odor')
stimulus = dj.create_virtual_module('stimulus', 'pipeline_stimulus')
treadmill = dj.create_virtual_module('treadmill', 'pipeline_treadmill')
mice = dj.create_virtual_module('mice', 'common_mice')
odor = dj.create_virtual_module('odor', 'pipeline_odor')
meso = dj.create_virtual_module('meso', 'pipeline_meso')


def add_treadmill(nwbfile: NWBFile, key: dict = None):
    """Fetch treadmill data and synchronize to odor clock using linear interpolation with extrapolation"""

    key = key or {'animal_id': 124, 'odor_session': 4}

    restriction = odor.MesoMatch & key

    odor_scan_times = (odor.OdorSync & restriction).fetch1('frame_times')
    beh_scan_times = (stimulus.BehaviorSync & restriction).fetch1('frame_times')
    beh_tread_times, tread_vel, tread_raw = (treadmill.Treadmill & restriction).fetch1('treadmill_time', 'treadmill_vel', 'treadmill_raw')

    beh_odor_interp = interp1d(beh_scan_times, odor_scan_times,  kind='linear', fill_value="extrapolate")
    odor_tread_times = beh_odor_interp(beh_tread_times)

    treadmill_raw_spatial_series = SpatialSeries(
        name="treadmill_position",
        description="treadmill position from Treadmill table",
        data=tread_raw,
        timestamps=odor_tread_times,
        reference_frame="unknown",
    )

    nwbfile.add_acquisition(treadmill_raw_spatial_series)

    if "behavior" not in nwbfile.processing:
        nwbfile.create_processing_module(name="behavior", description="behavioral data processing")

    nwbfile.processing["behavior"].add(
        TimeSeries(
            name="treadmill_velocity",
            description="treadmill velocity from Treadmill table",
            data=tread_vel,
            timestamps=treadmill_raw_spatial_series,
            unit="unknown",
        )
    )


def add_subject(nwbfile: NWBFile, key: dict = None):
    """Fetch subject data and add to NWBFile"""

    key = {'animal_id': 125}

    subject_info = (mice.Mice & key).fetch1()
    nwbfile.subject = Subject(
        subject_id=str(subject_info['animal_id']),
        date_of_birth=subject_info['dob'],
        sex=subject_info["sex"] if subject_info["sex"] in ("M", "F") else "U",
    )

    return nwbfile


def add_odor_trials(nwbfile: NWBFile, key: dict = None):
    """Fetch odor trials data and add to NWBFile"""

    key = key or {'animal_id': 125, 'odor_session': 0}

    nwbfile.add_trial_column("odorant", "the name of the odorant")
    nwbfile.add_trial_column("concentration", "the concentration of the odorant")
    nwbfile.add_trial_column("solution_date", "the date the odorant solution was made")

    for trial in ((odor.OdorTrials & key) * odor.OdorConfig):

        nwbfile.add_trial(
            start_time=trial['trial_start_time'],
            stop_time=trial['trial_end_time'],
            odorant=trial['odorant'],
            concentration=trial['concentration'],
            solution_date=trial['solution_date'],
        )

    return nwbfile


def add_respiration(nwbfile: NWBFile, key=None):
    """Fetch respiration data and add to NWBFile"""

    key = key or {'animal_id': 124, 'odor_session': 4, 'recording_idx': 2}

    resp_trace, resp_times = (odor.Respiration & key).fetch1('trace', 'times')

    respiration_signal = TimeSeries(
        name="respiration",
        description="respiration rate from Respiration table",
        data=resp_trace,
        timestamps=resp_times,
        unit="unknown",
    )

    nwbfile.add_acquisition(respiration_signal)

    return nwbfile


def add_summary_images(nwbfile, key=None):
    key = key or {
        'animal_id': 124,
        'session': 3,
        'scan_idx': 1,
        'pipeline_version': 1,
    }

    if "ophys" not in nwbfile.processing:
        nwbfile.create_processing_module(name="ophys", description="ophys data processing")

    avg_images = [
        GrayscaleImage(
            name=f"average_image_field{img_row['field']}_channel{img_row['channel']}",
            description="average image from SummaryImages.Average table",
            data=img_row["average_image"],
        ) for img_row in (meso.SummaryImages.Average() & key)
    ]

    nwbfile.processing["ophys"].add(Images("average_images", avg_images))

    corr_images = [
        GrayscaleImage(
            name=f"correlation_image_field{img_row['field']}_channel{img_row['channel']}",
            description="correlation image from SummaryImages.Correlation table",
            data=img_row["correlation_image"],
        ) for img_row in (meso.SummaryImages.Correlation() & key)
    ]

    nwbfile.processing["ophys"].add(Images("correlation_images", corr_images))


def add_imaging_plane(nwbfile: NWBFile, key: dict = None, metadata: dict = None) -> ImagingPlane:
    key = key or {
        'animal_id': 125,
        'session': 1,
        'scan_idx': 1,
        'pipe_version': 1,
        'field': 1,
        'channel': 1,
    }

    field, channel = key['field'], key['channel']

    device = nwbfile.create_device(
        name="Microscope",
        description="My two-photon microscope",
        manufacturer="The best microscope manufacturer",
    )

    optical_channel = OpticalChannel(
        name="OpticalChannel",
        description="an optical channel",
        emission_lambda=500.0,
    )

    imaging_plane = nwbfile.create_imaging_plane(
        name=f"ImagingPlane_field{field}_channel{channel}",
        optical_channel=optical_channel,
        imaging_rate=30.0,
        description=f"Imaging plane for field {field} channel {channel}",
        device=device,
        excitation_lambda=600.0,
        indicator="GFP",
        location="V1",
        # grid_spacing=[0.01, 0.01],
        # grid_spacing_unit="meters",
        # origin_coords=[1.0, 2.0, 3.0],
        # origin_coords_unit="meters",
    )

    return imaging_plane


def add_plane_segmentation(
    nwbfile: NWBFile, imaging_plane: ImagingPlane, key: dict = None, metadata: dict = None
) -> PlaneSegmentation:

    key = key or {
        'animal_id': 125,
        'session': 1,
        'scan_idx': 1,
        'pipe_version': 1,
        'field': 1,
        'channel': 1,
        'segmentation_method': 1,
    }

    field, channel, segmentation_method = key['field'], key['channel'], key['segmentation_method']

    if "ophys" not in nwbfile.processing:
        nwbfile.create_processing_module(name="ophys", description="ophys data processing")

    avg_image = (meso.SummaryImages.Average & key).fetch1('average_image')

    img_seg = ImageSegmentation()

    ps = img_seg.create_plane_segmentation(
        name=f"PlaneSegmentation_field{field}_channel{channel}_segmentation-method{segmentation_method}",
        description="output from segmenting my favorite imaging plane",
        imaging_plane=imaging_plane,
    )

    for mask_row in meso.Segmentation.Mask & key:  # iterate over masks
        mask_idx = mask_row["pixels"]
        mask = np.unravel_index(np.ndarray.astype(mask_idx,'int64'), avg_image.shape, order='F') # Convert from Fortran-style indices
        vals = mask_row["weights"].ravel()
        pixel_mask = [[x[0], y[0], v] for v, x, y in zip(vals, *mask)]
        ps.add_roi(pixel_mask=pixel_mask)

    nwbfile.processing["ophys"].add(img_seg)

    return ps


def add_fluorescence(nwbfile, plane_segmentation, key=None):
    key = key or {
        'animal_id': 125,
        'session': 1,
        'scan_idx': 1,
        'pipe_version': 1,
        'field': 1,
        'channel': 1,
        'segmentation_method': 1,
    }

    field, channel, segmentation_method = key['field'], key['channel'], key['segmentation_method']

    restriction = odor.MesoMatch & key  # Since tables can be restrictions, saving this shorthand simplifies following code

    fluorescence_trace = np.vstack((meso.Fluorescence.Trace & key).fetch("trace")).T
    odor_scan_times = (odor.OdorSync & restriction).fetch1('frame_times')

    if "ophys" not in nwbfile.processing:
        nwbfile.create_processing_module(name="ophys", description="ophys data processing")

    rt_region = plane_segmentation.create_roi_table_region(
        region=slice(None), description="all ROIs"
    )

    roi_response_series = RoiResponseSeries(
        name=f"Fluorescence_field{field}_channel{channel}_segmentation-method{segmentation_method}",
        description="Fluorescence trace from imaging plane",
        data=fluorescence_trace,
        unit="n.a.",
        timestamps=odor_scan_times,
        rois=rt_region,
    )

    fluoresence = Fluorescence([roi_response_series])
    nwbfile.processing["ophys"].add(fluoresence)

    return nwbfile


## test
from pynwb.testing.mock.file import mock_NWBFile

key = {
    'animal_id': 125,
    'session': 1,
    'scan_idx': 1,
    'pipe_version': 1,
    'field': 1,
    'channel': 1,
    'segmentation_method': 1,
}

nwbfile = mock_NWBFile()

add_treadmill(nwbfile, key=key)
add_subject(nwbfile, key=key)
add_odor_trials(nwbfile, key=key)
add_respiration(nwbfile, key={'animal_id': 124, 'odor_session': 4, 'recording_idx': 2})

# iterate over fields

add_summary_images(nwbfile, key=key)
imaging_plane = add_imaging_plane(nwbfile, key=key)
plane_segmentation = add_plane_segmentation(nwbfile, imaging_plane=imaging_plane, key=key)
add_fluorescence(nwbfile, plane_segmentation=plane_segmentation, key=key)

#configure_and_write_nwbfile(nwbfile=nwbfile, backend="hdf5", output_filepath="test.nwb")

with NWBHDF5IO("test.nwb", mode="w") as io:
    io.write(nwbfile)

# print(
#     nwbfile.processing["ophys"].
#     data_interfaces["ImageSegmentation"].
#     plane_segmentations["PlaneSegmentation_field1_channel1_segmentation-method1"].
#     to_dataframe()
# )

