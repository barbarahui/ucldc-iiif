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
import shutil

S3_URL_FORMAT = "s3://{0}/{1}"
PRECONVERT = ['image/jpeg', 'image/gif']

class NuxeoStashRef(object):

    ''' Base class for fetching a Nuxeo object, converting it to jp2 and stashing it in S3 '''

    def __init__(self, path, bucket, pynuxrc, replace=False):
       
        self.logger = logging.getLogger(__name__)
        
        self.path = path
        self.bucket = bucket
        self.pynuxrc = pynuxrc
        self.replace = replace
        self.logger.info("replace: {}".format(self.replace))

        self.nx = utils.Nuxeo(rcfile=self.pynuxrc)
        self.uid = self.nx.get_uid(self.path)
        self.source_download_url = self._get_object_download_url()
        self.source_mimetype = self._get_object_mimetype()

        self.tmp_dir = tempfile.mkdtemp()
        self.source_filename = os.path.basename(self.path)
        self.source_filepath = os.path.join(self.tmp_dir, self.source_filename)
        self.prepped_filepath = os.path.join(self.tmp_dir, 'prepped.tiff')

        name, ext = os.path.splitext(self.source_filename)
        self.jp2_filepath = os.path.join(self.tmp_dir, name + '.jp2')

        self.convert = Convert()
         
    def nxstashref(self):

        # first see if this looks like a valid file to try to convert 
        passed, precheck_msg = self.convert._pre_check(self.source_mimetype)
        if not passed:
            return precheck_msg

        # grab the file to convert
        self._download_nuxeo_file()

        # convert to jp2
        jp2_code, jp2_msg = self._create_jp2()
        if jp2_code:
            return jp2_msg

        # stash in s3
        self.logger.debug("Converted to jp2, now about to stash.")
        s3_location = self._s3_stash()

        # clean up
        self._remove_tmp()

        return s3_location

    def _remove_tmp(self):
        ''' clean up after ourselves '''
        shutil.rmtree(self.tmp_dir)

    def _create_jp2(self):
        ''' Sample class for converting a local image to a jp2
            Works for some compressed tiffs, but will likely need subclassing.
        '''
        # prep file for conversion to jp2 
        if self.source_mimetype in PRECONVERT:
            self.convert._pre_convert(self.source_filepath, self.prepped_filepath)
        elif self.source_mimetype == 'image/tiff':
            self.convert._uncompress_tiff(self.source_filepath, self.prepped_filepath)
        else:
            self.logger.warning("Did not know how to prep file with mimetype {} for conversion to jp2.".format(self.source_mimetype))
            return

        # create jp2
        jp2_retcode, jp2_msg = self.convert._tiff_to_jp2(self.prepped_filepath, self.jp2_filepath)

        # clean up
        #os.remove(uncompressed_file)
        #os.rmdir(tmp_dir)

        return jp2_retcode, jp2_msg 

    def _download_nuxeo_file(self):
        res = requests.get(self.source_download_url, auth=self.nx.auth)
        res.raise_for_status()
        with open(self.source_filepath, 'wb') as f:
            for block in res.iter_content(1024):
                if block:
                    f.write(block)
                    f.flush()
        self.logger.info("Downloaded file from {} to {}".format(self.source_download_url, self.source_filepath))

    def _get_object_download_url(self):
        """ Get object file download URL """
        parts = urlparse.urlsplit(self.nx.conf["api"])
        filename = self.path.split('/')[-1]
        url = '{}://{}/Nuxeo/nxbigfile/default/{}/file:content/{}'.format(parts.scheme, parts.netloc, self.uid, filename)

        return url 

    def _get_object_mimetype(self):
        """ Get object mime-type from Nuxeo metadata """
        mimetype = None

        metadata = self.nx.get_metadata(path=self.path)
        picture_views = metadata['properties']['picture:views']
        for pv in picture_views:
            if pv['tag'] == 'original':
                mimetype = pv['content']['mime-type']

        return mimetype

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
       elif self.replace:
           key = bucket.get_key(parts.path)
           key.set_metadata("Content-Type", mimetype)
           key.set_contents_from_filename(self.jp2_filepath)
           self.logger.info("re-uploaded {}".format(s3_url))
       else:
           self.logger.info("key already existed; not re-uploading {0}".format(s3_url))

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
