#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os
import argparse
from pynux import utils
import argparse

def main(argv=None):
    parser = argparse.ArgumentParser(description='convert an object to jp2')
    parser.add_argument('path', help="Nuxeo document path")

    utils.get_common_options(parser)
    if argv is None:
        argv = parser.parse_args()

    print argv.path
    nx = utils.Nuxeo(rcfile=argv.rcfile, loglevel=argv.loglevel.upper())    

    # under construction...

if __name__ == "__main__":
    sys.exit(main())
