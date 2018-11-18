from ansible_vault import Vault
import argparse
import os
from re import findall
import sendgrid
from sendgrid.helpers.mail import *


class ZipCrawler:
    def __init__(self, directory, threshold, email, dry_run):
        self.directory = directory
        self.threshold = threshold
        self.email = email
        self.dry_run = dry_run
        self.compressed_files = []
        self.uncompressed_files = []
        self.space_savings = 0

    def run(self):
        self.crawl_directory()

    def crawl_directory(self):
        for dirpath, dirnames, filenames in os.walk(self.directory):
            print(filenames)

    def send_email(self):
        vault = Vault('Frankenstein')
        api_key = vault.load(open('secrets.yml').read())
        sg = sendgrid.SendGridAPIClient(apikey=api_key)
        from_email = Email('peter@panatale.com')
        to_email = Email(self.email)
        subject = "AppNexus Crawler Compression Results"
        # TODO: Update content
        content = Content("text/plain", "this is test content")
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
        # raise an error here
        pass

    if not os.path.isdir(args.directory):
        # raise error here
        pass

    ZipCrawler(args.directory, args.threshold, args.email, args.dry_run).run()
