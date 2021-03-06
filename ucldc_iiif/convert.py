#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import logging

VALID_TYPES = ['image/jpeg', 'image/gif', 'image/tiff', 'image/png', 'image/jp2', 'image/jpx', 'image/jpm']
INVALID_TYPES = ['application/pdf']

# Settings recommended as a starting point by Jon Stroop.
# See https://groups.google.com/forum/?hl=en#!searchin/iiif-discuss/kdu_compress/iiif-discuss/OFzWFLaWVsE/wF2HaykHcd0J
KDU_COMPRESS_BASE_OPTS = [
    "-quiet", "-rate",
    "2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,"
    ".08266171",
    "Creversible=yes", "Clevels=7", "Cblk={64,64}", "Cuse_sop=yes",
    "Cuse_eph=yes", "Corder=RLCP", "ORGgen_plt=yes", "ORGtparts=R",
    "Stiles={1024,1024}", "-double_buffering", "10", "-num_threads", "4",
    "-no_weights"
]

KDU_COMPRESS_DEFAULT_OPTS = KDU_COMPRESS_BASE_OPTS[:]
KDU_COMPRESS_DEFAULT_OPTS.extend(["-jp2_space", "sRGB"])


class Convert(object):
    '''
        utilities for use in converting an image file to jp2 format
    '''

    def __init__(self):

        self.logger = logging.getLogger(__name__)

        self.tiffcp_location = os.environ.get('PATH_TIFFCP',
                                              '/usr/local/bin/tiffcp')
        self.magick_convert_location = os.environ.get('PATH_MAGICK_CONVERT',
                                                      '/usr/local/bin/convert')
        self.kdu_compress_location = os.environ.get(
            'PATH_KDU_COMPRESS', '/usr/local/bin/kdu_compress')
        self.tiff2rgba_location = os.environ.get('PATH_TIFF2RGBA',
                                                 '/usr/local/bin/tiff2rgba')
        self.tifficc_location = os.environ.get('PATH_TIFFICC',
                                               '/usr/local/bin/tifficc')
        self.kdu_expand_location = os.environ.get('PATH_KDU_EXPAND',
                                               '/usr/local/bin/kdu_expand')

    def _pre_check(self, mimetype):
        ''' do a basic pre-check on the object to see if we think it's
        something know how to deal with '''
        # see if we recognize this mime type
        if mimetype in VALID_TYPES:
            passed = True
            msg = "Mime-type '{}' was pre-checked and recognized as " \
                  "something we can try to convert.".format(mimetype)
            self.logger.info(msg)
        elif mimetype in INVALID_TYPES:
            passed = False
            msg = "Mime-type '{}' was pre-checked and recognized as " \
                  "something we don't want to convert.".format(mimetype)
            self.logger.info(msg)
        else:
            passed = False
            msg = "Mime-type '{}' was unrecognized. We don't know how to " \
                  "deal with this".format(mimetype)
            self.logger.warning(msg)

        return passed, msg

    def _uncompress_tiff(self, compressed_path, uncompressed_path):
        ''' uncompress a tiff using tiffcp.
        See http://www.libtiff.org/tools.html '''
        try:
            subprocess.check_output(
                [
                    self.tiffcp_location, "-c", "none", compressed_path,
                    uncompressed_path
                ],
                stderr=subprocess.STDOUT)
            uncompressed = True
            msg = 'File uncompressed. Input: {}, output: {}'.format(
                compressed_path, uncompressed_path)
            self.logger.info(msg)
        except subprocess.CalledProcessError, e:
            uncompressed = False
            msg = '`tiffcp` command failed: {}\nreturncode was: {}\n' \
                  'output was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

        return uncompressed, msg

    def _uncompress_jp2000(self, compressed_path, uncompressed_path):
        ''' uncompress a jp2000 file using kdu_expand '''
        try:
            subprocess.check_output(
                [
                    self.kdu_expand_location, "-i", compressed_path, "-o", uncompressed_path
                ],
                stderr=subprocess.STDOUT)
            uncompressed = True
            msg = 'File uncompressed using kdu_expand. Input: {}, output: {}'.format(
                compressed_path, uncompressed_path)
            self.logger.info(msg)
        except subprocess.CalledProcessError, e:
            uncompressed = False
            msg = '`kdu_expand` command failed: {}\nreturncode was: {}\n' \
                  'output was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

        return uncompressed, msg

    def _tiff_to_jp2(self, tiff_path, jp2_path):
        ''' convert a tiff to jp2 using kdu_compress.
        tiff must be uncompressed.'''
        basic_args = [
            self.kdu_compress_location, "-i", tiff_path, "-o", jp2_path
        ]
        default_args = basic_args[:]
        default_args.extend(KDU_COMPRESS_DEFAULT_OPTS)
        alt_args = basic_args[:]
        alt_args.extend(KDU_COMPRESS_BASE_OPTS)

        try:
            subprocess.check_output(
                default_args, stderr=subprocess.STDOUT)
            converted = True
            msg = '{} converted to {}'.format(tiff_path, jp2_path)
            self.logger.info(msg)
        except subprocess.CalledProcessError, e:
            self.logger.info(
                'A kdu_compress command failed. Trying alternate.')
            try:
                subprocess.check_output(
                    alt_args, stderr=subprocess.STDOUT)
                converted = True
                msg = '{} converted to {}'.format(tiff_path, jp2_path)
                self.logger.info(msg)
            except subprocess.CalledProcessError, e:
                converted = False
                msg = 'kdu_compress command failed: {}\nreturncode was: {}\n' \
                      'output was: {}'.format(e.cmd, e.returncode, e.output)
                self.logger.error(msg)

        return converted, msg

    def _pre_convert(self, input_path, output_path):
        '''
         convert file using ImageMagick `convert`:
         http://www.imagemagick.org/script/convert.php
        '''
        try:
            subprocess.check_output(
                [
                    self.magick_convert_location, "-compress", "None",
                    "-quality", "100", "-auto-orient", input_path, output_path
                ],
                stderr=subprocess.STDOUT)
            preconverted = True
            msg = 'Used ImagMagick convert to convert {} to {}'.format(
                input_path, output_path)
            self.logger.info(msg)
        except subprocess.CalledProcessError, e:
            preconverted = False
            msg = 'ImageMagic `convert` command failed: {}\nreturncode was:' \
                  '{}\noutput was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

        return preconverted, msg

    def _tiff_to_srgb_libtiff(self, input_path, output_path):
        '''
        convert color profile to sRGB using libtiff's `tiff2rgba` tool
        '''
        try:
            subprocess.check_output([
                self.tiff2rgba_location, "-c", "none", input_path, output_path
            ],
                stderr=subprocess.STDOUT)
            to_srgb = True
            msg = "Used tiff2rgba to convert {} to {}, with color profile" \
                  "sRGB (if not already sRGB)".format(input_path, output_path)
            self.logger.info(msg)
        except subprocess.CalledProcessError, e:
            to_srgb = False
            msg = 'libtiff `tiff2rgba` command failed: {}\nreturncode was:' \
                  '{}\noutput was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

        return to_srgb, msg

    def _tiff_to_srgb_little_cms(self, input_path, output_path):
        '''
        convert color profile to sRGB using Little CMS's `tifficc`
        ICC profile applier tool.
        '''
        try:
            subprocess.check_output(
                [self.tifficc_location, input_path, output_path],
                stderr=subprocess.STDOUT)
            to_srgb = True
            msg = "Used tifficc to convert {} to {}, with color profile " \
                  "sRGB (if not already sRGB)".format(input_path, output_path)
            self.logger.info(msg)
        except subprocess.CalledProcessError, e:
            to_srgb = False
            msg = 'Little CMS `tifficc` command failed: {}\nreturncode was:' \
                  '{}\noutput was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

        return to_srgb, msg


def main(argv=None):
    pass


if __name__ == "__main__":
    sys.exit(main())
