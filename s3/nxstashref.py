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
from s3.convert import Convert

S3_URL_FORMAT = "s3://{0}/{1}"

class NuxeoStashRef(object):

    ''' Base class for fetching a Nuxeo object, converting it to jp2 and stashing it in S3 '''

    def __init__(self, path, bucket, pynuxrc):
       
        self.logger = logging.getLogger(__name__)
        
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

        self.convert = Convert()
         
    def nxstashref(self):

        # first see if this looks like a valid file to try to convert 
        if not self._pre_check():
            return "{} did not pass precheck".format(self.path)

        # grab the file to convert
        self._download_nuxeo_file()

        # convert to jp2
        self._create_jp2()

        # stash in s3
        self.logger.debug("Converted to jp2, now about to stash.")
        s3_location = self._s3_stash()

        # clean up
        self._remove_tmp()

        return s3_location

    def _pre_check(self):
        ''' do a basic pre-check on the object to see if we think it's a convertible '''

        self.logger.info("Object {} did not pass pre-check. Not processing and stashing.".format(self.path))

        return False

    def _remove_tmp(self):
        ''' clean up after ourselves '''
        os.remove(self.source_filepath)
        os.remove(self.jp2_filepath)
        os.rmdir(self.tmp_dir)

    def _create_jp2(self):
        ''' Sample class for converting a local image to a jp2
            Works for some compressed tiffs, but will likely need subclassing.
        '''
        tmp_dir = tempfile.mkdtemp()

        # uncompress file
        uncompressed_file = os.path.join(tmp_dir, 'uncompressed.tiff')
        self.convert._uncompress_tiff(self.source_filepath, uncompressed_file)

        # create jp2
        self.convert._tiff_to_jp2(uncompressed_file, self.jp2_filepath)

        # clean up
        os.remove(uncompressed_file)
        os.rmdir(tmp_dir)

        return self.jp2_filepath 

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
       
       conn = boto.connect_s3() 

       try:
           bucket = conn.get_bucket(bucketbase)
       except boto.exception.S3ResponseError:
           bucket = conn.create_bucket(bucketbase)

       if not(bucket.get_key(parts.path)):
           key = bucket.new_key(parts.path)
           key.set_metadata("Content-Type", mimetype)
           key.set_contents_from_filename(self.jp2_filepath)
           self.logger.info("created {0}".format(s3_url))
       else:
           self.logger.info("key already existed; not creating {0}".format(s3_url))

       return s3_url 


def main(argv=None):
    pass
    '''
    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--pynuxrc', default='~/.pynuxrc-prod', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    nxstash = NuxeoStashRef(argv.path, argv.bucket, argv.pynuxrc)
    stashed = nxstash.nxstashref()
    '''

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
