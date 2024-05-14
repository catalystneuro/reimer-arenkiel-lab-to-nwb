"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from .interfaces.embargo2024_imaging_interface import Embargo2024ImagingInterface

class Embargo2024NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        ImagingGreenChannelFOV0=Embargo2024ImagingInterface,
        ImagingGreenChannelFOV1=Embargo2024ImagingInterface,
        ImagingGreenChannelFOV2=Embargo2024ImagingInterface,
    )
