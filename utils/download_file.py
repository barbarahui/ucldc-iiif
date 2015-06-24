#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys, os
import argparse
from pynux import utils
import urlparse
import tempfile
import requests

def main(argv=None):

    parser = argparse.ArgumentParser(description='check for existence of jp2 file on s3 for given nuxeo path')
    parser.add_argument('path', help="Nuxeo document path")

    utils.get_common_options(parser)
    if argv is None:
        argv = parser.parse_args()

    nuxeo_path = argv.path
    
    print "\nnuxeo_path:", nuxeo_path

    # get the Nuxeo ID
    nx = utils.Nuxeo(rcfile=argv.rcfile, loglevel=argv.loglevel.upper())
    nuxeo_id = nx.get_uid(nuxeo_path)
    print "nuxeo_id:", nuxeo_id

    download_url = get_download_url(nuxeo_id, nuxeo_path, nx)
    print download_url, '\n'

    filename = os.path.basename(nuxeo_path)
    filepath = os.path.join(os.getcwd(), filename)
    download_nuxeo_file(download_url, filepath, nx)

    print "\nDone\n"

def download_nuxeo_file(download_url, local_filepath, nx):
    res = requests.get(download_url, auth=nx.auth)
    res.raise_for_status()
    with open(local_filepath, 'wb') as f:
        for block in res.iter_content(1024):
            if block:
                f.write(block)
                f.flush()
    print "Downloaded file to {}".format(local_filepath)

def get_download_url(nuxeo_id, nuxeo_path, nx):
    """ Get object file download URL. We should really put this logic in pynux """
    parts = urlparse.urlsplit(nx.conf["api"])
    filename = nuxeo_path.split('/')[-1]
    url = '{}://{}/Nuxeo/nxbigfile/default/{}/file:content/{}'.format(parts.scheme, parts.netloc, nuxeo_id, filename)

    return url

if __name__ == "__main__":
    sys.exit(main())
