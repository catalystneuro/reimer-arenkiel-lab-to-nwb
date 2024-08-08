"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from tqdm import tqdm
from neuroconv.utils import load_dict_from_file, dict_deep_update
from neuroconv.tools.nwb_helpers import configure_and_write_nwbfile

from reimer_arenkiel_lab_to_nwb.embargo2024 import Embargo2024NWBConverter
from reimer_arenkiel_lab_to_nwb.dj_utils import (
    init_nwbfile,
    add_treadmill,
    add_subject,
    add_odor_trials,
    add_respiration,
    add_summary_images,
    get_ophys_keys,
    add_plane_segmentation,
    add_fluorescence,
    get_session_keys
)


def session_to_nwb(
        data_dir_path: Union[str, Path], output_dir_path: Union[str, Path], key: dict, stub_test: bool = False,
        verbose: bool = True
):
    data_dir_path = Path(data_dir_path)
    folder_path = data_dir_path / f"{key['animal_id']}_{key['session']}_{key['scan_idx']}"
    if not folder_path.is_dir():
        print(f"{folder_path} is not a directory")

    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"sub-{key['animal_id']}_ses-{key['session']}.nwb"

    source_data = dict()
    conversion_options = dict()

    ophys_metadata_path = Path(__file__).parent / "metadata" / "embargo2024_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)

    editable_metadata_path = Path(__file__).parent / "embargo2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)

    nwbfile = init_nwbfile(key=key, metadata=editable_metadata)

    # ophys_keys include all the field, channel, and segmentation_method associated with this session. We will iterate over
    ophys_keys = get_ophys_keys(key=key)

    # iterate over each ophys_key
    file_pattern = f"{key['animal_id']}_{key['session']}_*.tif"
    photon_series_index = 0
    for ophys_key in ophys_keys:
        interface_name = f"ImagingFOV{ophys_key['field']}Channel{ophys_key['channel']}"
        source_data[interface_name] = {
            "folder_path": str(folder_path),
            "file_pattern": file_pattern,
            "channel_name": f"Channel {ophys_key['channel']}",
            "field": ophys_key['field'],
        }
        conversion_options[interface_name] = {
            "stub_test": stub_test,
            "photon_series_index": photon_series_index,
            "photon_series_type": "TwoPhotonSeries",
        }
        photon_series_index += 1

    converter = Embargo2024NWBConverter(source_data=source_data)

    converter.temporally_align_data_interfaces(key=key)

    # Add datetime to conversion
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    metadata = dict_deep_update(metadata, editable_metadata)

    # Add ophys metadata
    metadata.pop("Ophys", None)
    metadata = dict_deep_update(metadata, ophys_metadata)

    # Run conversion
    if verbose:
        print("Add raw imaging data to NWB file")
    converter.add_to_nwbfile(
        metadata=metadata, nwbfile=nwbfile, conversion_options=conversion_options
    )

    add_treadmill(nwbfile, key=key, verbose=verbose)
    add_subject(nwbfile, key=key, verbose=verbose)
    add_odor_trials(nwbfile, key=key, verbose=verbose)
    add_respiration(nwbfile, key=key, verbose=verbose)
    add_summary_images(nwbfile, key=key, verbose=verbose)

    for ophys_key in tqdm(ophys_keys, desc="Processing imaging planes"):
        if ophys_key['channel']==1:
            imaging_plane = nwbfile.imaging_planes["imaging_plane_channel1"]
            plane_segmentation = add_plane_segmentation(nwbfile, imaging_plane, key=ophys_key, verbose=verbose)
            add_fluorescence(nwbfile, plane_segmentation, key=ophys_key, verbose=verbose)

    if verbose:
        print("Write NWB file")
    configure_and_write_nwbfile(nwbfile=nwbfile, backend="hdf5", output_filepath=nwbfile_path)


if __name__ == "__main__":
    import datajoint as dj

    root_path = Path("F:/CN_data")
    data_dir_path = root_path / "Reimer-Arenkiel-CN-data-share"
    output_dir_path = root_path / "Reimer-Arenkiel-conversion_nwb/"
    stub_test = True
    dj.conn()
    keys = get_session_keys()
    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        key=keys[-1],
        stub_test=stub_test,
    )
