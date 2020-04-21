#!/usr/bin/env python3

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime, timedelta


class TCX:
    """
    The typical TCX file could have the following structure:

<TrainingCenterDatabase>
    <Activities>
        <Activity Sport="Biking">
            <Id>2020-04-14T17:12:26.000Z</Id>
            <Lap StartTime="2020-04-14T17:12:26.000Z">
                <TotalTimeSeconds>1840</TotalTimeSeconds>
                <DistanceMeters>13036</DistanceMeters>
                <Calories>190</Calories>
                <AverageHeartRateBpm>
                    <Value>154</Value>
                </AverageHeartRateBpm>
                <Intensity>Active</Intensity>
                <Cadence>79</Cadence>
                <TriggerMethod>Manual</TriggerMethod>
                <Track>
                    <Trackpoint>
                        <Time>2020-04-14T17:12:27.820Z</Time>
                        <DistanceMeters>0</DistanceMeters>
                        <HeartRateBpm>
                            <Value>99</Value>
                        </HeartRateBpm>
                        <Cadence>57</Cadence>
                        <Extensions>
                            <ns3:TPX>
                                <ns3:Watts>40</ns3:Watts>
                            </ns3:TPX>
                        </Extensions>
                    </Trackpoint>
                    <Trackpoint>
                        <Time>2020-04-14T17:12:28.465Z</Time>
                        <DistanceMeters>3</DistanceMeters>
                        <HeartRateBpm>
                            <Value>89</Value>
                        </HeartRateBpm>
                        <Cadence>57</Cadence>
                        <Extensions>
                            <ns3:TPX>
                                <ns3:Watts>40</ns3:Watts>
                            </ns3:TPX>
                        </Extensions>
                    </Trackpoint>
                </Track>
            </Lap>
            <Notes>Bike Model</Notes>
        </Activity>
    </Activities>
</TrainingCenterDatabase>
    """

    Lap = "Lap"

    TotalTime = "TotalTimeSeconds"

    Track = "Track"
    Trackpoint = "Trackpoint"

    Time = "Time"
    HeartRate = "HeartRateBpm"
    Distance = "DistanceMeters"
    Cadence = "Cadence"
    Watts = "Watts"


def get_elements(tree, name):
    """
    Recursively find elements of the given tree whose tag
    contains the given string.
    """
    return (elem for elem in tree.iter() if name in elem.tag)


def scale(
    tree, scale_factor, scale_distance=True, scale_cadence=True, scale_watts=True
):
    """
    For the cases when a treadmill or bike measuers incorrect distance, cadence or watts
    we can adjust them keeping the same time and gps coordinates. Typically this is the case
    with incorrectly calibrated indoor equipment or outdoor trackers.
    """

    def scale_value(root, node_name, scale_factor):
        for node in get_elements(root, node_name):
            node.text = str(int(float(node.text) * scale_factor))

    for lap in get_elements(tree, TCX.Lap):
        for trackpoint in get_elements(lap, TCX.Trackpoint):

            if scale_distance:
                scale_value(trackpoint, TCX.Distance, scale_factor)

            if scale_cadence:
                scale_value(trackpoint, TCX.Cadence, scale_factor)

            if scale_watts:
                scale_value(trackpoint, TCX.Watts, scale_factor)


def read(file):
    """
    Read and parse TCX file.
    Return root of the workout XML-tree.
    """
    return ET.parse(file)


def write(tree, file):
    """
    Save workout tree as TCX file.
    """
    encoding = "utf-8"

    # Write to memory buffer, since ElementTree
    # doesn't include XML declaration.
    # Decode byte stream as a string and remove
    # namespace (e.g. "<ns3:...>") information from the string.
    mem_buf = BytesIO()
    tree.write(mem_buf, encoding=encoding, xml_declaration=True)
    s = mem_buf.getvalue().decode(encoding)
    s = re.sub(r"ns\d+:", "", s)

    with open(file, "w") as f2:
        print(s, file=f2)


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


if __name__ == "__main__":
    main()
