#!/usr/bin/env python3

import argparse
import textwrap
import re
import sys
from enum import IntEnum, auto
from lxml import etree as ET
from io import BytesIO
from datetime import datetime, timedelta


class TCX:
    """
    Base class for all TCX related elements
    that provides utility methods to work with
    XML based structured TCX files in form of ElementTree..
    """

    __TimeFormats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    __DisplayTimeFormat = "%Y-%m-%d %H:%M:%S (UTC)"
    __DisplayTimeOnly = "%H:%M:%S"

    def __init__(self, root):
        self._root = root

    def elements(self, name, strict=True):
        """
        Recursively find elements of the given tree whose tag
        contains the given string.
        """
        return TCX.get_elements(self._root, name, strict=strict)

    def element(self, name, strict=True):
        """
        Recursively find the first element of the given tree whose tag
        contains the given string.
        """
        return TCX.get_element(self._root, name, strict=strict)

    def get_attribute(self, name):
        """
        Gets attribute of the root element.
        """
        return self._root.get(name)

    def set_attribute(self, name, value):
        """
        Sets attribute of the root element.
        """
        self._root.set(name, value)

    def get_child_attribute(self, child_tag, key):
        """
        Returns given attribute of the first child with the given tag.
        """
        return self.element(child_tag).get(key)

    def set_child_attribute(self, child_tag, key, value):
        """
        Sets value of the given attribute of the first child with the given tag.
        """
        return self.element(child_tag).set(key, value)

    @staticmethod
    def get_elements(root, name, strict=True):
        """
        Recursively find elements of the given tree whose tag
        contains the given string.
        """

        def predicate(a, b):
            return (b.endswith(a)) if strict else (a in b)

        return (elem for elem in root.iter() if predicate(name, elem.tag))

    @staticmethod
    def get_element(root, name, strict=True):
        """
        Recursively find the first element of the given tree whose tag
        contains the given string.
        """

        def predicate(a, b):
            return (b.endswith(a)) if strict else (a in b)

        for elem in root.iter():
            if predicate(name, elem.tag):
                return elem

    @staticmethod
    def sort_children_by(parent, key):
        """
        Order children of the element tree by key.
        """
        parent[:] = sorted(parent, key=key)

    @staticmethod
    def parse_time(time_string):
        """
        Parses string representation of 'datetime' and returns
        an instance of the 'datetime'.
        """
        for tf in TCX.__TimeFormats:
            try:
                return datetime.strptime(time_string, tf)
            except:
                pass
        raise ValueError(f"Unable to parse time string: [{time_string}]")

    @staticmethod
    def to_tcx_time_string(dt: datetime):
        """
        Converts an instance of the 'datetime' to 
        correctly formated TCX string representation.
        """
        return dt.strftime(TCX.__TimeFormats[0])

    @staticmethod
    def to_ts(dt: datetime):
        """
        Coverts an instance of the 'datetime' to
        human readable string representation.
        """
        return dt.strftime(TCX.__DisplayTimeFormat)

    @staticmethod
    def to_timeonly(dt: datetime):
        """
        """
        return dt.strftime(TCX.__DisplayTimeOnly)

    @staticmethod
    def chop_ms(delta):
        return delta - timedelta(microseconds=delta.microseconds)


class Workout(TCX):
    """
    """

    class MergeKind(IntEnum):
        """
        Possible kinds of workout merge:

            - APPEND_LAPS:
                Append all laps from all workouts
                into one workout. This is the default option.

                    Workout_1  +  Workout_2  =>  Workout_M
                      Lap_1         Lap_A          Lap_1
                        Track_1       Track_A        Track_1
                        Track_2     Lap_B            Track_2
                      Lap_2           Track_B      Lap_2
                        Track_3       Track_C        Track_3
                                                   Lap_A
                                                     Track_A
                                                   Lap_B
                                                     Track_B
                                                     Track_C

            - MERGE_INTO_SINGLE_LAP:
                Merge all laps from all workouts into one single lap.
                This will preserve all the track information.

                    Workout_1  +  Workout_2  =>  Workout_M
                      Lap_1         Lap_A          Lap_1
                        Track_1       Track_A        Track_1
                        Track_2       Track_B        Track_2
                      Lap_2                          Track_3
                        Track_3                      Track_A
                                                     Track_B

            - MERGE_INTO_SINGLE_TRACK:
                Merge all tracks from all laps into a single lap
                with a single track. This will remove all the information
                about track splits.

                    Workout_1  +  Workout_2  =>  Workout_M
                      Lap_1         Lap_A          Lap_M
                        Track_1       Track_A        Track_M
                        Track_2       Track_B
                      Lap_2
                        Track_3

        """

        APPEND_LAPS = 1
        MERGE_INTO_SINGLE_LAP = 2
        MERGE_INTO_SINGLE_TRACK = 3

    __Id = "Id"
    __Activities = "Activities"
    __Activity = "Activity"
    __Sport = "Sport"
    __Lap = "Lap"
    __Notes = "Notes"

    def __init__(self, workout_root: ET._ElementTree):
        super().__init__(workout_root)

    @property
    def laps(self):
        """
        Workout should have at least one lap, but it could have more.
        """
        return (Lap(lap) for lap in self.elements(Workout.__Lap))

    @property
    def workout_id(self):
        """
        """
        return self.element(Workout.__Id).text

    @property
    def activity(self):
        """
        Kind of activity.
        """
        return self.get_child_attribute(Workout.__Activity, Workout.__Sport)

    @property
    def start_time(self):
        """
        Workout start time.
        """
        first_lap = sorted(self.laps, key=lambda lp: lp.start_time, reverse=False)[0]
        return first_lap.start_time

    @property
    def finish_time(self):
        """
        Workout finish time.
        """
        last_lap = sorted(self.laps, key=lambda lp: lp.finish_time, reverse=True)[0]
        return last_lap.finish_time

    @property
    def duration(self):
        """
        Workout duration.
        """
        d = self.finish_time - self.start_time
        return timedelta(seconds=d.total_seconds())

    @classmethod
    def load(cls, file):
        """
        Read and parse TCX file with workout data.
        Return root of the workout XML-tree.
        """
        return cls(ET.parse(file))

    def save(self, file):
        """
        Save workout tree as TCX file.
        """
        encoding = "utf-8"

        # Write to memory buffer, since ElementTree
        # doesn't include XML declaration.
        # Decode byte stream as a string and remove
        # namespace (e.g. "<ns3:...>") information from the string.
        mem_buf = BytesIO()
        self._root.write(mem_buf, encoding=encoding, xml_declaration=True)
        s = mem_buf.getvalue().decode(encoding)
        s = re.sub(r"ns\d+:", "", s)

        with open(file, "w") as f:
            print(s, file=f)

    def info(self, prefix="", verbose=False, stream=sys.__stdout__):
        """
        Outputs workout info to a stream.
        """
        print(prefix + "Workout:", file=stream)
        prefix += "  "

        print(prefix + "Id:           " + self.workout_id, file=stream)
        print(prefix + "Activity:     " + self.activity, file=stream)
        print(prefix + "Start time:   " + TCX.to_ts(self.start_time), file=stream)
        print(prefix + "Finish time:  " + TCX.to_ts(self.finish_time), file=stream)
        print(prefix + "Duration:     " + str(TCX.chop_ms(self.duration)), file=stream)

        print(prefix + "Laps:         ", file=stream)
        for n, lap in enumerate(self.laps):
            lap.info(prefix=prefix + "  ", n=n, verbose=verbose, stream=stream)

        print("", file=stream)
        print("", file=stream)

    def overlaps(self, workout):
        """
        Returns true if this workout overlaps the other workout.
        """
        return max(self.start_time, workout.start_time) <= min(
            self.finish_time, workout.finish_time
        )

    def overlaps_by(self, workout):
        """
        Returns the overlap time of two workouts.
        """
        return min(self.finish_time, workout.finish_time) - max(
            self.start_time, workout.start_time
        )

    def scale(
        self, scale_factor, scale_distance=True, scale_cadence=True, scale_watts=True
    ):
        """
        For the cases when a treadmill or bike measuers incorrect distance, cadence or watts
        we can adjust them keeping the same time and gps coordinates. Typically this is the case
        with incorrectly calibrated indoor equipment or outdoor trackers.
        """

        for lap in self.laps:
            for trackpoint in lap.trackpoints:

                if scale_distance:
                    trackpoint.distance = trackpoint.distance * scale_factor

                if scale_cadence:
                    trackpoint.cadence = trackpoint.cadence * scale_factor

                if scale_watts:
                    trackpoint.watts = trackpoint.watts * scale_factor

    def merge(self, workout, merge_kind=MergeKind.APPEND_LAPS):
        """
        Merge the workout with the other workout.
        """
        if self.overlaps(workout):
            raise ValueError("Workouts should not overlap")

        if merge_kind == Workout.MergeKind.APPEND_LAPS:
            # Append all laps from the other workout to this workout
            activity = self.element(Workout.__Activity)

            other_laps = workout.elements(Workout.__Lap)
            activity.extend(other_laps)

        else:
            self_laps = list(self.laps)
            workout_laps = list(workout.laps)

            if len(self_laps) != 1 or len(workout_laps) != 1:
                raise ValueError(
                    "In order to merge laps, each workout should have exactly one lap. "
                    "[{0}] workout has {2} laps, [{1}] workout has {3} laps.".format(
                        self.workout_id,
                        workout.workout_id,
                        len(self_laps),
                        len(workout_laps),
                    )
                )

            self_laps[0].merge(workout_laps[0], merge_kind=Lap.MergeKind(merge_kind))

    @staticmethod
    def overlap(*workouts):
        """
        Returns True if any two workouts overlap.
        """
        pass

    @staticmethod
    def concat_all(*workouts, split_laps=False):
        """
        """
        pass


class Lap(TCX):
    """
    """

    class MergeKind(IntEnum):
        """
        """

        MERGE_INTO_SINGLE_LAP = 2
        MERGE_INTO_SINGLE_TRACK = 3

    __StartTime = "StartTime"
    __TotalTime = "TotalTimeSeconds"
    __Distance = "DistanceMeters"
    __Calories = "Calories"
    __AverageHeartRate = "AverageHeartRateBpm"
    __MaxHeartRate = "MaximumHeartRateBpm"
    __Cadence = "Cadence"
    __Track = "Track"
    __Trackpoint = "Trackpoint"

    def __init__(self, lap_root: ET._Element):
        super().__init__(lap_root)

    @property
    def tracks(self):
        """
        """
        return (Track(t) for t in self.elements(Lap.__Track))

    @property
    def trackpoints(self):
        """
        """
        return (Trackpoint(tp) for tp in self.elements(Lap.__Trackpoint))

    @property
    def start_time(self):
        """
        """
        return Lap.parse_time(self.get_attribute(Lap.__StartTime))

    @start_time.setter
    def start_time(self, x):
        """
        """
        time = Lap.to_tcx_time_string(x)
        self.set_attribute(Lap.__StartTime, time)

    @property
    def finish_time(self):
        """
        """
        last_trackpoint = sorted(
            self.trackpoints, key=lambda tp: tp.time, reverse=True
        )[0]
        return last_trackpoint.time

    @property
    def duration(self):
        """
        Lap duration.
        """
        d = self.finish_time - self.start_time
        d = timedelta(seconds=d.total_seconds())
        return d

    @property
    def total_seconds(self):
        """
        Total lap time in seconds.
        """
        return int(self.element(Lap.__TotalTime).text)

    @total_seconds.setter
    def total_seconds(self, x):
        """
        """
        time = self.element(Lap.__TotalTime)
        time.text = str(int(x))

    @property
    def distance(self):
        """
        Lap distance in meters.
        """
        return float(self.element(Lap.__Distance).text)

    @distance.setter
    def distance(self, x):
        """
        """
        d = self.element(Lap.__Distance)
        d.text = str(float(x))

    @property
    def calories(self):
        """
        Lap calories.
        """
        return int(self.element(Lap.__Calories).text)

    @calories.setter
    def calories(self, x):
        """
        """
        c = self.element(Lap.__Calories)
        c.text = str(int(x))

    @property
    def cadence(self):
        """
        """
        return int(self.element(Lap.__Cadence).text)

    @property
    def heart_rate(self):
        """
        """
        e = self.element(Lap.__AverageHeartRate)
        return int(float(e[0].text)) if e is not None else None

    @property
    def max_heart_rate(self):
        """
        """
        e = self.element(Lap.__MaxHeartRate)
        return int(float(e[0].text)) if e is not None else None

    def overlaps(self, lap):
        """
        Returns true if this lap overlaps the other lap.
        """
        return max(self.start_time, lap.start_time) <= min(
            self.finish_time, lap.finish_time
        )

    def info(self, prefix="  ", n="", verbose=False, stream=sys.__stdout__):
        """
        Outputs lap info to a stream.
        """
        lap_title = "Lap" if n == "" else "Lap #{0:d}".format(n)
        lap_title += " [{0} -> {1}]".format(
            TCX.to_timeonly(self.start_time), TCX.to_timeonly(self.finish_time)
        )

        print(prefix + lap_title, file=stream)
        prefix += "  "

        print(prefix + "Start time:   " + TCX.to_ts(self.start_time), file=stream)
        print(prefix + "Finish time:  " + TCX.to_ts(self.finish_time), file=stream)
        print(prefix + "Duration:     " + str(TCX.chop_ms(self.duration)), file=stream)
        print(prefix + "Distance:     " + f"{self.distance:,}m", file=stream)
        print(prefix + "Calories:     " + str(self.calories), file=stream)
        print(prefix + "Avg cadence:  " + str(self.cadence), file=stream)

        if self.heart_rate:
            print(
                prefix + "Avg HR:       " + str(self.heart_rate) + " bpm", file=stream
            )

        if self.max_heart_rate:
            print(
                prefix + "Max HR:       " + str(self.max_heart_rate) + " bpm",
                file=stream,
            )

        print(prefix + "Tracks:", file=stream)
        for tn, track in enumerate(self.tracks):
            track.info(prefix=prefix + "  ", n=tn, verbose=verbose, stream=stream)

        print("", file=stream)

    def merge(self, lap, merge_kind=MergeKind.MERGE_INTO_SINGLE_LAP):
        """
        Merge the lap with the other lap.
        """
        if self.overlaps(lap):
            raise ValueError("Laps should not overlap")

        (earlier, later) = (
            (self, lap) if self.start_time < lap.start_time else (lap, self)
        )

        # Adjust distance of the trackpoints
        # from the later lap
        base_distance = earlier.distance
        for trackpoint in later.trackpoints:
            trackpoint.distance += base_distance

        # Marge two laps into single lap
        if merge_kind == Lap.MergeKind.MERGE_INTO_SINGLE_LAP:
            tracks = later.elements(Lap.__Track)
            earlier._root.extend(tracks)

            # Copy the merged and adjusted tracks
            self._root[:] = earlier._root[:]

        # Merge multiple tracks into single track
        else:
            # Merge trackpoints
            earlier_track = earlier.element(Lap.__Track)
            later_trackpoints = list(later.elements(Lap.__Trackpoint))
            earlier_track.extend(later_trackpoints)

            # Copy the merged and adjusted trackpoints to this lap
            self_track = self.element(Lap.__Track)
            self_track[:] = earlier_track[:]

            # To avoid any possible inconsistencies we order merged trackpoints by time
            TCX.sort_children_by(
                self_track, lambda trackpoint: Trackpoint(trackpoint).time
            )

        self.start_time = earlier.start_time
        self.total_seconds += lap.total_seconds
        self.distance += lap.distance
        self.calories += lap.calories
        # TODO: adjust max HR


class Track(TCX):
    """
    """

    __Trackpoint = "Trackpoint"

    def __init__(self, track_root: ET._Element):
        super().__init__(track_root)

    @property
    def start_time(self):
        """
        """
        first_trackpoint = sorted(
            self.trackpoints, key=lambda tp: tp.time, reverse=False
        )[0]
        return first_trackpoint.time

    @property
    def finish_time(self):
        """
        """
        last_trackpoint = sorted(
            self.trackpoints, key=lambda tp: tp.time, reverse=True
        )[0]
        return last_trackpoint.time

    @property
    def duration(self):
        """
        Track duration.
        """
        d = self.finish_time - self.start_time
        d = timedelta(seconds=d.total_seconds())
        return d

    @property
    def trackpoints(self):
        """
        """
        return (Trackpoint(tp) for tp in self.elements(Track.__Trackpoint))

    def info(self, prefix="  ", n=0, verbose=False, stream=sys.__stdout__):
        """
        """
        track_title = "Track #{0:d} [{1} -> {2}]".format(
            n, TCX.to_timeonly(self.start_time), TCX.to_timeonly(self.finish_time)
        )
        print(prefix + track_title, file=stream)

        prefix += "  "
        print(prefix + "Start time:   " + TCX.to_ts(self.start_time), file=stream)
        print(prefix + "Finish time:  " + TCX.to_ts(self.finish_time), file=stream)
        print(prefix + "Duration:     " + str(TCX.chop_ms(self.duration)), file=stream)
        print(prefix + "Trackpoints:  " + str(len(list(self.trackpoints))), file=stream)

        if verbose:
            for t in self.trackpoints:
                t.info(prefix + "  ", verbose=verbose, stream=stream)


class Trackpoint(TCX):
    """
    """

    __Time = "Time"
    __HeartRate = "HeartRateBpm"
    __Distance = "DistanceMeters"
    __Cadence = "Cadence"
    __Watts = "Watts"

    def __init__(self, trackpoint_root: ET._Element):
        super().__init__(trackpoint_root)

    @property
    def time(self):
        """
        Timestamp (datetime)
        """
        return TCX.parse_time(self.element(Trackpoint.__Time).text)

    @property
    def distance(self):
        """
        Distance in meters (float)
        """
        return float(self.element(Trackpoint.__Distance).text)

    @distance.setter
    def distance(self, x):
        node = self.element(Trackpoint.__Distance)
        node.text = str(float(x))

    @property
    def cadence(self):
        """
        Cadence (float)
        """
        node = self.element(Trackpoint.__Cadence)
        return float(node.text) if node is not None else None

    @cadence.setter
    def cadence(self, x):
        node = self.element(Trackpoint.__Cadence)
        node.text = str(float(x))

    @property
    def watts(self):
        """
        Watts (float)
        """
        node = self.element(Trackpoint.__Watts)
        return float(node.text) if node is not None else None

    @watts.setter
    def watts(self, x):
        node = self.element(Trackpoint.__Watts)
        node.text = str(float(x))

    def info(self, prefix="  ", verbose=False, stream=sys.__stdout__):
        """
        """
        trackpoint_info = f"{TCX.to_timeonly(self.time)} -> {int(self.distance):,}m;"

        if self.watts is not None:
            trackpoint_info += f" {int(self.watts)}W;"

        if self.cadence is not None:
            trackpoint_info += f" Cadence: {int(self.cadence)};"

        print(prefix + trackpoint_info, file=stream)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scale, concatenate and modify TCX files",
        epilog=f"Example: {sys.argv[0]} --merge activity1.tcx activity2.tcx",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # ----------------------
    # -- Exclusive actions

    action = parser.add_argument_group("actions")
    action_ex = action.add_mutually_exclusive_group()
    action_ex.add_argument(
        "-i",
        dest="info",
        action="count",
        help=textwrap.dedent(
            """\
            Output workout information.
                -i  : Workout, lap and track info
                -ii : Workout, lap, track and trackpoint info
            """
        ),
    )
    action_ex.add_argument(
        "-m",
        dest="merge",
        type=str,
        choices=["append_laps", "merge_lap", "merge_track"],
        action="store",
        help=textwrap.dedent(
            """\
            Merge multiple workouts into one workout.
            Options:
                append_laps  - Append all laps from all workouts into one workout 
                merge_laps   - Merge all laps from all workouts into one lap
                merge_tracks - Merge all tracks from all workouts into one lap with one track
            Example:
                ./tcx.py -m merge_lap -o out.tcx f1.tcx f2.tcx f3.tcx 
            """
        ),
    )
    action_ex.add_argument(
        "-s",
        dest="scale_factor",
        nargs="?",
        type=float,
        help="Scale duration, power, cadence and distance by the specified factor",
    )

    # --------------------
    # -- Other arguments

    parser.add_argument(
        "-o", dest="output_file", nargs="?", default="out.tcx", help="Output TCX file",
    )

    parser.add_argument("input", type=str, nargs="+", help="Input TCX files")

    return parser.parse_args()


def handle_action(args):
    """
    """

    # Output info
    if args.info is not None:

        if args.output_file is None:
            handle_info(args.input, verbose=args.info > 1)
        else:
            print(f"Saving output to {args.output_file}... ", end="", flush=True)
            with open(args.output_file, "w") as f:
                handle_info(args.input, verbose=args.info > 1, stream=f)
            print("Done")

    # Merge workouts
    elif args.merge is not None:
        pass

    # Scale workouts
    elif args.scale_factor is not None:
        pass


def handle_info(input, verbose=False, stream=sys.__stdout__):
    for f in input:
        try:
            print(f"==== {f} =======================================", file=stream)
            w = Workout.load(f)
            w.info(verbose=verbose, stream=stream)
        except Exception as e:
            print(f"Failed to process {f} file. \n{e}\n\n", file=stream)


def handle_scale(args):
    pass


def handle_merge(args):
    pass


def main():
    handle_action(parse_args())


if __name__ == "__main__":
    main()
