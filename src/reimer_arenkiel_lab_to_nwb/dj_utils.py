import uuid
import datetime
from copy import deepcopy
from zoneinfo import ZoneInfo

import numpy as np
from pynwb import NWBFile, NWBHDF5IO
from pynwb.behavior import SpatialSeries
from pynwb.device import Device
from pynwb.file import Subject
from pynwb.image import GrayscaleImage
from pynwb.ophys import (
    ImageSegmentation,
    OpticalChannel,
    ImagingPlane,
    Fluorescence,
    RoiResponseSeries,
    PlaneSegmentation,
)
from scipy.interpolate import interp1d
from pynwb.base import TimeSeries, Images
import datajoint as dj
from neuroconv.tools.nwb_helpers import configure_and_write_nwbfile
from tqdm import tqdm, trange
dj.config["database.host"] = "165.227.73.182:3306"
dj.config["database.user"] = "catalystneuro_asap"
dj.config["database.password"] = "JRlab2024!"
conn = dj.conn()
conn.set_query_cache()

odor = dj.create_virtual_module("odor", "pipeline_odor")
stimulus = dj.create_virtual_module("stimulus", "pipeline_stimulus")
treadmill = dj.create_virtual_module("treadmill", "pipeline_treadmill")
mice = dj.create_virtual_module("mice", "common_mice")
meso = dj.create_virtual_module("meso", "pipeline_meso")
all_sessions = dj.create_virtual_module("all_sessions", "pipeline_experiment")


def add_treadmill(nwbfile: NWBFile, key: dict = None, verbose: bool = False) -> None:
    """Fetch treadmill data and synchronize to odor clock using linear interpolation with extrapolation"""

    if verbose:
        print(f"Adding treadmill data for {key}")

    restriction = odor.MesoMatch & key

    odor_scan_times = (odor.OdorSync & restriction).fetch1("frame_times")
    beh_scan_times = (stimulus.BehaviorSync & restriction).fetch1("frame_times")
    beh_tread_times, tread_vel, tread_raw = (treadmill.Treadmill & restriction).fetch1(
        "treadmill_time", "treadmill_vel", "treadmill_raw"
    )

    if verbose:
        if len(odor_scan_times) != len(beh_scan_times):
            print(f"Length of odor scan times: {len(odor_scan_times)}")
            print(f"Length of behavior scan times: {len(beh_scan_times)}")
    beh_odor_interp = interp1d(
        beh_scan_times, odor_scan_times[: len(beh_scan_times)], kind="linear", fill_value="extrapolate"
    )
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


def add_subject(nwbfile: NWBFile, key: dict = None, verbose: bool = False) -> None:
    """Fetch subject data and add to NWBFile"""

    if verbose:
        print(f"Adding subject data for {key}")

    subject_info = (mice.Mice & key).fetch1()
    nwbfile.subject = Subject(
        subject_id=str(subject_info["animal_id"]),
        date_of_birth=datetime.datetime.combine(subject_info['dob'], datetime.datetime.min.time()),
        sex=subject_info["sex"] if subject_info["sex"] in ("M", "F") else "U",
        description=subject_info["mouse_notes"] or "no notes",
        species="Mus Musculus",
    )


def add_odor_trials(nwbfile: NWBFile, key: dict = None, verbose: bool = False) -> None:
    """Fetch odor trials data and add to NWBFile"""

    if verbose:
        print(f"Adding odor trials for {key}")

    nwbfile.add_trial_column("odorant", "the name of the odorant")
    nwbfile.add_trial_column("concentration", "the concentration of the odorant")
    nwbfile.add_trial_column("solution_date", "the date the odorant solution was made")

    for trial in (odor.OdorTrials & key) * odor.OdorConfig:
        nwbfile.add_trial(
            start_time=trial["trial_start_time"],
            stop_time=trial["trial_end_time"],
            odorant=trial["odorant"],
            concentration=float(trial["concentration"]),
            solution_date=str(trial["solution_date"]),
        )


def add_respiration(nwbfile: NWBFile, key=None, verbose: bool = False):
    """Fetch respiration data and add to NWBFile"""

    if verbose:
        print(f"Adding respiration data for {key}")

    if not odor.Respiration & key:
        if verbose:
            print(f"No respiration data found for {key}")
        return

    resp_trace, resp_times = (odor.Respiration & key).fetch1("trace", "times")

    respiration_signal = TimeSeries(
        name="respiration",
        description="respiration rate from Respiration table",
        data=resp_trace,
        timestamps=resp_times,
        unit="unknown",
    )

    nwbfile.add_acquisition(respiration_signal)


def add_summary_images(nwbfile: NWBFile, key: dict = None, verbose: bool = False):
    """Fetch summary images data and add to NWBFile"""

    if verbose:
        print(f"Adding summary images for {key}")

    if "ophys" not in nwbfile.processing:
        nwbfile.create_processing_module(name="ophys", description="ophys data processing")

    avg_images = [
        GrayscaleImage(
            name=f"average_image_FOV{img_row['field']}_channel{img_row['channel']}",
            description="average image from SummaryImages.Average table",
            data=img_row["average_image"],
        )
        for img_row in (meso.SummaryImages.Average() & key)
    ]

    nwbfile.processing["ophys"].add(Images("average_images", avg_images))

    corr_images = [
        GrayscaleImage(
            name=f"correlation_image_FOV{img_row['field']}_channel{img_row['channel']}",
            description="correlation image from SummaryImages.Correlation table",
            data=img_row["correlation_image"],
        )
        for img_row in (meso.SummaryImages.Correlation() & key)
    ]

    nwbfile.processing["ophys"].add(Images("correlation_images", corr_images))


default_ophys_metadata = dict(
    NWBFile=dict(
        institution="Baylor College of Medicine",
        keywords=["odor", "olfaction", "calcium imaging", "mesoscope"],
    ),
    Ophys=dict(
        Device=dict(
            name="two_photon_microscope",
            description="Janelia 2P-RAM mesoscope.",
            manufacturer="ThorLabs",
        ),
        OpticalChannel=dict(
            name="green_channel",
            description="Emitted light was collected through a 525/50 filter and a gallium arsenide phosphide "
                        "photomultiplier tube (Hamamatsu).",
            emission_lambda=525.0,
        ),
        ImagingPlane=dict(
            name="imaging_plane",
            description="Imaging plane for the Green channel recorded with 2p microscope.",
            excitation_lambda=920.0,
            indicator="GCaMP6f",
            location="Whole Brain",
        ),
    )
)


def add_imaging_plane(
        nwbfile: NWBFile, device: Device, key: dict = None, metadata: dict = None, verbose: bool = False
) -> ImagingPlane:
    """Fetch imaging plane metadata and add to NWBFile"""
    
    if verbose:
        print(f"Adding imaging plane for {key}")

    metadata = metadata or default_ophys_metadata

    optical_channel = OpticalChannel(**metadata["Ophys"]["OpticalChannel"])

    imaging_plane = nwbfile.create_imaging_plane(
        **metadata["Ophys"]["ImagingPlane"],
        optical_channel=optical_channel,
        device=device,
    )

    return imaging_plane


def add_plane_segmentation(
        nwbfile: NWBFile, imaging_plane: ImagingPlane, key: dict = None, metadata: dict = None, verbose: bool = False
) -> PlaneSegmentation:
    """Fetch segmentation data and add to NWBFile"""

    if verbose:
        print(f"Adding plane segmentation for {key}")

    field, channel, segmentation_method = key["field"], key["channel"], key["segmentation_method"]

    if "ophys" not in nwbfile.processing:
        nwbfile.create_processing_module(name="ophys", description="ophys data processing")

    avg_image = (meso.SummaryImages.Average & key).fetch1("average_image")

    if f"ImageSegmentation{segmentation_method}" not in nwbfile.processing["ophys"].data_interfaces:
        img_seg = ImageSegmentation(name=f"ImageSegmentation{segmentation_method}")
        nwbfile.processing["ophys"].add(img_seg)
    else:
        img_seg = nwbfile.processing["ophys"].data_interfaces[f"ImageSegmentation{segmentation_method}"]

    ps = img_seg.create_plane_segmentation(
        name=f"plane_segmentation_FOV{field}",
        description=f"Output from segmenting FOV{field}.",
        imaging_plane=imaging_plane,
    )

    for mask_row in meso.Segmentation.Mask & key:  # iterate over masks
        mask_idx = mask_row["pixels"]
        mask = np.unravel_index(
            np.ndarray.astype(mask_idx, "int64"), avg_image.shape, order="F"
        )  # Convert from Fortran-style indices
        vals = mask_row["weights"].ravel()
        pixel_mask = [[x[0], y[0], v] for v, x, y in zip(vals, *mask)]
        ps.add_roi(pixel_mask=pixel_mask)

    return ps


def add_fluorescence(nwbfile, plane_segmentation, key: dict = None, verbose: bool = False) -> None:
    """Fetch fluorescence trace and add to NWBFile"""

    if verbose:
        print(f"Adding fluorescence trace for {key}")

    field, channel, segmentation_method = key["field"], key["channel"], key["segmentation_method"]

    restriction = (
            odor.MesoMatch & key
    )  # Since tables can be restrictions, saving this shorthand simplifies following code

    fluorescence_trace = np.vstack((meso.Fluorescence.Trace & key).fetch("trace")).T
    odor_scan_times = (odor.OdorSync & restriction).fetch1("frame_times")

    if verbose:
        if len(fluorescence_trace) != len(odor_scan_times):
            print(f"Length of fluorescence trace: {len(fluorescence_trace)}")
            print(f"Length of odor scan times: {len(odor_scan_times)}")

    if "ophys" not in nwbfile.processing:
        nwbfile.create_processing_module(name="ophys", description="ophys data processing")

    rt_region = plane_segmentation.create_roi_table_region(region=slice(None), description="all ROIs")

    roi_response_series = RoiResponseSeries(
        name=f"fluorescence_FOV{field}",
        description=f"Fluorescence traces from FOV{field}",
        data=fluorescence_trace,
        unit="n.a.",
        timestamps=odor_scan_times[:len(fluorescence_trace)],
        rois=rt_region,
    )

    if f"Fluorescence{segmentation_method}" not in nwbfile.processing["ophys"].data_interfaces:
        fluoresence = Fluorescence(name=f"Fluorescence{segmentation_method}")
        nwbfile.processing["ophys"].add(fluoresence)
    else:
        fluoresence = nwbfile.processing["ophys"].data_interfaces[f"Fluorescence{segmentation_method}"]
    fluoresence.add_roi_response_series(roi_response_series)

def get_imaging_start_time(key: dict = None):
    restriction = (
            odor.MesoMatch & key
    )  # Since tables can be restrictions, saving this shorthand simplifies following code
    odor_scan_times = (odor.OdorSync & restriction).fetch1("frame_times")
    return odor_scan_times[0]

def init_nwbfile(key: dict, metadata: dict = None) -> NWBFile:
    data = (all_sessions.Session & key).fetch1()
    metadata = metadata or default_ophys_metadata

    nwbfile_kwargs = deepcopy(metadata["NWBFile"])

    nwbfile_kwargs.update(dict(
        session_description=f"animal {data['animal_id']} session {data['session']}",
        session_id=str(data["session"]),
        identifier=str(uuid.uuid4()),
        session_start_time=datetime.datetime.combine(
            data["session_date"], datetime.time(0, 0)
        ).replace(tzinfo=ZoneInfo("America/Chicago"))
    ))

    nwbfile = NWBFile(**nwbfile_kwargs)

    return nwbfile


def make_session_nwbfile(key, verbose=False):
    nwbfile = init_nwbfile(key=key)
    add_treadmill(nwbfile, key=key, verbose=verbose)
    add_subject(nwbfile, key=key, verbose=verbose)
    add_odor_trials(nwbfile, key=key, verbose=verbose)
    add_respiration(nwbfile, key=key, verbose=verbose)
    add_summary_images(nwbfile, key=key, verbose=verbose)

    device = nwbfile.create_device(**default_ophys_metadata["Ophys"]["Device"])

    # ophys_keys include all the field, channel, and segmentation_method associated with this session. We will iterate over
    ophys_keys = [ophys_key for ophys_key in meso.Segmentation() & key]

    # iterate over each ophys_key
    for ophys_key in tqdm(ophys_keys, desc="Processing imaging planes"):
        imaging_plane = add_imaging_plane(nwbfile, key=ophys_key, verbose=verbose, device=device)
        plane_segmentation = add_plane_segmentation(nwbfile, imaging_plane, key=ophys_key, verbose=verbose)
        add_fluorescence(nwbfile, plane_segmentation, key=ophys_key, verbose=verbose)

    return nwbfile


def get_session_keys():
    return [key for key in odor.MesoMatch()]


def get_ophys_keys(key: dict):
    return [ophys_key for ophys_key in meso.Segmentation() & key]


if __name__ == "__main__":
    verbose = True

    keys = [key for key in odor.MesoMatch()]

    for key in tqdm(keys, desc="Processing sessions"):
        nwbfile = make_session_nwbfile(key, verbose=verbose)
        fpath = f"sub-{key['animal_id']}_session-{key['session']}.nwb"

        # with NWBHDF5IO(fpath, mode="w") as io:
        #     io.write(nwbfile)

        # this threw an error when configuring datasets. Let's save uncompressed datasets for now
        configure_and_write_nwbfile(nwbfile=nwbfile, backend="hdf5", output_filepath=fpath)
