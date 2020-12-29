# timestamper

This is a mirror of https://gitea.derdritte.net/markus/timestamper, most reference will be to that repository.

## What

This script splits up an exported audiobook from Google Books, which you can download for some of the audiobooks they offer. This combined audiofile is separated into chapters and tagged appropriately (with title and track-number, other tags are copied from the input-file).

## Requirements

* ffmpeg
* python3.7+
* pip (or whatever you want to install the requirements with)
* internet connection (to connect to Google Books via http/s, nothing complicated)
* the exported audiofile from Google Books
* the link to the audiobook you are working with

## Installation

Clone the repo

    git clone https://gitea.derdritte.net/markus/timestamper.git

Switch folder

    cd timestamper

Create and active a virtualenv (optional, but recommended)

    python -m venv .venv
    source .venv/bin/activate

Install dependencies

    .venv $ pip install -r requirements.txt

You are done! You can now run the script.

    .venv $ ./timestamper.py -h
    usage: timestamper.py [-h] (-gi GOOGLE-BOOKS-ID | -gl GOOGLE-LINK | -mf METADATA_FILE) [-o OUTPUT_FOLDER] [-f FORMAT] [-cs CHAPTER_SEPARATOR]
                          [-bc BANNED_CHARACTERS [BANNED_CHARACTERS ...]] [-e EXPORT_ONLY] [-dpp] [-of] [-ds] [-d] [-nm] [-nr]
                          AUDIOFILE
    …

## Quickstart

For installation see above. Once the script is working, you need to download the audiofile from google. This script will not (!) do this for you, this script does not download any copyrighted material whatsoever, it only helps with metadata.

1. Go to <https://play.google.com/books>
2. Some books in your library will show the "Export" option when you click on the three dots on the card of a specific audiobook. Click on that "Export"-link, choose your preferred quality and download the file to a location you can reference easily.
3. Copy the link to the detail-page of the audiobook. You can just click on the picture for the audiobook you are working with and then copy the link from the location-bar; or right-click on the picture and select "Copy Link Location" (Firefox)
4. With all that done, you can now call the script

        .venv $ ./timestamper.py your_audio.m4a -gl google_book_link
    In this example, replace `your_audio.m4a` with the audiofile you exported from Google Books and `google_book_link` with the link to the detail-page you just copied.

    Be aware, you might have to put the link to google in quotes `-gl "https://play.google.com/books/listen?id=AQAAAEBsuD74QM"`, depending on your terminal.
5. You will start to see progress-output or errors in your terminal.
6. That's it!

If you want to try this out before you buy an audiobook, Google Books offers some free audiobooks (at least for now), which will also work with this script. Just make sure the audiobook has the option for "export" available. You can start here: <https://play.google.com/store/books/category/audiobooks>

## Why

I am a fan of [Brandon Sanderson](https://en.wikipedia.org/wiki/Brandon_Sanderson) and wanted to buy the latest book in the Stormlight Archive series. I did check couple of different websites and saw that Google Books offers an export option, so I could use the player of my choice on the device of my choice and Mr. Sanderson has activated the option for [Rhythm of War](https://play.google.com/books/listen?id=AQAAAEBsuD74QM) (which you can also buy DRM-free on [libro.fm](https://libro.fm/audiobooks/9781250759788-rhythm-of-war)).

So I bought the book and went to download the files, which turned out to be one file. The audiobook is over 52 hours long, the file is around 1.5GB in size. That is just simple unusable. I did send a request for chaptered files or a big file with chapter-metadata to Google, but they have other things to do and have not responded to me, at least up until now.

I took a look at the Google Books website and they offer the chapter-metadata for all audiobooks on the respective detail-page of the book (where you can usually also listen to samples). They publicly display the data in hours/minutes/seconds, but have microsecond-based timestamps embedded in the javascript of the page, so I wrote this tool to make that combined and huge file into usable smaller files with proper filenames and meta-tags for chapters.

I do hope some other people will also find this useful.

## Contribute

I am happy to take any suggestions or reasonable feature-requests, although this solution feels pretty over-engineered as it is. Just open a ticket or pull request, or contact me ([@derdritte](https://github.com/derdritte)) directly. I am happy to chat.
