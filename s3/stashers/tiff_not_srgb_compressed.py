#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from s3.nxstashref import NuxeoStashRef 
import tempfile
import subprocess

class TiffNotSRGBNuxeoStashRef(NuxeoStashRef):

    def __init__(self, path, bucket, pynuxrc):
        super(TiffNotSRGBNuxeoStashRef, self).__init__(path, bucket, pynuxrc)

    def _create_jp2(self):

        ''' this works for UCR Sabino Osuna and UCSC Aerial '''
        # TODO: make sure that this is a convertible image file
        # in https://github.com/DDMAL/diva.js/blob/master/source/processing/process.py ooks like it uses imagemagick to convert other types of image files into tiffs.

        tmp_dir = tempfile.mkdtemp()

        # first need to make sure tiff is uncompressed - demo kdu_compress only deals with uncompressed tiffs
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

def main(argv=None):
    parser = argparse.ArgumentParser(description='Produce jp2 version of Nuxeo image file and stash in S3.')
    parser.add_argument('path', help="Nuxeo document path")
    parser.add_argument('bucket', help="S3 bucket name")
    parser.add_argument('--pynuxrc', default='~./pynuxrc-prod', help="rc file for use by pynux")
    if argv is None:
        argv = parser.parse_args()

    nxstash = TiffNotSRGBNuxeoStashRef(argv.path, argv.bucket, argv.pynuxrc)
    stashed = nxstash.nxstashref()

    print stashed

if __name__ == "__main__":
    sys.exit(main())
