from pathlib import Path
from neuroconv.utils import FilePathType, FolderPathType
from nwbinspector import inspect_all
from nwbinspector.inspector_tools import save_report, format_messages
from tqdm import tqdm
from embargo2024_convert_session import session_to_nwb
import datajoint as dj

from reimer_arenkiel_lab_to_nwb.dj_utils import get_session_keys

def convert_all_sessions(
    data_dir_path: FilePathType,
    output_dir_path: FolderPathType,
    stub_test: bool = False,
):
    """
    Convert all sessions from the Vu 2024 dataset to NWB format.

    Parameters
    ----------
    data_dir_path : FilePathType
        The path to all the sessions folders containing the raw imaging data.
    output_dir_path : FolderPathType
        The folder path to save the NWB files.
    stub_test : bool, optional
        Whether to run the conversion as a stub test.
        When set to True, write only a subset of the data for each session.
        When set to False, write the entire data for each session.

    """

    keys = get_session_keys()
    for key in tqdm(keys, desc="Processing sessions"):
        dj.conn()
        session_to_nwb(
            data_dir_path=data_dir_path,
            output_dir_path=output_dir_path,
            key=key,
            stub_test=stub_test,
        )

    report_path = output_dir_path / "inspector_result.txt"
    if not report_path.exists():
        results = list(inspect_all(path=output_dir_path))
        save_report(
            report_file_path=report_path,
            formatted_messages=format_messages(
                results,
                levels=["importance", "file_path"],
            ),
        )

if __name__ == "__main__":
    # Parameters for conversion
    root_path = Path("E:/CN_data")
    data_dir_path = root_path / "Reimer-Arenkiel-CN-data-share"
    output_dir_path = root_path / "Reimer-Arenkiel-conversion_nwb/"

    # The raw imaging data folder path
    data_dir_path = root_path / "Reimer-Arenkiel-CN-data-share"

    # The folder path to save the NWB files
    output_dir_path = root_path / "Reimer-Arenkiel-conversion_nwb/"

    # Whether to overwrite existing NWB files, default is False
    overwrite = True
    # Whether to run the conversion as a stub test
    # When set to True, write only a subset of the data for each session
    # When set to False, write the entire data for each session
    stub_test = False

    convert_all_sessions(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )
