from pynwb import NWBFile
from pynwb.behavior import SpatialSeries
from pynwb.file import Subject
from pynwb.image import GrayscaleImage
from scipy.interpolate import interp1d
from pynwb.base import TimeSeries, Images
import datajoint as dj


dj.conn()

odor = dj.create_virtual_module('odor', 'pipeline_odor')
stimulus = dj.create_virtual_module('stimulus', 'pipeline_stimulus')
treadmill = dj.create_virtual_module('treadmill', 'pipeline_treadmill')
mice = dj.create_virtual_module('mice', 'common_mice')
odor = dj.create_virtual_module('odor', 'pipeline_odor')
meso = dj.create_virtual_module('meso', 'pipeline_meso')


def add_treadmill(nwbfile: NWBFile, animal_id: int = 125, odor_session: int = 0):
    """Fetch treadmill data and synchronize to odor clock using linear interpolation with extrapolation"""

    restriction = odor.MesoMatch & {'animal_id':animal_id, 'odor_session': odor_session}

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


def add_subject(nwbfile: NWBFile, animal_id: int = 125):
    """Fetch subject data and add to NWBFile"""

    subject_info = (mice.Mice & {'animal_id':animal_id}).fetch1()
    nwbfile.subject = Subject(
        subject_id=str(subject_info['animal_id']),
        date_of_birth=subject_info['dob'],
        sex=subject_info["sex"] if subject_info["sex"] in ("M", "F") else "U",
    )

    return nwbfile


def add_odor_trials(nwbfile: NWBFile, animal_id: int = 125, odor_session: int = 0):
    """Fetch odor trials data and add to NWBFile"""

    key = {'animal_id': animal_id, 'odor_session': odor_session}

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





from pynwb.testing.mock.file import mock_NWBFile


nwbfile = mock_NWBFile()

# add_treadmill(nwbfile)
# add_subject(nwbfile)
# add_odor_trials(nwbfile)
# add_respiration(nwbfile, key={'animal_id': 124, 'odor_session': 4, 'recording_idx': 2})
add_summary_images(nwbfile)

print(nwbfile.processing["ophys"].data_interfaces["correlation_images"])
