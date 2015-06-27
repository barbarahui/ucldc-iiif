#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef
import logging

def main(argv=None):

    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--replace', action="store_true", help="replace file on s3 if it already exists")
    parser.add_argument('--pynuxrc', default='~/.pynuxrc-prod', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    filename = argv.path.split('/')[-1]
    logfile = '{}.log'.format(filename)
    print "Logfile will be output to: {}\n".format(logfile)
    logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s (%(name)s) [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
 
    nxstash = NuxeoStashRef(argv.path, argv.bucket, argv.pynuxrc, argv.replace)
    nxstash.nxstashref()

    print "\nDone."

if __name__ == "__main__":
    sys.exit(main())
