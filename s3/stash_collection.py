#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef
import logging
from deepharvest.deepharvest_nuxeo import DeepHarvestNuxeo
import json

def main(argv=None):

    parser = argparse.ArgumentParser(description='For Nuxeo collection, create jp2 versions of image files and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path to collection")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--replace', action="store_true", help="replace file on s3 if it already exists")
    parser.add_argument('--pynuxrc', default='~/.pynuxrc-prod', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    collection = argv.path.split('/')[-1]

    # logging
    logfile = 'logs/{}.log'.format(collection)
    print "LOG:\t{}".format(logfile)
    logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s (%(name)s) [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
 
    dh = DeepHarvestNuxeo(argv.path, argv.bucket, pynuxrc=argv.pynuxrc)

    report = {}
    objects = dh.fetch_objects()
    for obj in objects:
        nxstash = NuxeoStashRef(obj['path'], argv.bucket, argv.pynuxrc, argv.replace)
        report[nxstash.uid] = nxstash.nxstashref()
        for c in dh.fetch_components(obj):
            nxstash = NuxeoStashRef(c['path'], argv.bucket, argv.pynuxrc) 
            report[nxstash.uid] = nxstash.nxstashref()

    # output report to json file
    reportfile = "reports/{}.json".format(collection)
    with open(reportfile, 'w') as f:
        json.dump(report, f, sort_keys=True, indent=4)

    # parse report to give basic stats
    report = json.load(open(reportfile))
    print "REPORT:\t{}".format(reportfile)
    print "SUMMARY:"
    print "processed:\t{}".format(len(report))
    not_image = len([key for key, value in report.iteritems() if not value['is_image']['is_image']])
    print "not image:\t{}".format(not_image)
    unrecognized = len([key for key, value in report.iteritems() if not value['precheck']['pass']])
    print "not convertible:\t{}".format(unrecognized)
    converted = len([key for key, value in report.iteritems() if value['converted']])
    print "converted:\t{}".format(converted)
    stashed = len([key for key, value in report.iteritems() if value['stashed']])
    print "stashed:\t{}".format(stashed)

    print "\nDone."

if __name__ == "__main__":
    sys.exit(main())
