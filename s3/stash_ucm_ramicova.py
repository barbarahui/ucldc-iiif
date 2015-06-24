#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
from pynux import utils
from s3.nxstashref import NuxeoStashRef
import tempfile

class Stasher(NuxeoStashRef):
    def __init__(self, path, bucket, pynuxrc):
         super(Stasher, self).__init__(path, bucket, pynuxrc)

    def _create_jp2(self):

        tmp_dir = tempfile.mkdtemp()

        # convert jpg to tiff
        name, ext = os.path.splitext(self.source_filename)
        tiff_path = os.path.join(tmp_dir, name + '.tiff')
        self.convert._jpg_to_tiff(self.source_filepath, tiff_path)

        # convert tiff to jp2
        self.convert._tiff_to_jp2_no_jp2_space(tiff_path, self.jp2_filepath)

        # clean up
        os.remove(tiff_path)
        os.rmdir(tmp_dir)

def main():
    pynuxrc = "~/.pynuxrc-prod"
    nx = utils.Nuxeo(rcfile=pynuxrc)
    documents = nx.children("asset-library/UCSF/30th_General_Hospital")
    for doc in documents:
        print doc['path']
        stasher = Stasher(doc['path'], 'barbarahui_test_bucket', pynuxrc) 
        stasher.nxstashref()

if __name__ == "__main__":
    sys.exit(main())
