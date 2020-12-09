#!/usr/bin/env python3
import argparse
import os
import re
import requests
import subprocess
import html

from slimit.parser import Parser
from urllib import parse

GOOGLE_LINK = "https://play.google.com/books/listen?id={id}"
metadata = {}

parser = argparse.ArgumentParser(
    description=(
        "Automatically download chapter-timestamps from Google Books and separate an "
        "input-file by those timestamps. Title- and track-attributes will be set. "
        "Google Books url/id (or local file) and the audio-input file are required. "
        "PLEASE NOTE: This will not download any copyrighted material whatsoever, you "
        "have to provide the audiofile yourself."
    ),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    metavar="AUDIOFILE",
    dest="audio_file",
    action="store",
    type=str,
    help="the audiofile that tracks will be exported from",
)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument(
    "-gi",
    "--google-id",
    metavar="GOOGLE-BOOKS-ID",
    dest="google_id",
    action="store",
    type=str,
    help="the id for the audiobook to download the track-data for (e.g. AQAAAEBsuD74QM)",
)
group.add_argument(
    "-gl",
    "--google-link",
    metavar="GOOGLE-LINK",
    dest="google_link",
    action="store",
    type=str,
    help="the link for the audiobook to download the track-data for (e.g. https://play.google.com/books/listen?id=AQAAAEBsuD74QM)",
)
group.add_argument(
    "-mf",
    "--metadata_file",
    metavar="METADATA_FILE",
    dest="metadata_file",
    action="store",
    type=str,
    help="the location of the file that contains the metadata for the tracks",
)

parser.add_argument(
    "-o",
    "--output-folder",
    metavar="OUTPUT_FOLDER",
    type=str,
    help="the folder that the tracks will be written to, created if it does not exist",
)
parser.add_argument(
    "-f",
    "--format",
    metavar="FORMAT",
    default="mp3",
    type=str,
    help=(
        "used as file-extension, ffmpeg will take this and try to derive the audio "
        "codec"
    ),
)
parser.add_argument(
    "-cs",
    "--chapter-separator",
    default="|",
    help="what separates the chapter/part names from the timestamps in the file",
)
parser.add_argument(
    "-bc",
    "--banned-characters",
    nargs="+",
    default="/",
    help="characters that may not show up in generated filenames",
)
parser.add_argument(
    "-e",
    "--export-only",
    type=int,
    default=0,
    help="limit the number of files that will be exported per run (0 means export all)",
)
parser.add_argument(
    "-dpp",
    "--dont-prepend-partnames",
    action="store_true",
    help="do not prepend the part-names to the chapter names (only works with --google-id or --google-link)",
)
parser.add_argument(
    "-of",
    "--override-output",
    action="store_true",
    help="override existing output-files",
)
parser.add_argument(
    "-ds",
    "--dont-skip-existing",
    action="store_true",
    help="do not skip existing output-files during export, combine with --override-outputs to actually override output-files",
)
parser.add_argument(
    "-d", "--debug", action="store_true", help="adds some debug messages to the output"
)
parser.add_argument(
    "-nm",
    "--no-metadata",
    action="store_true",
    help="do not save metadata to exported tracks (ffmpeg will still copy some on it's own)",
)
parser.add_argument(
    "-nr",
    "--no-resume",
    action="store_true",
    help="ignore local metadata (only works with --google-id or --google-link)",
)
args = parser.parse_args()


def die(message: str = "", value=1):
    """
    Prints the optional message then halts the script with non-zero return value.

    :param message: Message to be printed, defaults to ""
    :type message: str, optional
    :param value: Return value on exit, defaults to 1
    :type value: int, optional
    """
    if message:
        print(message)
    exit(value)


def milli(value: str) -> float:
    """
    Tries to convert a given string into 1/1000

    :param value: Value to be converted.
    :type value: str
    :return: 1/1000 of the input on success, None on error.
    :rtype: float
    """
    try:
        return int(value) / 1000
    except ValueError:
        return None


def save_metadata_to_file(
    tracks: list, destination: os.PathLike, metadata: dict = None, source: str = None
):
    """
    Save the passed tracks into the destination file, optionally noting the source.

    :param tracks: A list of tracks you want to save, a list item should look like: {"name": "Chapter Name", "start": 10.0030, "end": 128.1020}
    :type tracks: list
    :param destination: Path for the file that will be written to
    :type destination: os.PathLike
    :param source: A source-reference, embedded in the file as a comment, defaults to None
    :type source: str, optional
    """
    with open(destination, "w") as fp:
        fp.writelines(
            [
                "# Automatically created using timestamper\n",
                f"# Source: {source}\n" if source else "",
            ]
            + (
                [f"# @{k}{args.chapter_separator}{v}\n" for k, v in metadata.items()]
                if metadata
                else []
            )
            + [
                f"{t.get('name')}{args.chapter_separator}{t.get('start')}|{t.get('end')}\n"
                for t in tracks
            ]
        )


def load_metadata_from_file(path: os.PathLike) -> list:
    """
    Load the track-metadata from a file

    :param path: Path to the file the metadata will be read from.
    :type path: os.PathLike
    :return: A list of dicts, containing the tracks
    :rtype: list
    """
    metadata = {}
    if os.path.exists(path):
        try:
            tracks = []
            with open(path, "r") as fp:
                track_lines = fp.readlines()
                for line in track_lines:
                    if line.startswith("# @"):
                        parts = line.lstrip("# @").split(args.chapter_separator)
                        if len(parts) != 2:
                            print(f"Ignored malformed line: {line}")
                            continue
                        metadata[parts[0]] = parts[1].strip()

                    elif line.startswith("#") or not len(line.strip()):
                        continue

                    elif line.count(args.chapter_separator) != 2:
                        die(
                            f'Line "{line}" does not contain the chapter-name/time '
                            f'separator "{args.chapter_separator}" (only) once.'
                        )

                    parts = line.split(args.chapter_separator)
                    tracks.append(
                        {
                            "name": parts[0].strip(),
                            "start": parts[1].strip(),
                            "end": parts[2].strip(),
                        }
                    )
            return (tracks, metadata)
        except PermissionError:
            die("track_file: no permission to read {}".format(args.track_file))


def get_tracks_from_google(url: str) -> list:
    """
    Load metadata from google.

    :param url: Metadata will be scraped from the page identified by this URL.
    :type url: str
    :return: [description]
    :rtype: list
    """
    metadata = {}
    req = requests.get(url)
    if req.status_code == 200:
        _html = req.text
    else:
        die(f"Could not get page from google: {url}")

    matches = re.findall("_OC_contentInfo = ([^;]*)", _html)
    if not matches:
        die("No chapters found in the google-page, maybe the markup has changed?")

    parser = Parser(yacc_optimize=False, lex_optimize=False)
    tree = parser.parse(matches[0])
    chapters = tree.children()[0].children()[0].children()[0].children()[0].children()

    matches = re.findall(r'<title id="main-title">(.*) - Google Play<\/title>', _html)
    if matches:
        metadata["title"] = html.unescape(matches[0])

    tracks = []
    current_part = ""
    last_timestamp = 0
    last_name = ""

    for c in chapters:
        item_number = len(c.items)
        a = ""
        b = ""
        try:
            a = c.items[0].value.strip('"')
            b = c.items[1].value.strip('"')
        except IndexError:
            pass

        if item_number == 1:
            last_name = a
        elif item_number == 2:
            current_part = a
            if milli(c.items[1].value.strip('"')) != last_timestamp:
                tracks.append(
                    {
                        "name": last_name,
                        "start": last_timestamp,
                        "end": milli(b),
                    }
                )
                last_name = a
                last_timestamp = milli(b)
        elif item_number == 3:
            if milli(b) != last_timestamp:
                tracks.append(
                    {
                        "name": last_name,
                        "start": last_timestamp,
                        "end": milli(b),
                    }
                )
            if current_part:
                last_name = f"{current_part}: " + a
            else:
                last_name = a
            last_timestamp = milli(b)

    tracks.append(
        {
            "name": last_name,
            "start": last_timestamp,
            "end": "",
        }
    )
    return tracks, metadata


def main():
    tracks = []
    if not os.path.exists(args.audio_file):
        die("AUDIO_FILE: {} doesn't exist.".format(args.audio_file))

    if not args.output_folder:
        args.output_folder = os.getcwd()

    export_folder = os.path.abspath(args.output_folder)
    if os.path.exists(export_folder):
        pass
    elif os.path.exists(os.path.dirname(export_folder)):
        os.makedirs(export_folder)
    else:
        die(f'OUTPUT_FOLDER: "{export_folder}" does not exist.')

    if args.google_id:
        args.google_link = GOOGLE_LINK.format(id=args.google_id)

    if args.google_link:
        parsed = parse.urlparse(args.google_link)
        id = parse.parse_qs(parsed.query).get("id")
        if not id:
            die(f"This does not look right: {args.google_link}")
        id = id[0]
        destination = f"{export_folder}{os.path.sep}{id}.txt"
        if os.path.exists(destination) and not args.no_resume:
            print(f"Using local metadata: {destination}")
            tracks, metadata = load_metadata_from_file(destination)
        else:
            tracks, metadata = get_tracks_from_google(args.google_link)
            if metadata.get("title"):
                export_folder = (
                    os.getcwd()
                    + os.path.sep
                    + "".join(
                        c
                        for c in metadata.get("title")
                        if c not in args.banned_characters
                    )
                )
                destination = f"{export_folder}{os.path.sep}{id}.txt"
                if os.path.exists(export_folder):
                    pass
                elif os.path.exists(os.path.dirname(export_folder)):
                    os.makedirs(export_folder)
                else:
                    die(f'OUTPUT_FOLDER: "{export_folder}" does not exist.')
        save_metadata_to_file(
            tracks, destination, metadata=metadata, source=args.google_link
        )

    if args.metadata_file:
        tracks, metadata = load_metadata_from_file(args.metadata_file)

    try:
        if not tracks:
            die(
                'No tracks found, check format: "Chapter name|(hh:mm:ss|mm:ss|s*)", the '
                "time represents the length of the chapter."
            )
    except NameError:
        die("Error in reading the TRACKFILE or parsing the google page.")

    print(f"{len(tracks)} tracks to export to {export_folder}.")
    if args.export_only > 0:
        print(f"We are only exporting {args.export_only}.")
    exported = 0
    skipped = 0
    try:
        iterator = 1
        for track in tracks:
            chapter_name = (
                f"{str(iterator).zfill(len(str(len(tracks))))}. "
                + "".join(
                    char for char in track["name"] if char not in args.banned_characters
                ).strip()
            )
            meta_title = "".join(
                char for char in track["name"] if char not in args.banned_characters
            ).strip()
            destination = f"{export_folder}{os.path.sep}{chapter_name}.{args.format}"
            if (not args.dont_skip_existing) and os.path.exists(destination):
                print(f'Skipped "{chapter_name}" ({iterator}/{len(tracks)})')
                skipped += 1
                iterator += 1
                continue
            command = (
                [
                    "ffmpeg",
                    "-y" if args.override_output else "-n",
                    "-ss",
                    str(track["start"]),
                    "-i",
                    args.audio_file,
                ]
                + (["-to", str(track["end"]), "-copyts"] if track["end"] else [])
                + [
                    "-metadata",
                    f"title={meta_title}",
                    "-metadata",
                    f"track={iterator}",
                    f"{destination}",
                ]
            )

            if args.debug:
                print(" ".join(command))
            run_result = subprocess.run(
                command,
                capture_output=True,
            )
            if run_result.returncode != 0:
                print(f"command was: '{' '.join(command)}'")
                die(f"ffmpeg did not terminate normally: {str(run_result.stderr)}")

            print(f'Exported "{chapter_name}" ({iterator}/{len(tracks)})')
            exported += 1
            iterator += 1
            if args.export_only > 0 and args.export_only == exported:
                break

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt, aborted processing.\n")
    print(f"Exported {exported} tracks to {export_folder}.")
    if skipped:
        print(f"Skipped {skipped} files that already existed.")


if __name__ == "__main__":
    main()
