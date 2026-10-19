from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from roiextractors.extractors.tiffimagingextractors.scanimagetiffimagingextractor import (
    ScanImageTiffSinglePlaneImagingExtractor,
)
from roiextractors.extractors.tiffimagingextractors.scanimagetiff_utils import extract_extra_metadata, parse_metadata
from roiextractors.imagingextractor import ImagingExtractor
from roiextractors.multiimagingextractor import MultiImagingExtractor
from roiextractors.extraction_tools import PathType, DtypeType, ArrayType


class Embargo2024ImagingExtractor(ImagingExtractor):
    def __init__(
        self,
        folder_path: PathType,
        file_pattern: str,
        channel_name: str,
        field: int,
        number_of_fields: int = 3,
        extract_all_metadata: bool = True,
    ) -> None:

        """Create a ImagingExtractor instance from a folder of TIFF files produced by ScanImage, where each frames can be split in many field of view.

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

        from natsort import natsorted

        file_paths = natsorted(Path(folder_path).glob(file_pattern))
        if not extract_all_metadata:
            metadata = self._extract_metadata(file_paths[0])
        imaging_extractors = []
        for file_path in file_paths:
            if extract_all_metadata:
                metadata = self._extract_metadata(file_path)
            imaging_extractors.append(
                ScanImageTiffSinglePlaneImagingExtractor(
                    file_path=file_path,
                    channel_name=channel_name,
                    plane_name='0',
                    metadata=metadata,
                    parsed_metadata=parse_metadata(metadata),
                )
            )
        self.imaging_extractor = MultiImagingExtractor(imaging_extractors=imaging_extractors)
        self._times = self.imaging_extractor._times
        fov_length = self.imaging_extractor.get_image_size()[0] // number_of_fields
        boundaries = [[i * fov_length, (i + 1) * fov_length if i < number_of_fields - 1 else -1] for i in range(number_of_fields)]
        self.fov_boundaries = boundaries[field-1]

    @staticmethod
    def _extract_metadata(file_path: PathType) -> dict:
        metadata = extract_extra_metadata(file_path=file_path)
        # In some sessions (e.g. 134_22, 141_5, 141_8) two channels were active but only channel 1 was saved
        # (SI.hChannels.channelSave = 1). roiextractors counts the active channels, which would read every other
        # frame of the file as channel 1, so count the saved channels instead.
        metadata["SI.hChannels.channelsActive"] = metadata["SI.hChannels.channelSave"]
        return metadata

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
    

    
