#!/usr/bin/env python
import sys
import os
import boto3
import pprint
import re
import tempfile
import shutil

OPERATION_PARAMETERS = {'Bucket': 'ucldc-private-files',
                        'Prefix': 'jp2000/'}
pp = pprint.PrettyPrinter(indent=4)

class FixLegacyJp2(object):

    def __init__(self):

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
            if self.counter >= 3:
                return

    def fix_file(self, id):
        
        # check file header
        #response = self.s3.get_object(Bucket='ucldc-private-files', Key=id)
        #pp.pprint(response)

        # download file
        with open(os.path.join(self.tmp_dir, 'tmp.jp2'), 'wb') as f:
            self.s3.download_fileobj('ucldc-private-files', id, f)

        # convert file
        # convert._uncompress_jp2000(input, output)
        # convert._tiff_to_jp2(input, output)

        # upload file

    def convert_to_tiff(self, input_path, output_path):
        ''' uncompress jp2 using kdu_expand '''
        pass

    def tiff_to_jp2(self, input_path, output_path):
        ''' convert tiff to jp2 using kdu_compress '''
        pass

    def remove_tmp(self):
        ''' clean up after ourselves '''
        shutil.rmtree(self.tmp_dir)

def main():
    fixjp2 = FixLegacyJp2()
    results_iterator = fixjp2.get_results_iterator()

    for page in results_iterator:
        if fixjp2.counter >= 3:
            break 
        print ("Marker: ", page['Marker'])
        fixjp2.process_page(page) 
        print("count: ", fixjp2.counter)

    #fixjp2.remove_tmp()
    
    print("count: ", fixjp2.counter)
 
if __name__ == "__main__":
    sys.exit(main())
