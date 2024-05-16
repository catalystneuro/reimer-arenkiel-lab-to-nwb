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
        fov_boundaries: list,
        channel_name: str,
        image_metadata: dict = None,
        extract_all_metadata: bool = False,
    ):
        super().__init__(
            folder_path=folder_path,
            file_pattern=file_pattern,
            fov_boundaries=fov_boundaries,
            channel_name=channel_name,
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