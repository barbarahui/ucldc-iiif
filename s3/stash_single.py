#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef
import logging
import json

def main(argv=None):

    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--pynuxrc', default='~/.pynuxrc-prod', help="rc file for use by pynux")
    parser.add_argument('--replace', action="store_true", help="replace file on s3 if it already exists")
    if argv is None:
        argv = parser.parse_args()

    # logging
    # FIXME would like to name log with nuxeo UID 
    filename = argv.path.split('/')[-1]
    logfile = "logs/{}.log".format(filename)
    print "LOG:\t{}".format(logfile)
    logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s (%(name)s) [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
 
    # convert and stash jp2
    nxstash = NuxeoStashRef(argv.path, argv.bucket, argv.pynuxrc, argv.replace)
    report = nxstash.nxstashref()

    # output report to json file
    reportfile = "reports/{}.json".format(filename)
    with open(reportfile, 'w') as f:
        json.dump(report, f, sort_keys=True, indent=4)

    # parse report to give basic stats
    print "REPORT:\t{}".format(reportfile)
    print "SUMMARY:"
    if 'already_s3_stashed' in report.keys():
        print "already stashed:\t{}".format(report['already_s3_stashed'])
    print "converted:\t{}".format(report['converted'])
    print "stashed:\t{}".format(report['stashed']) 

    print "\nDone."

if __name__ == "__main__":
    sys.exit(main())
