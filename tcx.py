#!/usr/bin/env python3

import argparse
import re
import sys
import xml.etree.ElementTree as ET


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
