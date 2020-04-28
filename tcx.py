#!/usr/bin/env python3

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime, timedelta


class TCX:
    """
    Base class for all TCX related elements
    that provides utility methods to work with
    XML based structured TCX files in form of ElementTree..
    """

    __TimeFormat = "%Y-%m-%dT%H:%M:%S.%fZ"
    __DisplayTimeFormat = "%Y-%m-%d %H:%M:%S (UTC)"
    __DisplayTimeOnly = "%H:%M:%S"

    def __init__(self, root):
        self._root = root

    def get_elements(self, name):
        """
        Recursively find elements of the given tree whose tag
        contains the given string.
        """
        return (elem for elem in self._root.iter() if name in elem.tag)

    def get_element(self, name):
        """
        Recursively find the first element of the given tree whose tag
        contains the given string.
        """
        for elem in self._root.iter():
            if name in elem.tag:
                return elem

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
        return self.get_element(child_tag).get(key)

    def set_child_attribute(self, child_tag, key, value):
        """
        Sets value of the given attribute of the first child with the given tag.
        """
        return self.get_element(child_tag).set(key, value)

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
        return datetime.strptime(time_string, TCX.__TimeFormat)

    @staticmethod
    def to_tcx_time_string(dt: datetime):
        """
        Converts an instance of the 'datetime' to 
        correctly formated TCX string representation.
        """
        return dt.strftime(TCX.__TimeFormat)

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

    __Id = "Id"
    __Activity = "Activity"
    __Sport = "Sport"
    __Lap = "Lap"
    __Notes = "Notes"

    def __init__(self, workout_root: ET.ElementTree):
        super().__init__(workout_root)

    @property
    def laps(self):
        """
        Workout should have at least one lap, but it could have more.
        """
        return (Lap(lap) for lap in self.get_elements(Workout.__Lap))

    @property
    def workout_id(self):
        """
        """
        return self.get_element(Workout.__Id).text

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

    def info(self, prefix="", stream=sys.__stdout__):
        """
        Outputs workout info to a stream.
        """
        print(prefix + "Workout:", file=stream)
        prefix += "  "

        print(prefix + "Id:          " + self.workout_id, file=stream)
        print(prefix + "Activity:    " + self.activity, file=stream)
        print(prefix + "Start time:  " + TCX.to_ts(self.start_time), file=stream)
        print(prefix + "Finish time: " + TCX.to_ts(self.finish_time), file=stream)
        print(prefix + "Duration:    " + str(TCX.chop_ms(self.duration)), file=stream)

        print(prefix + "Laps:        ", file=stream)
        for n, lap in enumerate(self.laps):
            lap.info(prefix=prefix + "  ", n=n, stream=stream)

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

    def concat(self, workout, merge_laps=True):
        """
        Concatenate the workout with the other workout.
        """
        if self.overlaps(workout):
            raise ValueError("Workouts should not overlap")

        if merge_laps:
            self_laps = list(self.laps)
            workout_laps = list(workout.laps)

            if len(self_laps) != 1 or len(workout_laps) != 1:
                raise ValueError(
                    "In order to merge laps, each workout should have exactly one lap. "
                    "[{0}] workout has {2} laps, [{1}] workout has {3} laps.".format(
                        self.workout_id, workout.workout_id, len(self_laps), len(workout_laps)
                    )
                )

            self_laps[0].merge(workout_laps[0])

        else:
            pass

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

    __StartTime = "StartTime"
    __TotalTime = "TotalTimeSeconds"
    __Distance = "DistanceMeters"
    __Calories = "Calories"
    __AverageHeartRate = "AverageHeartRateBpm"
    __MaxHeartRate = "MaximumHeartRateBpm"
    __Cadence = "Cadence"
    __Track = "Track"
    __Trackpoint = "Trackpoint"

    def __init__(self, lap_root: ET.Element):
        super().__init__(lap_root)

    @property
    def trackpoints(self):
        """
        """
        return (Trackpoint(tp) for tp in self.get_elements(Lap.__Trackpoint))

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
        return int(self.get_element(Lap.__TotalTime).text)

    @total_seconds.setter
    def total_seconds(self, x):
        """
        """
        time = self.get_element(Lap.__TotalTime)
        time.text = str(int(x))

    @property
    def distance(self):
        """
        Lap distance in meters.
        """
        return int(self.get_element(Lap.__Distance).text)

    @distance.setter
    def distance(self, x):
        """
        """
        d = self.get_element(Lap.__Distance)
        d.text = str(int(x))

    @property
    def calories(self):
        """
        Lap calories.
        """
        return int(self.get_element(Lap.__Calories).text)

    @calories.setter
    def calories(self, x):
        """
        """
        c = self.get_element(Lap.__Calories)
        c.text = str(int(x))

    @property
    def cadence(self):
        """
        """
        return int(self.get_element(Lap.__Cadence).text)

    @property
    def heart_rate(self):
        """
        """
        e = self.get_element(Lap.__AverageHeartRate)
        return int(float(e[0].text)) if e else None

    @property
    def max_heart_rate(self):
        """
        """
        e = self.get_element(Lap.__MaxHeartRate)
        return int(float(e[0].text)) if e else None

    def overlaps(self, lap):
        """
        Returns true if this lap overlaps the other lap.
        """
        return max(self.start_time, lap.start_time) <= min(
            self.finish_time, lap.finish_time
        )

    def info(self, prefix="  ", n="", stream=sys.__stdout__):
        """
        Outputs lap info to a stream.
        """
        lap_title = "Lap" if n == "" else "Lap #{0:d}".format(n)
        lap_title += " [{0} -> {1}]".format(
            TCX.to_timeonly(self.start_time), TCX.to_timeonly(self.finish_time)
        )

        print(prefix + lap_title, file=stream)
        prefix += "  "

        print(prefix + "Start time:  " + TCX.to_ts(self.start_time), file=stream)
        print(prefix + "Finish time: " + TCX.to_ts(self.finish_time), file=stream)
        print(prefix + "Duration:    " + str(TCX.chop_ms(self.duration)), file=stream)
        print(prefix + "Distance:    " + f"{self.distance:,}m", file=stream)
        print(prefix + "Calories:    " + str(self.calories), file=stream)
        print(prefix + "Avg cadence: " + str(self.cadence), file=stream)

        if self.heart_rate:
            print(prefix + "Avg HR:      " + str(self.heart_rate) + " bpm", file=stream)

        if self.max_heart_rate:
            print(
                prefix + "Max HR:      " + str(self.max_heart_rate) + " bpm",
                file=stream,
            )

        print(prefix + "Trackpoints: " + str(len(list(self.trackpoints))), file=stream)
        print("", file=stream)

    def merge(self, lap):
        """
        Merge the lap with the other lap.
        """
        if self.overlaps(lap):
            raise ValueError("Laps should not overlap")

        (earlier, later) = (
            (self, lap) if self.start_time < lap.start_time else (lap, self)
        )

        # Adjust later lap distance
        base_distance = earlier.distance
        for trackpoint in later.trackpoints:
            trackpoint.distance += base_distance

        # Merge trackpoints
        earlier_track = earlier.get_element(Lap.__Track)
        earlier_track.extend(later.get_elements(Lap.__Trackpoint))

        # Copy the merged and adjusted trackpoints to this lap
        self_track = self.get_element(Lap.__Track)
        self_track[:] = earlier_track[:]

        # To avoid any possible inconsistencies we order merged trackpoints by time
        # TCX.sort_children_by(self_track, lambda trackpoint: Trackpoint(trackpoint).time)

        self.start_time = earlier.start_time
        self.total_seconds += lap.total_seconds
        self.distance += lap.distance
        self.calories += lap.calories


class Trackpoint(TCX):
    """
    """

    __Time = "Time"
    __HeartRate = "HeartRateBpm"
    __Distance = "DistanceMeters"
    __Cadence = "Cadence"
    __Watts = "Watts"

    def __init__(self, trackpoint_root: ET.Element):
        super().__init__(trackpoint_root)

    @property
    def time(self):
        """
        Timestamp (datetime)
        """
        return TCX.parse_time(self.get_element(Trackpoint.__Time).text)

    @property
    def distance(self):
        """
        Distance in meters (int)
        """
        return int(self.get_element(Trackpoint.__Distance).text)

    @distance.setter
    def distance(self, x):
        node = self.get_element(Trackpoint.__Distance)
        node.text = str(int(x))

    @property
    def cadence(self):
        """
        Cadence (int)
        """
        return int(self.get_element(Trackpoint.__Cadence).text)

    @cadence.setter
    def cadence(self, x):
        node = self.get_element(Trackpoint.__Cadence)
        node.text = str(int(x))

    @property
    def watts(self):
        """
        Watts (int)
        """
        return int(self.get_element(Trackpoint.__Watts).text)

    @watts.setter
    def watts(self, x):
        node = self.get_element(Trackpoint.__Watts)
        node.text = str(int(x))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scale, concatenate and modify TCX files",
        epilog=f"Example: {sys.argv[0]} --concat activity1.tcx activity2.tcx",
    )

    parser.add_argument("input", type=str, nargs="+", help="Input TCX files")
    parser.add_argument(
        "-v",
        "--verbosity",
        action="store_true",
        help="Output detailed log of operation",
    )
    parser.add_argument(
        "-c",
        "--concat",
        action="store_true",
        help="Concatenate multiple TCX files into one",
    )
    parser.add_argument(
        "-s",
        "--scale",
        nargs="?",
        type=float,
        help="Scale duration, power, cadence and distance by the specified factor",
    )
    parser.add_argument(
        "-o", "--output", nargs="?", help="Output TCX file",
    )

    return parser.parse_args()


def main():
    # args = parse_args()
    # print(args)

    w1 = Workout.load("w1.tcx")  # (args.input[0])
    w2 = Workout.load("w2.tcx")  # (args.input[1])

    w1.info()
    w2.info()

    w1.concat(w2)
    w1.save("merged.tcx")

    # w1.concat(w2)
    # w1.save("merged.tcx")

    # print(w.activity)
    # print(w.start_time)
    # print(w.finish_time)
    # print(w.duration)

    # w.scale(2)
    # w.save("out.tcx")


if __name__ == "__main__":
    main()
