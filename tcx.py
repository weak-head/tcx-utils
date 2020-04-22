#!/usr/bin/env python3

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime, timedelta


class TCX:
    """
    """

    __TimeFormat = "%Y-%m-%dT%H:%M:%S.%fZ"

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
        """
        return self._root.get(name)

    @staticmethod
    def parse_time(time_string):
        """
        """
        return datetime.strptime(time_string, TCX.__TimeFormat)


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
        """
        return (Lap(lap) for lap in self.get_elements(Workout.__Lap))

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

        with open(file, "w") as f2:
            print(s, file=f2)

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


class Lap(TCX):
    """
    """

    __StartTime = "StartTime"
    __TotalTime = "TotalTimeSeconds"
    __Distance = "DistanceMeters"
    __Calories = "Calories"
    __AverageHeartRate = "AverageHeartRateBpm"
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
        return Lap.parse_time(self.get_attribute(Lap.__StartTime))

    @start_time.setter
    def start_time(self, x):
        pass

    @property
    def finish_time(self):
        """
        """
        last_trackpoint = sorted(
            self.trackpoints, key=lambda tp: tp.time, reverse=True
        )[0]
        return last_trackpoint.time


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
    args = parse_args()
    print(args)

    # w = Workout.load(args.input[0])
    # w.scale(2)
    # w.save("out.tcx")


if __name__ == "__main__":
    main()
