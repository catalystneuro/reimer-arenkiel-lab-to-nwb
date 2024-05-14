"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from zoneinfo import ZoneInfo
from natsort import natsorted

from neuroconv.utils import load_dict_from_file, dict_deep_update

from reimer_arenkiel_lab_to_nwb.embargo2024 import Embargo2024NWBConverter


def session_to_nwb(
    data_dir_path: Union[str, Path], output_dir_path: Union[str, Path], session_date:str, session_id: str, subject_id:str, stub_test: bool = False
):

    data_dir_path = Path(data_dir_path)
    folder_path = data_dir_path / Path(session_date)

    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"{subject_id}_{session_id}.nwb"

    source_data = dict()
    conversion_options = dict()

    list_of_fov_boundaries = [[0,400], [450, 850], [900,1300]]
    # Add Imaging Green Channel Plane1
    for i,fov_boundaries in enumerate(list_of_fov_boundaries):
        interface_name = f"ImagingGreenChannelFOV{i}"
        source_data[interface_name] = {
            "folder_path": str(folder_path),
            "file_pattern": f"{subject_id}_{session_id}_*.tif",
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
    metadata["Subject"].update(subject_id=subject_id)

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "embargo2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Add ophys metadata
    ophys_metadata_path = Path(__file__).parent / "metadata" / "embargo2024_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)
    metadata.pop("Ophys", None)
    metadata = dict_deep_update(metadata, ophys_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":

    root_path = Path("/media/amtra/Samsung_T5/CN_data")
    data_dir_path = root_path / "Reimer-Arenkiel-CN-data-share"
    output_dir_path = root_path / "Reimer-Arenkiel-conversion_nwb/"
    stub_test = True
    session_date = "2022-07-21_12-09-48"
    session_id = "22"
    subject_id = "134"

    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        session_date = session_date,
        session_id=session_id,
        subject_id=subject_id,
        stub_test=stub_test,
    )
