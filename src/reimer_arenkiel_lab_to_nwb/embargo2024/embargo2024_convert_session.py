"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
import datetime
from zoneinfo import ZoneInfo
from natsort import natsorted

from neuroconv.utils import load_dict_from_file, dict_deep_update

from reimer_arenkiel_lab_to_nwb.embargo2024 import Embargo2024NWBConverter
from roiextractors import ScanImageTiffSinglePlaneImagingExtractor


def session_to_nwb(
    data_dir_path: Union[str, Path], output_dir_path: Union[str, Path], session_id: str, stub_test: bool = False
):

    data_dir_path = Path(data_dir_path)
    folder_path = data_dir_path / Path(session_id)
    subject_id = "test_subject"

    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    source_data = dict()
    conversion_options = dict()

    # Add Imaging Channel1
    source_data.update(
        dict(ImagingChannel1=dict(folder_path=str(folder_path), file_pattern="*.tif", channel_name="Channel 1"))
    )
    conversion_options.update(dict(ImagingChannel1=dict(stub_test=stub_test, photon_series_index=0)))
    # Add Imaging Channel2
    source_data.update(
        dict(ImagingChannel2=dict(folder_path=str(folder_path), file_pattern="*.tif", channel_name="Channel 2"))
    )
    conversion_options.update(dict(ImagingChannel2=dict(stub_test=stub_test, photon_series_index=1)))

    converter = Embargo2024NWBConverter(source_data=source_data)

    # Add datetime to conversion
    metadata = converter.get_metadata()
    datetime.datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("US/Eastern"))
    date = datetime.datetime.today()  # TO-DO: Get this from author
    metadata["NWBFile"]["session_start_time"] = date
    metadata["Subject"].update(subject_id=subject_id)
    metadata["NWBFile"].update(session_id=session_id)

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "embargo2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":

    root_path = Path("/media/amtra/Samsung_T5/CN_data")
    data_dir_path = root_path / "Reimer-Arenkiel-CN-data-share"
    output_dir_path = root_path / "Reimer-Arenkiel-conversion_nwb/"
    stub_test = True
    session_id = "2022-07-21_12-09-48"

    session_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        session_id=session_id,
        stub_test=stub_test,
    )
