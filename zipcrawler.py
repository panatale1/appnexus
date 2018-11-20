"""AppNexus TechOps assessment"""
import argparse
import gzip
import os
import sys
from datetime import datetime
from re import findall
from shutil import copyfileobj

import daemon
from ansible_vault import Vault
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail

INCOMPRESSIBLE_FILES = ['jpg', 'pdf', 'wma', 'mp3', 'avi', 'mp4', 'gz', 'zip', 'iso']


class ZipCrawler:
    """Class that crawls a directory and compresses files"""
    def __init__(self, directory, threshold, email, dry_run):
        """Sets initial class variables"""
        self.directory = directory
        # Append trailing slash to directory if not passed in
        if self.directory[-1] != '/':
            self.directory += '/'
        # Convert string to int
        self.threshold = int(threshold)
        self.email = email
        self.dry_run = dry_run
        self.compressed_files = []
        self.uncompressed_files = []
        self.space_savings = 0

    def run(self):
        """Primary method for ZipCrawler class"""
        self.crawl_directory()
        self.print_results()
        if not self.dry_run:
            # Do not send email if dry run
            self.send_email()

    def crawl_directory(self):
        """Crawls self.directory looking for files"""
        # Use os.walk to crawl and get files in directory
        for dummy, dummy_1, filenames in os.walk(self.directory):
            # loop over files
            for filename in filenames:
                self.compress(filename)
            # only do files in top level directory
            break

    def compress(self, filename):
        """Compresses or skips files"""
        # Get uncompressed size
        uncompressed_size = os.stat('{}{}'.format(self.directory, filename)).st_size
        print("{} analyzing {}{}".format(datetime.now(), self.directory, filename))
        # Check if uncompressed size is over the threshold or if it's a file that won't compress
        if uncompressed_size < self.threshold:
            print("{} skipping {}{} -- smaller than threshold".format(
                datetime.now(), self.directory, filename))
            self.uncompressed_files.append(filename)
        elif filename.split('.')[-1] in INCOMPRESSIBLE_FILES:
            print("{} skipping {}{} -- file is already highly compressed".format(
                datetime.now(), self.directory, filename))
        else:
            # Compress file, analyze compression ratio
            with open('{}{}'.format(self.directory, filename), 'rb') as input_file:
                with gzip.open('{}{}.gz'.format(self.directory, filename), 'wb') as output_file:
                    copyfileobj(input_file, output_file)
            compressed_size = os.stat('{}{}.gz'.format(self.directory, filename)).st_size
            # Compression ratio is too small, delete the compressed file
            if self.calculate_compression_ratio(uncompressed_size, compressed_size) < 10:
                print("{} skipping {}{} -- less than 10% compression".format(
                    datetime.now(), self.directory, filename))
                self.uncompressed_files.append(filename)
                os.remove('{}{}.gz'.format(self.directory, filename))
            else:
                # Compression ratio isn't too small
                print("{} compressing {}{}".format(datetime.now(), self.directory, filename))
                self.compressed_files.append(filename)
                self.space_savings += (uncompressed_size - compressed_size)
                if self.dry_run:
                    # If dry run, delete compressed file, otherwise delete original
                    os.remove('{}{}.gz'.format(self.directory, filename))
                else:
                    os.remove('{}{}'.format(self.directory, filename))

    def calculate_compression_ratio(self, uncompressed, compressed):  # pylint: disable=no-self-use
        """Calculates compression ratio"""
        return (1 - (compressed/uncompressed)) * 100

    def print_results(self):
        """Prints results to the screen"""
        print("These files were compressed:")
        print(" ".join(self.compressed_files))
        print("")
        print("These files were not compressed:")
        print(" ".join(self.uncompressed_files))
        print("")
        print("Total disk savings: {} bytes".format(self.space_savings))

    def send_email(self):
        """Sends results email"""
        # Read SendGrid API key from Ansible vault
        vault = Vault('Frankenstein')
        api_key = vault.load(open('secrets.yml').read())
        # Set up SendGrid API Client
        send_grid = SendGridAPIClient(apikey=api_key)
        # Set up email message
        from_email = Email('peter@panatale.com')
        to_email = Email(self.email)
        subject = "AppNexus Crawler Compression Results"
        content = "These files were compressed:\n"
        for filename in self.compressed_files:
            content += '{}\n'.format(filename)
        content += "\nThese files were not compressed:\n"
        for filename in self.uncompressed_files:
            content += '{}\n'.format(filename)
        content += '\nTotal disk savings: {} bytes'.format(self.space_savings)
        content = Content("text/plain", content)
        mail = Mail(from_email, subject, to_email, content)
        mail.reply_to = Email('panatale1@gmail.com')
        # Send email message
        dummy = send_grid.client.mail.send.post(request_body=mail.get())


if __name__ == "__main__":
    # Add arguments to parser
    parser = argparse.ArgumentParser()  # pylint: disable=invalid-name
    parser.add_argument("-d", "--directory", help="the directory to crawl")
    parser.add_argument(
        "-t", "--threshold",
        help="the maximum uncompressed file size in bytes, no units")
    parser.add_argument("-e", "--email", help="email to send results to")
    parser.add_argument(
        "--dry-run", help="see visual output without compressing or email", action="store_true")
    parser.add_argument(
        '-b', '--background', help='run as daemon in the background', action="store_true")
    args = parser.parse_args()  # pylint: disable=invalid-name

    # pylint: disable=invalid-name
    email_regex = r'^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$'

    # Check for email validity
    if len(findall(email_regex, args.email)[0]) != 3:
        print("Please enter a valid email address and try again.")
        sys.exit()

    # Check for valid directory
    if not os.path.isdir(args.directory):
        print("That directory does not exist. Please try again.")
        sys.exit()

    # Check for threshold validity
    if not args.threshold.isnumeric():
        print(
            "Please enter a valid number for the threshold and try again. No units, please.")
        sys.exit()

    # If backgrounded, run as daemon
    if args.background:
        with daemon.DaemonContext():
            ZipCrawler(args.directory, args.threshold, args.email, args.dry_run).run()
    else:
        ZipCrawler(args.directory, args.threshold, args.email, args.dry_run).run()
