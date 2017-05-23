#!/usr/bin/env python
import sys
import os
import boto3
import re
import tempfile
import shutil
import subprocess
import logging
import argparse 

OPERATION_PARAMETERS = {'Bucket': 'ucldc-private-files',
                        'Prefix': 'jp2000/'}

class FixLegacyJp2(object):

    def __init__(self):

        self.logger = logging.getLogger(__name__)
        self.s3 = boto3.client('s3')
        self.paginator = self.s3.get_paginator('list_objects')
        self.counter = 0
        self.tmp_dir = tempfile.mkdtemp(dir='/tmp')

    def get_results_iterator(self, start_token=None):
        
        # I can't get the paginator to return 'NextToken' or 'NextMarker', no matter what I try,
        # so I'm not using `MaxItems` argument for now
        PaginationConfig={}
        if start_token:
            PaginationConfig['StartingToken']: start_token
         
        return self.paginator.paginate(**OPERATION_PARAMETERS, PaginationConfig=PaginationConfig)

    def process_page(self, page):
    
        for object in page['Contents']:
            # they all have the pattern `NNNNN-arkstuff-zN.jp2` — most of them starting `13030-`
            # the `z` number is the index number into complex object
            id = object['Key']
            if re.search(r'^jp2000/\d{5}-.*-z\d+\.jp2$', id):
                self.counter = self.counter + 1
                self.fix_file(id)

    def fix_file(self, id):
        
        original_filepath = os.path.join(self.tmp_dir, 'orig.jp2') 
        uncompressed_filepath = os.path.join(self.tmp_dir, 'uncompressed.tiff') 
        new_filepath = os.path.join(self.tmp_dir, 'new.jp2') 

        # check file header
        #response = self.s3.get_object(Bucket='ucldc-private-files', Key=id)
        #pp.pprint(response)

        # download file
        with open(original_filepath, 'wb') as f:
            self.s3.download_fileobj('ucldc-private-files', id, f)
        self.logger.info("Downloaded {}".format(id))

        # convert file
        self.uncompress_jp2000(original_filepath, uncompressed_filepath)
        self.tiff_to_jp2(uncompressed_filepath, new_filepath)
        self.logger.info("Converted {}".format(id))

        # upload file
        with open(new_filepath, 'rb') as f:
            self.s3.upload_fileobj(f, 'ucldc-private-files', id)
        self.logger.info("Restashed {}".format(id))

    def uncompress_jp2000(self, input_path, output_path):
        ''' uncompress jp2 using kdu_expand '''
        try:
            subprocess.check_output(
                [
                    '/usr/local/bin/kdu_expand', "-i", input_path, "-o", output_path
                ],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            msg = '`kdu_expand` command failed: {}\nreturncode was: {}\n' \
                  'output was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

    def tiff_to_jp2(self, input_path, output_path):
        ''' convert tiff to jp2 using kdu_compress '''

        try:
            subprocess.check_output(
                [
                    "/usr/local/bin/kdu_compress", "-i", input_path, "-o", output_path,
                    "-quiet", "-rate",
                    "2.4,1.48331273,.91673033,.56657224,.35016049,.21641118,.13374944,"
                    ".08266171",
                    "Creversible=yes", "Clevels=7", "Cblk={64,64}", "Cuse_sop=yes",
                    "Cuse_eph=yes", "Corder=RLCP", "ORGgen_plt=yes", "ORGtparts=R",
                    "Stiles={1024,1024}", "-double_buffering", "10", "-num_threads", "4",
                    "-no_weights"
                ],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            msg = 'kdu_compress command failed: {}\nreturncode was: {}\n' \
                  'output was: {}'.format(e.cmd, e.returncode, e.output)
            self.logger.error(msg)

    def remove_tmp(self):
        ''' clean up after ourselves '''
        shutil.rmtree(self.tmp_dir)

def main(marker, loglevel):

    logfile = 'logs/convert_legacy_oac_jp2s'
    numeric_level = getattr(logging, loglevel, None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(
        filename=logfile,
        level=numeric_level,
        format='%(asctime)s (%(name)s) [%(levelname)s]: %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)

    print('Starting at marker: ', marker)
    print('logfile: ', logfile)

    fixjp2 = FixLegacyJp2()
    results_iterator = fixjp2.get_results_iterator()

    for page in results_iterator:
        logger.info("Marker: {}".format(page['Marker']))
        fixjp2.process_page(page) 
        logger.info("page legacy jp2 count: {}".format(fixjp2.counter))

    fixjp2.remove_tmp()
    
    logger.info("total legacy jp2 count: {}".format(fixjp2.counter))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Fix legacy jp2000s so they work with potto-loris')
    parser.add_argument('--marker', default=None)
    parser.add_argument('--loglevel', default='INFO')

    argv = parser.parse_args()

    marker = argv.marker
    loglevel = argv.loglevel

    sys.exit(main(marker=marker, loglevel=loglevel))
