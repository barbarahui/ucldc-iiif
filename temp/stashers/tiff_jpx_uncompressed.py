#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef 
import tempfile
import subprocess

class TiffJpxNuxeoStashRef(NuxeoStashRef):

    def __init__(self, path, bucket, pynuxrc):
        super(TiffJpxNuxeoStashRef, self).__init__(path, bucket, pynuxrc)

        name, ext = os.path.splitext(self.source_filename)
        self.jpx_filepath = os.path.join(self.tmp_dir, name + '.jpx')

    def _remove_tmp(self):
        ''' clean up after ourselves '''
        os.remove(self.source_filepath)
        os.remove(self.jp2_filepath)
        os.remove(self.jpx_filepath)
        os.rmdir(self.tmp_dir)
        
    def _create_jp2(self):

        ''' trying this for tiffs that kdu_compress says it can only convert to jpx
            NOTE: this creates a jp2 for /asset-library/UCI/Cochems/MS-R016_0943.tif barbarahui_test_bucket
            However, Loris complains that the image cannot be displayed because it contains errors 
        '''

        # create jpx using Kakadu
        # Settings recommended as a starting point by Jon Stroop. See https://groups.google.com/forum/?hl=en#!searchin/iiif-discuss/kdu_compress/iiif-discuss/OFzWFLaWVsE/wF2HaykHcd0J
        kdu_compress_location = '/apps/nuxeo/kakadu/kdu_compress' # FIXME add config
        subprocess.call([kdu_compress_location,
                             "-i", self.source_filepath,
                             "-o", self.jpx_filepath,
                             "-quiet",
                             "-rate", "2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,.08266171",
                             "Creversible=yes",
                             "Clevels=7",
                             "Cblk={64,64}",
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


        # create jp2 using imagemagick
        '''
        magick_location = '/apps/nuxeo/pkg/bin/convert'
        magick_args = [magick_location, self.jpx_filepath, self.jp2_filepath]
        print "magick_args:", magick_args
        subprocess.call([magick_location, self.source_filepath, self.jp2_filepath])
        '''

        return self.jp2_filepath

def main(argv=None):
    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('pynuxrc', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    nxstash = TiffJpxNuxeoStashRef(argv.path, argv.bucket, argv.pynuxrc)
    stashed = nxstash.nxstashref()

    print stashed

if __name__ == "__main__":
    sys.exit(main())
