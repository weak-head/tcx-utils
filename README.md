# tcx-utils

## Environment setup

```bash
# Install dependencies
pip3 install pipenv
pipenv shell
pipenv install

# Make the script executable
chmod +x tcx.py
```

## Usage

```txt
usage: tcx.py [-h]
              [-i | -m {append_laps,merge_lap,merge_track} | -s [SCALE_FACTOR]]
              [-o [OUTPUT_FILE]]
              input [input ...]

Scale, concatenate and modify TCX files

positional arguments:
  input                 Input TCX files

optional arguments:
  -h, --help            show this help message and exit
  -o [OUTPUT_FILE]      Output TCX file

actions:
  -i                    Output workout information.
                            -i  : Workout, lap and track info
                            -ii : Workout, lap, track and trackpoint info
  -m {append_laps,merge_lap,merge_track}
                        Merge multiple workouts into one workout.
                        Options:
                            append_laps  - Append all laps from all workouts into one workout
                            merge_laps   - Merge all laps from all workouts into one lap
                            merge_tracks - Merge all tracks from all workouts into one lap with one track
                        Example:
                            ./tcx.py -m merge_lap -o out.tcx f1.tcx f2.tcx f3.tcx
  -s [SCALE_FACTOR]     Scale duration, power, cadence and distance by the specified factor

Example: ./tcx.py -m append_laps activity1.tcx activity2.tcx
```

### Examples

Output workout info to the file:

```bash
./tcx.py -i -o out.txt w1.tcx w2.tcx w3.tcx
```

Merge several workouts into one:

```bash
./tcx.py -m append_laps -o merged.tcx w1.tcx w2.tcx w3.tcx w4.tcx
```
