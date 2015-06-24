#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
import subprocess
import logging
import ConfigParser

class Convert(object):

    ''' 
        utilities for converting images to jp2 
        see https://github.com/DDMAL/diva.js/blob/master/source/processing/process.py
    '''

    def __init__(self):
        
        self.logger = logging.getLogger(__name__)

        self.tiffcp_location = '/apps/nuxeo/pkg/bin/tiffcp'
        self.magick_convert_location = '/apps/nuxeo/pkg/bin/convert'
        self.kdu_compress_location = '/apps/nuxeo/kakadu/kdu_compress'

    def _uncompress_tiff(self, compressed_path, uncompressed_path):
        ''' uncompress a tiff '''
        # use tiffcp to uncompress: http://www.libtiff.org/tools.html
        # tiffinfo ucm_dr_001_001_a.tif # gives you info on whether or not this tiff is compressed
        # FIXME make sure tiffcp is installed - add to required packages
        subprocess.call([self.tiffcp_location,
            "-c", "none",
            compressed_path,
            uncompressed_path])
        self.logger.info('File uncompressed. Input: {}, output: {}'.format(compressed_path, uncompressed_path))

    def _tiff_to_jp2(self, tiff_path, jp2_path):
        ''' convert an uncompressed tiff to jp2 using kdu_compress'''
        # Settings recommended as a starting point by Jon Stroop. See https://groups.google.com/forum/?hl=en#!searchin/iiif-discuss/kdu_compress/iiif-discuss/OFzWFLaWVsE/wF2HaykHcd0J
        subprocess.call([self.kdu_compress_location,
                             "-i", tiff_path,
                             "-o", jp2_path,
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
        
        self.logger.info('{} converted to {}'.format(tiff_path, jp2_path))

    def _tiff_to_jp2_no_jp2_space(self, tiff_path, jp2_path):
        ''' convert an uncompressed tiff to jp2 using kdu_compress'''
        # Settings recommended as a starting point by Jon Stroop. See https://groups.google.com/forum/?hl=en#!searchin/iiif-discuss/kdu_compress/iiif-discuss/OFzWFLaWVsE/wF2HaykHcd0J
        subprocess.call([self.kdu_compress_location,
                             "-i", tiff_path,
                             "-o", jp2_path,
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
        self.logger.info('{} converted to {}'.format(tiff_path, jp2_path))

    def _jpx_to_jp2(self):
        ''' convert jpx to jp2 '''
        pass

    def _jpg_to_tiff(self, input_path, output_path):
        ''' convert jpg to jp2 '''
        subprocess.call([self.magick_convert_location,
                         "-compress", "None",
                         input_path,
                         output_path])
        self.logger.info('{} converted to {}'.format(input_path, output_path))
        
    def _gif_to_jp2(self):
        ''' convert gif to jp2 '''
        pass

def main(argv=None):
    pass
 
if __name__ == "__main__":
    sys.exit(main())
