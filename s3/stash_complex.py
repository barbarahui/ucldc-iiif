#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from pynux import utils
import boto
import nxstashref

""" temp script. need to fold this logic into stash_collection_ref_images.py """

def main(argv=None):
    parser = argparse.ArgumentParser(description='Stash reference images in S3 for a given COMPLEX Nuxeo collection.')
    parser.add_argument('path', help="Nuxeo Path to collection")
    parser.add_argument('bucket', help="S3 bucket name")

    utils.get_common_options(parser)
    if argv is None:
        argv = parser.parse_args()

    path = argv.path
    aws_bucket = argv.bucket

    nx = utils.Nuxeo(rcfile=argv.rcfile, loglevel=argv.loglevel.upper())

    # establish a boto connection to S3 that we can reuse
    s3_conn = boto.connect_s3()

    # documents = get_all_images(path)
    parents = nx.children(path)
    for parent in parents:
        path = parent['path']
        documents = nx.children(path) # FIXME right now this assumes that all child objects are convertible images
        for document in documents:
            path = document['path']
            s3_location = nxstashref.nxstashref(path, aws_bucket, nx, s3_conn)
            print "stashed in s3:", path, s3_location
         
def get_all_images(collection_path):
    """ identify all master image files within a given Nuxeo collection """
    pass

if __name__ == "__main__":
    sys.exit(main())

"""
Copyright © 2014, Regents of the University of California
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the University of California nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
