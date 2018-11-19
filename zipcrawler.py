from ansible_vault import Vault
import argparse
from datetime import datetime
import gzip
import os
from re import findall
import sendgrid
from sendgrid.helpers.mail import *
from shutil import copyfileobj

INCOMPRESSIBLE_FILES = ['jpg', 'pdf', 'wma', 'mp3', 'avi', 'mp4', 'gz', 'zip', 'iso']


class ZipCrawler:
    def __init__(self, directory, threshold, email, dry_run):
        self.directory = directory
        if self.directory[-1] != '/':
            self.directory += '/'
        self.threshold = int(threshold)
        self.email = email
        self.dry_run = dry_run
        self.compressed_files = []
        self.uncompressed_files = []
        self.space_savings = 0

    def run(self):
        self.crawl_directory()
        self.print_results()
        if not self.dry_run:
            self.send_email()

    def crawl_directory(self):
        for dirpath, dirnames, filenames in os.walk(self.directory):
            for filename in filenames:
                self.compress(filename)
            break

    def compress(self, filename):
        uncompressed_size = os.stat('{}{}'.format(self.directory, filename)).st_size
        print("{} analyzing {}{}".format(datetime.now(), self.directory, filename))
        if uncompressed_size < self.threshold:
            print("{} skipping {}{} -- smaller than threshold".format(
                datetime.now(), self.directory, filename))
            self.uncompressed_files.append(filename)
        elif filename.split('.')[-1] in INCOMPRESSIBLE_FILES:
            print("{} skipping {}{} -- file is already highly compressed".format(
                datetime.now(), self.directory, filename))
        else:
            with open('{}{}'.format(self.directory, filename), 'rb') as input_file:
                with gzip.open('{}{}.gz'.format(self.directory, filename), 'wb') as output_file:
                    copyfileobj(input_file, output_file)
            compressed_size = os.stat('{}{}.gz'.format(self.directory, filename)).st_size
            if self.calculate_compression_ratio(uncompressed_size, compressed_size) < 10:
                print("{} skipping {}{} -- less than 10% compression".format(
                    datetime.now(), self.directory, filename)) 
                self.uncompressed_files.append(filename)
                os.remove('{}{}.gz'.format(self.directory, filename))
            else:
                print("{} compressing {}{}".format(datetime.now(), self.directory, filename))
                self.compressed_files.append(filename)
                self.space_savings += (uncompressed_size - compressed_size)
                if self.dry_run:
                    os.remove('{}{}.gz'.format(self.directory, filename))
                else:
                    os.remove('{}{}'.format(self.directory, filename))

    def calculate_compression_ratio(self, uncompressed, compressed):
        return (1 - (compressed/uncompressed)) * 100

    def print_results(self):
        print("These files were compressed:")
        print(" ".join(self.compressed_files))
        print("")
        print("These files were not compressed:")
        print(" ".join(self.uncompressed_files))
        print("")
        print("Total disk savings: {} bytes".format(self.space_savings))

    def send_email(self):
        vault = Vault('Frankenstein')
        api_key = vault.load(open('secrets.yml').read())
        sg = sendgrid.SendGridAPIClient(apikey=api_key)
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
        response = sg.client.mail.send.post(request_body=mail.get())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="the directory to crawl")
    parser.add_argument("-t", "--threshold", help="the maximum uncompressed file size")
    parser.add_argument("-e", "--email", help="email to send results to")
    parser.add_argument(
        "--dry-run", help="see visual output without compressing or email", action="store_true")
    args = parser.parse_args()

    email_regex = '^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$'

    if len(findall(email_regex, args.email)) != 3:
        # TODO: raise an error here
        pass

    if not os.path.isdir(args.directory):
        # TODO: raise error here
        pass

    ZipCrawler(args.directory, args.threshold, args.email, args.dry_run).run()
