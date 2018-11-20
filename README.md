###AppNexus Directory Crawler###

Clone the repo into a directory, and install requirements by using:
`pip3 install -r requirements.txt`

Run the program using:
`python3 zipcrawler.py` with the appropriate arguments

Required arguments:
`-d --directory` The directory to crawl
`-e --email` The email to send the results to
`-t --threshold` The minimum size to compress (in bytes)

Optional arguments:
`--dry-run` Doesn't email, doesn't compress
`-b --background` Run in the background as a daemon (does not produce output on the screen)
`-h --help` Display a help menu
