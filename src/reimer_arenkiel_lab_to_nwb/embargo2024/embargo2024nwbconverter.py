"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from neuroconv.datainterfaces import ScanImageMultiFileImagingInterface

class Embargo2024NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        ImagingChannel1=ScanImageMultiFileImagingInterface,
        ImagingChannel2=ScanImageMultiFileImagingInterface,
    )
