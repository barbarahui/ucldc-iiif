#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef
import logging
from deepharvest.deepharvest_lija import DeepHarvestLija
import json

def main(argv=None):

    parser = argparse.ArgumentParser(description='For LIJA, create jp2 versions of image files and stash in S3. *This is a temporary workaround until we reload in Nuxeo*.')
    parser.add_argument('path', help="Nuxeo document path to collection")
    parser.add_argument('--bucket', default='ucldc-nuxeo-ref-images', help="S3 bucket name")
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
 
    dh = DeepHarvestLija(argv.path, argv.bucket, pynuxrc=argv.pynuxrc)
    regular_objects, qtvr_objects = dh.fetch_objects()

    ##########################
    # stash regular object images
    ##########################
    report = {}
    for obj in regular_objects:
        print obj['path']
        nxstash = NuxeoStashRef(obj['path'], argv.bucket, argv.pynuxrc, argv.replace)
        report[nxstash.uid] = nxstash.nxstashref()
        for c in dh.fetch_components(obj):
            nxstash = NuxeoStashRef(c['path'], argv.bucket, argv.pynuxrc) 
            report[nxstash.uid] = nxstash.nxstashref()

    # output report to json file
    reportfile = "reports/{}-regular.json".format(collection)
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

    ##########################
    # stash QTVR object images
    ##########################
    report = {}
    for obj in qtvr_objects:
        # just stash the tiff
        print obj['path']
        parent_md, component_md = dh.get_qtvr_metadata(obj)
        tiff_uid = parent_md['id']
        tiff_full_md = dh.nx.get_metadata(uid=tiff_uid)
        tiff_path = tiff_full_md['path'] 
        nxstash = NuxeoStashRef(tiff_path, argv.bucket, argv.pynuxrc, argv.replace)
        report[nxstash.uid] = nxstash.nxstashref()

    # output report to json file
    reportfile = "reports/{}-qtvr.json".format(collection)
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
