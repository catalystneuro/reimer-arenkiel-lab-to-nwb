import datetime
from pathlib import Path
from neuroconv.datainterfaces.ophys.baseimagingextractorinterface import BaseImagingExtractorInterface
from neuroconv.utils import FolderPathType
from ..extractors.embargo2024_imaging_extractor import Embargo2024ImagingExtractor


class Embargo2024ImagingInterface(BaseImagingExtractorInterface):
    """Interface for reading multi-file (buffered) TIFF files produced via ScanImage."""

    display_name = "ScanImage Single Plane Multi-File Imaging"
    associated_suffixes = (".tif",)
    info = "Interface for ScanImage multi-file (buffered) TIFF files."

    Extractor = Embargo2024ImagingExtractor

    def __init__(
        self,
        folder_path: FolderPathType,
        file_pattern: str,
        channel_name: str,
        field: int,
        number_of_fields: int = 3,
        image_metadata: dict = None,
        extract_all_metadata: bool = False,
    ):
        """Interface for reading multi-file (buffered) TIFF files produced via ScanImage., where each frames can be split in many field of view.

        Parameters
        ----------
        folder_path : PathType
            Path to the folder containing the TIFF files.
        file_pattern : str
            Pattern for the TIFF files to read -- see pathlib.Path.glob for details.
        channel_name : str
            Name of the channel for this extractor.
        field : int
            Field of view number as extracted from the ophys key.
        number_of_fields : int, default 3
            Number of fields to split the frame.
        extract_all_metadata : bool
            If True, extract metadata from every file in the folder. If False, only extract metadata from the first
            file in the folder. The default is True.
        """

        super().__init__(
            folder_path=folder_path,
            file_pattern=file_pattern,
            channel_name=channel_name,
            field=field,
            number_of_fields=number_of_fields,
            extract_all_metadata=extract_all_metadata,
        )
        from natsort import natsorted
        from roiextractors.extractors.tiffimagingextractors.scanimagetiff_utils import extract_extra_metadata

        file_paths = natsorted(Path(folder_path).glob(file_pattern))
        first_file_path = file_paths[0]

        image_metadata = image_metadata or extract_extra_metadata(file_path=first_file_path)
        self.image_metadata = image_metadata


    def get_metadata(self) -> dict:
        metadata = super().get_metadata()

        extracted_session_start_time = datetime.datetime.strptime(
            self.image_metadata["epoch"], "[%Y %m %d %H %M %S.%f]"
        )
        metadata["NWBFile"].update(session_start_time=extracted_session_start_time)

        return metadata