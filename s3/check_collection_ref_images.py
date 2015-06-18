#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys, os
import argparse
from pynux import utils
from boto import connect_s3
from boto.s3.connection import S3Connection, OrdinaryCallingFormat
from boto.s3.key import Key
import urlparse

def check_object_on_s3(nuxeo_id, bucketpath):

    # see if a jp2 file exists on S3 for this object
    conn = connect_s3(calling_format = OrdinaryCallingFormat())    
    bucketpath = bucketpath.strip("/")
    bucketbase = bucketpath.split("/")[0]
    obj_key = nuxeo_id
    s3_url = "s3://{0}/{1}".format(bucketpath, obj_key)
    parts = urlparse.urlsplit(s3_url)

    try:
        bucket = conn.get_bucket(bucketbase)
    except boto.exception.S3ResponseError:
        print "bucket doesn't exist on S3:", bucketbase

    if not(bucket.get_key(parts.path)):
        print "s3_url:", s3_url
        print "bucketpath:", bucketpath
        print "bucketbase:", bucketbase
        print "object doesn't exist on S3:", parts.path

def main(argv=None):

    parser = argparse.ArgumentParser(description='check for existence of jp2 file on s3 for given nuxeo path')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--pynuxrc', default='~/.pynux-prod', help="rc file for use by pynux")

    utils.get_common_options(parser)
    if argv is None:
        argv = parser.parse_args()

    nuxeo_path = argv.path
    bucketpath = argv.bucket

    nx = utils.Nuxeo(rcfile=argv.rcfile, loglevel=argv.loglevel.upper())
    # just for simple objects for now
    objects = nx.children(argv.path)
    print "\nFound objects at {}.\nChecking S3 bucket {} for existence of corresponding files.\nThis could take a while...".format(nuxeo_path, bucketpath)
    i = 0
    for obj in objects:
        nuxeo_id = nx.get_uid(obj['path'])
        check_object_on_s3(nuxeo_id, bucketpath)
        i = i + 1

    print "Done. Checked {} objects".format(i)

if __name__ == "__main__":
    sys.exit(main())
