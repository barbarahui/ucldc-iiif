#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef
import logging
from deepharvest.deepharvest_nuxeo import DeepHarvestNuxeo

def main(argv=None):

    parser = argparse.ArgumentParser(description='For Nuxeo collection, create jp2 versions of image files and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path to collection")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--pynuxrc', default='~/.pynuxrc-prod', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    logging.basicConfig(filename='ucldc-iiif.log', level=logging.DEBUG, format='%(asctime)s (%(name)s) [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
 
    dh = DeepHarvestNuxeo(argv.path, argv.bucket, argv.pynuxrc)

    objects = dh.fetch_objects()
    for obj in objects:
        nxstash = NuxeoStashRef(obj['path'], argv.bucket, argv.pynuxrc)
        stashed = nxstash.nxstashref()
        for c in dh.fetch_components(obj):
            nxstash = NuxeoStashRef(c['path'], argv.bucket, argv.pynuxrc) 
            stashed = nxstash.nxstashref()

if __name__ == "__main__":
    sys.exit(main())
