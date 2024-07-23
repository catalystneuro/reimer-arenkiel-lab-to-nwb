"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from time import time
from tqdm import tqdm
from neuroconv.utils import load_dict_from_file, dict_deep_update
from neuroconv.tools.nwb_helpers import configure_and_write_nwbfile

from reimer_arenkiel_lab_to_nwb.embargo2024 import Embargo2024NWBConverter
from reimer_arenkiel_lab_to_nwb.dj_utils import *

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
    fov_boundaries = [[0, 400], [450, 850], [900, 1300]]

    for ophys_key in tqdm(ophys_keys, desc="Processing imaging planes"):
        interface_name = f"ImagingFOV{ophys_key["field"]}"
        source_data[interface_name] = {
            "folder_path": str(folder_path),
            "file_pattern": f"{key['animal_id']}_{key['session']}_*.tif",
            "channel_name": "Channel 1",
            "fov_boundaries": fov_boundaries[ophys_key["field"]-1]
        }
        conversion_options[interface_name] = {
            "stub_test": stub_test,
            "photon_series_index": ophys_key["field"]-1,
            "photon_series_type": "TwoPhotonSeries",
        }
    converter = Embargo2024NWBConverter(source_data=source_data)

    converter.temporally_align_data_interfaces(key=key)

    # Add datetime to conversion
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "embargo2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Add ophys metadata
    metadata.pop("Ophys", None)
    metadata = dict_deep_update(metadata, ophys_metadata)

    # Run conversion
    converter.add_to_nwbfile(
        metadata=metadata, nwbfile=nwbfile, conversion_options=conversion_options
    )

    for ophys_key in tqdm(ophys_keys, desc="Processing imaging planes"):
        photon_series_name = metadata["Ophys"]["TwoPhotonSeries"][ophys_key["field"]-1]["name"]
        imaging_plane = nwbfile.acquisition[photon_series_name].imaging_plane
        plane_segmentation = add_plane_segmentation(nwbfile, imaging_plane, key=ophys_key, verbose=verbose)
        add_fluorescence(nwbfile, plane_segmentation, key=ophys_key, verbose=verbose)

    configure_and_write_nwbfile(nwbfile=nwbfile, backend="hdf5", output_filepath=nwbfile_path)


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
    end_time = time()
    print(f"Running time:{end_time - start_time}")
