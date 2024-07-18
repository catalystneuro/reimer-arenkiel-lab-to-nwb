"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from zoneinfo import ZoneInfo
from natsort import natsorted
from tqdm import tqdm
from neuroconv.utils import load_dict_from_file, dict_deep_update

from reimer_arenkiel_lab_to_nwb.embargo2024 import Embargo2024NWBConverter
from reimer_arenkiel_lab_to_nwb.dj_utils import get_session_keys, get_ophys_keys, init_nwbfile, add_treadmill, add_subject, add_odor_trials, add_respiration, add_summary_images, add_imaging_plane, add_plane_segmentation, add_fluorescence

def session_to_nwb(
        data_dir_path: Union[str, Path], output_dir_path: Union[str, Path], key: dict, stub_test: bool = False, verbose: bool = True
):
    data_dir_path = Path(data_dir_path)
    folder_path = data_dir_path / f"{key['animal_id']}_{key['session']}_{key['scan_idx']}"

    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"seb-{key['animal_id']}_ses-{key['session']}.nwb"

    source_data = dict()
    conversion_options = dict()

    ophys_metadata_path = Path(__file__).parent / "metadata" / "embargo2024_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)

    nwbfile = init_nwbfile(key=key)
    add_treadmill(nwbfile, key=key, verbose=verbose)
    add_subject(nwbfile, key=key, verbose=verbose)
    add_odor_trials(nwbfile, key=key, verbose=verbose)
    add_respiration(nwbfile, key=key, verbose=verbose)
    add_summary_images(nwbfile, key=key, verbose=verbose)

    device = nwbfile.create_device(name=ophys_metadata["Ophys"]["Device"][0]["name"])

    # ophys_keys include all the field, channel, and segmentation_method associated with this session. We will iterate over
    ophys_keys = get_ophys_keys(key=key)

    # iterate over each ophys_key
    for ophys_key in tqdm(ophys_keys, desc="Processing imaging planes"):
        imaging_plane = add_imaging_plane(nwbfile, key=ophys_key, verbose=verbose, device=device)
        plane_segmentation = add_plane_segmentation(nwbfile, imaging_plane, key=ophys_key, verbose=verbose)
        add_fluorescence(nwbfile, plane_segmentation, key=ophys_key, verbose=verbose)

    list_of_fov_boundaries = [[0, 400], [450, 850], [900, 1300]]
    # Add Imaging Green Channel Plane1
    for i, fov_boundaries in enumerate(list_of_fov_boundaries):
        interface_name = f"ImagingGreenChannelFOV{i + 1}"
        source_data[interface_name] = {
            "folder_path": str(folder_path),
            "file_pattern": f"{key['animal_id']}_{key['session']}_*.tif",
            "channel_name": "Channel 1",
            "fov_boundaries": fov_boundaries
        }
        conversion_options[interface_name] = {
            "stub_test": stub_test,
            "photon_series_index": i,
            "photon_series_type": "TwoPhotonSeries",
        }
    converter = Embargo2024NWBConverter(source_data=source_data)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    metadata["Subject"].update(subject_id=str(key['animal_id']))

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "embargo2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Add ophys metadata
    # metadata.pop("Ophys", None)
    # metadata = dict_deep_update(metadata, ophys_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile=nwbfile, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":
    root_path = Path("E:/CN_data")
    data_dir_path = root_path / "Reimer-Arenkiel-CN-data-share"
    output_dir_path = root_path / "Reimer-Arenkiel-conversion_nwb/"
    stub_test = True

    keys = get_session_keys()


    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        key=keys[4],
        stub_test=stub_test,
    )
