#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from pynux import utils
import requests
import subprocess
import tempfile
import boto
import magic
import urlparse
import logging

S3_URL_FORMAT = "s3://{0}/{1}"

class NuxeoStashRef(object):

    ''' Base class for converting nuxeo images to jp2 and stashing them in S3 '''

    def __init__(self, path, bucket, pynuxrc):
       
        self.path = path
        self.bucket = bucket
        self.pynuxrc = pynuxrc

        self.nx = utils.Nuxeo(rcfile=self.pynuxrc)
        self.uid = self.nx.get_uid(self.path)
        self.source_download_url = self._get_object_download_url(self.uid, self.path)

        self.tmp_dir = tempfile.mkdtemp()
        self.source_filename = os.path.basename(self.path)
        self.source_filepath = os.path.join(self.tmp_dir, self.source_filename)

        name, ext = os.path.splitext(self.source_filename)
        self.jp2_filepath = os.path.join(self.tmp_dir, name + '.jp2')
         
    def nxstashref(self, s3_conn=None):

        # grab the file to convert
        self._download_nuxeo_file()

        # convert to jp2
        self._create_jp2()

        # stash in s3
        s3_location = self._s3_stash()

        # clean up
        self._remove_tmp()

        return s3_location

    def _remove_tmp(self):
        ''' clean up after ourselves '''
        os.remove(self.source_filepath)
        os.remove(self.jp2_filepath)
        os.rmdir(self.tmp_dir)

    def _create_jp2(self):
        ''' Sample class for converting a local image to a jp2
            This should work for compressed tiffs like those in asset-library/UCM/Ramicova
            But this will likely need to be sub-classed for many (most?) collections.
        '''
        tmp_dir = tempfile.mkdtemp()

        uncompressed_file = os.path.join(tmp_dir, 'uncompressed.tiff')
        self._uncompress_image(self.source_filepath, uncompressed_file)

        # create jp2 using Kakadu
        # Settings recommended as a starting point by Jon Stroop. See https://groups.google.com/forum/?hl=en#!searchin/iiif-discuss/kdu_compress/iiif-discuss/OFzWFLaWVsE/wF2HaykHcd0J
        kdu_compress_location = '/apps/nuxeo/kakadu/kdu_compress' # FIXME add config
        subprocess.call([kdu_compress_location,
                             "-i", uncompressed_file,
                             "-o", self.jp2_filepath,
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

        os.remove(uncompressed_file)
        os.rmdir(tmp_dir)

        return self.jp2_filepath 

    def _uncompress_image(self, input_file, output_file):
        # use tiffcp to uncompress: http://www.libtiff.org/tools.html
        # tiff info ucm_dr_001_001_a.tif # gives you info on whether or not this tiff is compressed
        # FIXME make sure tiffcp is installed - add to required packages
        subprocess.call(['tiffcp',
            "-c", "none",
            input_file,
            output_file])

    def _download_nuxeo_file(self):
        res = requests.get(self.source_download_url, auth=self.nx.auth)
        res.raise_for_status()
        with open(self.source_filepath, 'wb') as f:
            for block in res.iter_content(1024):
                if block:
                    f.write(block)
                    f.flush()

    def _get_object_download_url(self, nuxeo_id, nuxeo_path):
        """ Get object file download URL. We should really put this logic in pynux """
        parts = urlparse.urlsplit(self.nx.conf["api"])
        filename = nuxeo_path.split('/')[-1]
        url = '{}://{}/Nuxeo/nxbigfile/default/{}/file:content/{}'.format(parts.scheme, parts.netloc, nuxeo_id, filename)

        return url 


    def _s3_stash(self):
       """ Stash file in S3 bucket. 
       """
       bucketpath = self.bucket.strip("/")
       bucketbase = self.bucket.split("/")[0]   
       s3_url = S3_URL_FORMAT.format(bucketpath, self.uid)
       parts = urlparse.urlsplit(s3_url)
       mimetype = magic.from_file(self.jp2_filepath, mime=True)
       
       logging.debug('s3_url: {0}'.format(s3_url))
       logging.debug('bucketpath: {0}'.format(bucketpath))
       logging.debug('bucketbase: {0}'.format(bucketbase))
 
       conn = boto.connect_s3() 

       try:
           bucket = conn.get_bucket(bucketbase)
       except boto.exception.S3ResponseError:
           bucket = conn.create_bucket(bucketbase)

       if not(bucket.get_key(parts.path)):
           key = bucket.new_key(parts.path)
           key.set_metadata("Content-Type", mimetype)
           key.set_contents_from_filename(self.jp2_filepath)
           logging.info("created {0}".format(s3_url))
       else:
           logging.info("key already existed; not creating {0}".format(s3_url))

       return s3_url 


def main(argv=None):
    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--pynuxrc', default='~./pynuxrc-prod', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    nxstash = NuxeoStashRef(argv.path, argv.bucket, argv.pynuxrc)
    stashed = nxstash.nxstashref()

    print stashed 

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
