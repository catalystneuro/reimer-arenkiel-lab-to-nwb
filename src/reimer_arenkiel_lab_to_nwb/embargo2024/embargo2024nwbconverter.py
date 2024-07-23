"""Primary NWBConverter class for this dataset."""
from neuroconv import NWBConverter
from .interfaces.embargo2024_imaging_interface import Embargo2024ImagingInterface
from reimer_arenkiel_lab_to_nwb.dj_utils import get_imaging_start_time, get_ophys_keys

class Embargo2024NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        ImagingFOV1=Embargo2024ImagingInterface,
        ImagingFOV2=Embargo2024ImagingInterface,
        ImagingFOV3=Embargo2024ImagingInterface,
    )

    def temporally_align_data_interfaces(self, key: dict = None):
        ophys_keys = get_ophys_keys(key=key)
        for ophys_key in ophys_keys:
            imaging_start_time = get_imaging_start_time(key=ophys_key)
            imaging_interface = self.data_interface_objects[f"ImagingFOV{ophys_key["field"]}"]
            imaging_interface.set_aligned_starting_time(imaging_start_time)
