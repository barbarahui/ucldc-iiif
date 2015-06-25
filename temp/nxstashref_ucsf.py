#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
from pynux import utils
from s3.nxstashref import NuxeoStashRef
import tempfile
import logging

class Stasher(NuxeoStashRef):
    def __init__(self, path, bucket, pynuxrc):
         super(Stasher, self).__init__(path, bucket, pynuxrc)

    def _create_jp2(self):

        tmp_dir = tempfile.mkdtemp()

        # convert file to tiff (right now this tries to convert everything!)
        name, ext = os.path.splitext(self.source_filename)
        tiff_path = os.path.join(tmp_dir, name + '.tiff')
        self.convert._jpg_to_tiff(self.source_filepath, tiff_path)

        # convert tiff to jp2
        self.convert._tiff_to_jp2_no_jp2_space(tiff_path, self.jp2_filepath)

        # clean up
        os.remove(tiff_path)
        os.rmdir(tmp_dir)

def main():
    logging.basicConfig(filename='ucldc-iiif.log', level=logging.INFO, format='%(asctime)s (%(name)s) [%(levelname)s]: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
    logger.info('Started')
    pynuxrc = "~/.pynuxrc-prod"
    nx = utils.Nuxeo(rcfile=pynuxrc)
    documents = nx.children("/asset-library/UCSF/School_of_Dentistry_130")
    for doc in documents:
        stasher = Stasher(doc['path'], 'barbarahui_test_bucket', pynuxrc) 
        stasher.nxstashref()
    logger.info('Finished')

if __name__ == "__main__":
    sys.exit(main())
