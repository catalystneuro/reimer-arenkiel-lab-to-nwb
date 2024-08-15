# Notes concerning the embargo2024 conversion
* subject and session description, datajoint database ([General](#general))
* 2-photon imaging data, .tiff files with ScanImage format ([Raw Imaging](#raw-imaging))
* segmentation data, datajoint database ([Segmentation](#segmentation))
* olphactory stimuli ([Olphactory stimuli](#olphactory))
* synch signals ([Synch signals](#synch))
* treadmill ([Treadmill](#treadmill))


## General
The raw data shared referes to one subject (`animal_is = 134`) one session (`session = 22`).
```python
experiment.Session() & 'animal_id = 134' & 'session = 22'
```
| animal_id | session | rig | session_date | username | anesthesia | scan_path | behavior_path | craniotomy_notes | session_notes | archive | session_ts |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 134 | 22 | R2P1 | 2022-07-21 | ryan | awake | W:\Two-Photon\ryan\2022-07-21_12-09-48 | W:\Two-Photon\ryan\2022-07-21_12-09-48 |  |  | JR2P1A3A | 2022-07-21 12:09:48 |

## Raw Imaging 
### Method description from [Pre-print Ling 2023](https://www.biorxiv.org/content/10.1101/2023.04.24.538157v2):
Two-photon imaging was performed on a ThorLabs/Janelia 2P-RAM mesoscope. The laser wavelength was set to 920 nm to image GCaMP6f signals. Imaging parameters were controlled with ScanImage software. To maximize frame rates in each imaging session, fields of view were defined for acquisition that included a single plane visualizing only the dorsal surface of bilateral OBs (1800 um long x ~600um –wide fields of view that were tiled to cover a total field of view that was 1800-2500 um wide). Images were acquired continuously throughout experiments (during odor presentations, intertrial, and inter-block intervals), with 5um/pixel resolution at the fastest possible frame rate allowed by the imaging parameters (15-18 Hz). 
![alt text](frame_tiled.png)

### From dataset
* Frame dimension: 120 x n_columns (variable n_columns dimension)
    We divided the frame in three FOVs
    ![alt text](frame_channel_1.png)
    ![alt text](frame_channel_2.png)
* From dj --> only one channel used
```python
meso.ScanInfo() & 'animal_id = 134'  & 'session = 22'
```
general data about mesoscope scans
| animal_id | session | scan_idx | pipe_version | nfields | nchannels | nframes | nframes_requested | x | y | fps | bidirectional | usecs_per_line | fill_fraction | nrois | valid_depth |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 134 | 22 | 2 | 1 | 3 | 1 | 182000 | 182000 | 0.0 | 0.0 | 17.7982 | 1 | 41.6188 | 0.712867 | 3 | 1 |
* more imaging matadata at: 
```python
experiment.Scan() & 'animal_id = 134' & 'session = 22'
```
| animal_id | session | scan_idx | lens | brain_area | aim | filename | depth | scan_notes | site_number | software | version | scan_ts |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 134 | 22 | 2 | meso | unset | 2pScan | 134_22_00002 | 150 |  | 0 | scanimage | 2017b | 2022-07-21 12:11:02 |

`filename` could be as input for `ScanImageMultiFileImagingInterface`

* Question: where to find the channel / fluorophore info related to the specific subject/session

## Segmentation
`mask_key` must specified `mask_id` and `field`.
`field` indexed the original frame splitted from left to right 
```python
mask_key = {'animal_id': 134, 'session': 22, 'scan_idx': 2, 'field' : 3, 'mask_id':1}
```
```python
fluorescence = (meso.Fluorescence.Trace & mask_key).fetch1('trace')
mask_idx = (meso.Segmentation.Mask & mask_key).fetch1('pixels')
avg_image = (meso.SummaryImages.Average & mask_key).fetch1('average_image')
corr_image = (meso.SummaryImages.Correlation & mask_key).fetch1('correlation_image')
```
## Olphactory stimuli
* **odor.MesoMatch**: This table is used to convert from odor recording keys to meso recording keys; it will be most useful as a restriction on other tables.
* **odor.OdorTrial**: Contains timing for each odor presentation (on odor clock) and which odor channel was used.
    * **WARNING**: A single trial_idx can have multiple odors presented at once! Don't assume one odorant per trial.
    * **(odor.OdorTrials * odor.OdorConfig) & 'animal_id = 134' & 'odor_session = 32'**: Use this to list the actual odorant names  

| animal_id | odor_session | recording_idx | trial_idx | channel | trial_start_time | trial_end_time | odorant | concentration | solution_date |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 134 | 32 | 32 | 0 | 2 | 59.2888 | 60.2928 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 1 | 2 | 60.2966 | 61.2995 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 2 | 2 | 61.3034 | 62.3067 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 3 | 2 | 62.3106 | 63.313 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 4 | 2 | 63.317 | 64.3213 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 60 | 3 | 119.726 | 120.729 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 61 | 3 | 120.732 | 121.736 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 62 | 3 | 121.74 | 122.743 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 63 | 3 | 122.746 | 123.752 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 64 | 3 | 123.756 | 124.76 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 120 | 4 | 180.164 | 181.167 | Methyl Salicylate | 0.10 | 2022-05-17 |
| 134 | 32 | 32 | 121 | 4 | 181.171 | 182.174 | Methyl Salicylate | 0.10 | 2022-05-17 |

* **odor.Respiration**: Contains the respiration trace and the times it was recorded (on odor clock) --> no data for subject 134 session 22

## Synch signals
* **odor.OdorSync**: Contains the times for each fluorescence recording (on odor clock)
* **stimuus.BehaviorSync**: Contains the times for each fluorescence recording (on behavior clock)

## Treadmill
* **treadmill.Treadmill**: Contains treamill velocity and times of recording (on behavior clock)