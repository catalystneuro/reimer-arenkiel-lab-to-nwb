from typing import Optional, Tuple
import numpy as np
from roiextractors.extractors.tiffimagingextractors.scanimagetiffimagingextractor import (
    ScanImageTiffSinglePlaneMultiFileImagingExtractor,
)
from roiextractors.imagingextractor import ImagingExtractor
from roiextractors.extraction_tools import PathType, DtypeType, ArrayType


class Embargo2024ImagingExtractor(ImagingExtractor):
    def __init__(
        self,
        folder_path: PathType,
        file_pattern: str,
        channel_name: str,
        fov_boundaries: list,
        extract_all_metadata: bool = True,
    ) -> None:

        self.fov_boundaries = fov_boundaries
        self.imaging_extractor = ScanImageTiffSinglePlaneMultiFileImagingExtractor(
            folder_path=folder_path,
            file_pattern=file_pattern,
            channel_name=channel_name,
            plane_name='0',
            extract_all_metadata=extract_all_metadata,
        )
        self._times = self.imaging_extractor._times

    def get_video(self, start_frame: Optional[int] = None, end_frame: Optional[int] = None, channel: int = 0) -> np.ndarray:
        """
        The frames are divided in three adjacent planes that must be separated
        """
        video = self.imaging_extractor.get_video(start_frame=start_frame, end_frame=end_frame, channel=channel)
        return video[:,self.fov_boundaries[0]:self.fov_boundaries[1], :]

    def get_image_size(self) -> Tuple[int, int]:
        first_frame = self.get_frames(frame_idxs=0)
        n_channels, n_frames, n_rows, n_columns = first_frame.shape
        return [n_rows, n_columns]

    def get_num_frames(self) -> int:
        return self.imaging_extractor.get_num_frames()

    def get_dtype(self) -> DtypeType:
        return self.imaging_extractor.get_dtype()

    def get_sampling_frequency(self) -> float:
        return self.imaging_extractor.get_sampling_frequency()

    def get_channel_names(self) -> list:
        return self.imaging_extractor.get_channel_names()

    def get_num_channels(self) -> int:
        return self.imaging_extractor.get_num_channels()
    
    def get_frames(self, frame_idxs: ArrayType, channel: int = 0) -> np.ndarray:
        frame = self.imaging_extractor.get_frames(frame_idxs=frame_idxs,channel=channel)
        return frame[:,:,self.fov_boundaries[0]:self.fov_boundaries[1], :]
    

    
