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
import urllib

S3_URL_FORMAT = "s3://{0}/{1}"
PRECONVERT = ['image/jpeg', 'image/gif', 'image/png']

class NuxeoStashRef(object):

    ''' Base class for fetching a Nuxeo object, converting it to jp2 and stashing it in S3 '''

    def __init__(self, path, bucket, pynuxrc, replace=False):
       
        self.logger = logging.getLogger(__name__)
        
        self.path = urllib.quote(path)
        self.bucket = bucket
        self.pynuxrc = pynuxrc
        self.replace = replace
        self.logger.info("initialized NuxeoStashRef with path {}".format(self.path))

        self.nx = utils.Nuxeo(rcfile=self.pynuxrc)
        self.uid = self.nx.get_uid(self.path)
        self.source_download_url = self._get_object_download_url()
        self.metadata = self.nx.get_metadata(path=self.path)

        self.tmp_dir = tempfile.mkdtemp(dir='/apps/content/tmp') # FIXME put in conf
        self.source_filename = "sourcefile"
        self.source_filepath = os.path.join(self.tmp_dir, self.source_filename)
        self.magick_tiff_filepath = os.path.join(self.tmp_dir, 'magicked.tif')
        self.uncompressed_tiff_filepath = os.path.join(self.tmp_dir, 'uncompressed.tif')
        self.srgb_tiff_filepath = os.path.join(self.tmp_dir, 'srgb.tiff')
        self.prepped_filepath = os.path.join(self.tmp_dir, 'prepped.tiff')

        name, ext = os.path.splitext(self.source_filename)
        self.jp2_filepath = os.path.join(self.tmp_dir, name + '.jp2')

        self.convert = Convert()
        self.report = {}
        self._update_report('uid', self.uid)
        self._update_report('path', self.path)
        self._update_report('bucket', self.bucket)
        self._update_report('replace', self.replace)
        self._update_report('pynuxrc', self.pynuxrc)
        self._update_report('source_download_url', self.source_download_url)

    def nxstashref(self):

        self.report['converted'] = False
        self.report['stashed'] = False

        # first see if this looks like a valid file to try to convert 
        is_image, image_msg = self._is_image()
        self._update_report('is_image', {'is_image': is_image, 'msg': image_msg})
        self._update_report('precheck', {'pass': False, 'msg': image_msg})
        if not is_image:
            self._remove_tmp()
            return self.report
            
        self.source_mimetype = self._get_object_mimetype()
        passed, precheck_msg = self.convert._pre_check(self.source_mimetype)
        self._update_report('precheck', {'pass': passed, 'msg': precheck_msg})
        if not passed:
            self._remove_tmp()
            return self.report

        has_file, has_file_msg = self._has_file()
        self._update_report('has_file', {'has_file': has_file, 'msg': has_file_msg})
        if not has_file:
            self._remove_tmp()
            return self.report

        self.s3_stashed = self._is_s3_stashed()
        self._update_report('already_s3_stashed', self.s3_stashed)
        if not self.replace and self.s3_stashed:
            return self.report

        # grab the file to convert
        self._download_nuxeo_file()

        # convert to jp2
        converted, jp2_report = self._create_jp2()
        self._update_report('create_jp2', jp2_report) 
        self._update_report('converted', converted)
        if not converted:
            self._remove_tmp()
            return self.report

        # stash in s3
        stashed, s3_report = self._s3_stash()
        self._update_report('s3_stash', s3_report)
        self._update_report('stashed', stashed)
 
        self._remove_tmp()
        return self.report 

    def _has_file(self):
        ''' do a check to see if this nuxeo doc has a content file '''
        try:
            filename = self.metadata['properties']['file:content']['name']
            msg = "File content found."
            return True, msg
        except KeyError:
            msg = "Empty doc (no content name found)."
            return False, msg
        except TypeError:
            msg = "Empty doc (empty content name)."
            return False, msg

    def _is_image(self):
        ''' do a basic check to see if this is an image '''
        # check Nuxeo object type
        try:
            type = self.metadata['type']
        except KeyError:
            msg = "Could not find Nuxeo metadata type for object. Setting nuxeo type to None"
            return False, msg

        if type in ['SampleCustomPicture']:
            msg = "Nuxeo type is {}".format(type)
            return True, msg
        else:
            msg = "Nuxeo type is {}".format(type)
            return False, msg

    def _is_s3_stashed(self):
       """ Check for existence of key on S3.
       """
       key_exists = False

       bucketpath = self.bucket.strip("/")
       bucketbase = self.bucket.split("/")[0]
       s3_url = S3_URL_FORMAT.format(bucketpath, self.uid)
       parts = urlparse.urlsplit(s3_url)

       conn = boto.connect_s3()

       try:
           bucket = conn.get_bucket(bucketbase)
       except boto.exception.S3ResponseError:
           self.logger.info("Bucket does not exist: {}".format(bucketbase))
           return False 
       
       if bucket.get_key(parts.path):
           return True 

    def _update_report(self, key, value):
        ''' add a key/value pair to report dict '''
        self.report[key] = value 

    def _remove_tmp(self):
        ''' clean up after ourselves '''
        shutil.rmtree(self.tmp_dir)

    def _create_jp2(self):
        ''' convert a local image to a jp2
        '''
        report = {} 

        # prep file for conversion to jp2
        if self.source_mimetype in PRECONVERT:
            preconverted, preconvert_msg = self.convert._pre_convert(self.source_filepath, self.magick_tiff_filepath)
            report['pre_convert'] = {'preconverted': preconverted, 'msg': preconvert_msg}

            tiff_to_srgb, tiff_to_srgb_msg = self.convert._tiff_to_srgb_libtiff(self.magick_tiff_filepath, self.prepped_filepath)
            report['tiff_to_srgb'] = {'tiff_to_srgb': tiff_to_srgb, 'msg': tiff_to_srgb_msg}

        elif self.source_mimetype == 'image/tiff':
            uncompressed, uncompress_msg = self.convert._uncompress_tiff(self.source_filepath, self.uncompressed_tiff_filepath)
            report['uncompress_tiff'] = {'uncompressed': uncompressed, 'msg': uncompress_msg}

            tiff_to_srgb, tiff_to_srgb_msg = self.convert._tiff_to_srgb_libtiff(self.uncompressed_tiff_filepath, self.prepped_filepath)
            report['tiff_to_srgb'] = {'tiff_to_srgb': tiff_to_srgb, 'msg': tiff_to_srgb_msg}

        else:
            msg = "Did not know how to prep file with mimetype {} for conversion to jp2.".format(self.source_mimetype)
            self.logger.warning(msg)
            report['status'] = 'unknown mimetype'
            report['msg'] = "Did not know how to prep file with mimetype {} for conversion to jp2.".format(self.source_mimetype)
            return report

        # convert to sRGB
         

        # create jp2
        converted, jp2_msg = self.convert._tiff_to_jp2(self.prepped_filepath, self.jp2_filepath)
        report['convert_tiff_to_jp2'] = {'converted': converted, 'msg': jp2_msg}

        return converted, report

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
        try:
            picture_views = self.metadata['properties']['picture:views']
            for pv in picture_views:
                if pv['tag'] == 'original':
                    mimetype = pv['content']['mime-type']
        except KeyError:
            pass

        return mimetype

    def _s3_stash(self):
       """ Stash file in S3 bucket. 
       """
       report = {}
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
           self.logger.info("Created S3 bucket {}".format(bucketbase))

       if not(bucket.get_key(parts.path)):
           key = bucket.new_key(parts.path)
           key.set_metadata("Content-Type", mimetype)
           key.set_contents_from_filename(self.jp2_filepath)
           msg = "created {0}".format(s3_url)
           action = 'created'
           self.logger.info(msg)
       elif self.replace:
           key = bucket.get_key(parts.path)
           key.set_metadata("Content-Type", mimetype)
           key.set_contents_from_filename(self.jp2_filepath)
           msg = "re-uploaded {}".format(s3_url)
           action = 'replaced'
           self.logger.info(msg)
       else:
           msg = "key already existed; not re-uploading {0}".format(s3_url)
           action = 'skipped'
           self.logger.info(msg)

       report['s3_url'] = s3_url
       report['msg'] = msg
       report['action'] = action 
       report['stashed'] = True

       return True, report


def main(argv=None):
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
