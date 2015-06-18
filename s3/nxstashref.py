#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from pynux import utils
import requests
import subprocess
import tempfile
import pprint
import boto
import magic
import urlparse

pp = pprint.PrettyPrinter()

def main(argv=None):

    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', nargs=1, help="Nuxeo document path")
    parser.add_argument('bucket', nargs=1, help="S3 bucket name")
    # add optional argument to skip stash if object already exists on S3. need make this OOP.
    utils.get_common_options(parser)

    if argv is None:
        argv = parser.parse_args()
    
    path = argv.path[0]
    bucket = argv.bucket[0]
    nx = utils.Nuxeo(rcfile=argv.rcfile, loglevel=argv.loglevel.upper())

    nxstashref(path, bucket, nx)

def nxstashref(path, bucket, nx, s3_conn=None):
    """ grab image from Nuxeo, convert to jp2 and stash in S3 """
    uid = nx.get_uid(path)
    tmp_dir = tempfile.mkdtemp()
    filename = os.path.basename(path)

    # skip if jp2 is already stashed on s3
    s3_url = get_s3_url(bucket, uid)
    if check_s3_obj_exists(bucket, uid):
        print "object already exists on s3. not stashing."
        return s3_url

    # make sure that this is a convertible image file
    # in https://github.com/DDMAL/diva.js/blob/master/source/processing/process.py ooks like it uses imagemagick to convert other types of image files into tiffs.

    # grab the file to convert
    filepath = os.path.join(tmp_dir, filename)
    download_url = os.path.join('https://nuxeo.cdlib.org/Nuxeo/nxbigfile/default', uid, 'file:content', filename) # FIXME add get_download_url to pynux utils
    download_nuxeo_file(download_url, filepath, nx.auth)
    
    # convert to jp2
    input_file = filepath
    name, ext = os.path.splitext(filename)
    jp2_file = os.path.join(tmp_dir, name + '.jp2')
    create_jp2(input_file, jp2_file)

    # stash in S3
    s3_location = s3_stash(jp2_file, bucket, uid, s3_conn) 

    # delete temp stuff we're not using anymore
    os.remove(filepath)
    os.remove(jp2_file)
    os.rmdir(tmp_dir)

    return s3_location 

def check_s3_obj_exists(bucket, uid, conn=None):
    """ do a quick check for the existence of an object in an s3 bucket """
    if conn is None:
        conn = boto.connect_s3()

    bucket = conn.get_bucket(bucket)

    if bucket.get_key(uid):    
        return True
    else:
        return False

def download_nuxeo_file(download_from, download_to, nuxeo_auth):
    # retry twice, as Nuxeo seems prone to intermittent 503 HTTP errors. (See http://www.mobify.com/blog/http-requests-are-hard/)
    session = requests.Session()
    session.mount("http://", requests.adapters.HTTPAdapter(max_retries=5))
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=5))

    try:
        res = session.get(download_from, auth=nuxeo_auth)
        #res.raise_for_status() 
        with open(download_to, 'wb') as f:
            for block in res.iter_content(1024):
                if block:
                    f.write(block)
                    f.flush()
    except:
        print "could not get to:", download_from

def create_jp2(input_file, output_file):

    tmp_dir = tempfile.mkdtemp()

    # first need to make sure tiff is uncompressed - demo kdu_compress only deals with uncompressed tiffs
    uncompressed_file = os.path.join(tmp_dir, 'uncompressed.tiff')
    uncompress_image(input_file, uncompressed_file)

    # create jp2 using Kakadu
    # Settings recommended as a starting point by Jon Stroop. See https://groups.google.com/forum/?hl=en#!searchin/iiif-discuss/kdu_compress/iiif-discuss/OFzWFLaWVsE/wF2HaykHcd0J
    kdu_compress_location = '/apps/nuxeo/kakadu/kdu_compress' # FIXME add config to .pynuxrc
    try:
        subprocess.call([kdu_compress_location,
                         "-i", uncompressed_file,
                         "-o", output_file,
                         "-quiet",
                         "-rate", "2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,.08266171",
                         "Creversible=yes",
                         "Clevels=7",
                         "Cblk={64,64}",
                         "-jp2_space", "sRGB",
                         "Cuse_sop=yes",
                         "Cuse_eph=yes",
                         "Corder=RLCP",
                         "ORGgen_plt=yes",
                         "ORGtparts=R",
                         "Stiles={1024,1024}",
                         "-double_buffering", "10",
                         "-num_threads", "4",
                         "-no_weights"
                         ])

    except subprocess.CalledProcessError as e:
        print e.output

    os.remove(uncompressed_file)
    os.rmdir(tmp_dir)

    return output_file 


def uncompress_image(input_file, output_file):
    # use tiffcp to uncompress: http://www.libtiff.org/tools.html
    # tiff info ucm_dr_001_001_a.tif # gives you info on whether or not this tiff is compressed
    # FIXME make sure tiffcp is installed - add to required packages
    subprocess.call(['tiffcp',
        "-c", "none",
        input_file,
        output_file]) 


def get_s3_url(bucketname, obj_key):
    """ compose the s3_url for a given bucketname and object key """
    s3_url = "s3://{0}/{1}".format(bucketname, obj_key)

    return s3_url

def s3_stash(filepath, bucketname, obj_key, conn=None):
    """ Stash a file in the named bucket. 
         `conn` is an optional boto.connect_s3()
    """
    s3_url = get_s3_url(bucketname, obj_key)
    parts = urlparse.urlsplit(s3_url)
    mimetype = magic.from_file(filepath, mime=True)
    if conn is None:
        conn = boto.connect_s3()

    bucket = conn.get_bucket(bucketname)

    if not(bucket.get_key(parts.path)):
        key = bucket.new_key(parts.path)
        key.set_metadata("Content-Type", mimetype)
        key.set_contents_from_filename(filepath)
        print "created", s3_url
    else:
        print "bucket already existed:", s3_url
        pass # tell us the key already existed. use logging?

    return s3_url

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
