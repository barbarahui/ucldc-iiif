# ucldc-iiif

Scripts for working with Loris IIIF server in Amazon Web Services. 

The basic idea is that we convert our images (mostly tiffs) to jp2000 format and stash them on [AWS S3](https://aws.amazon.com/s3/). These images are then served up using an instance of the [Loris IIIF Image Server](https://github.com/loris-imageserver/loris), which we deploy using [AWS Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/).

# Installation

## Clone this repo

Clone this git repo as per usual, e.g.:

    git clone https://github.com/barbarahui/ucldc-iiif.git

## Install system dependencies

Some of these come standard on nix systems, but install if necessary:

1. tiffcp

1. ImageMagick, for its 'convert' command line utility: http://www.imagemagick.org/script/convert.php

1. tiff2rgba

1. tifficc

1. Kakadu's 'kdu_compress' utility, which can be downloaded as part of a bundle of demo apps here: http://kakadusoftware.com/downloads/ (see copyright notice; these binaries can only be used for non-commercial purposes)

## Install python package

    $ cd ucldc-iiif
    $ python setup.py install
    $ mkdir logs
    $ mkdir reports
    

# Create jpeg2000 files and stash on S3

Note: these are very simple placeholder instructions for the UCLDC team, just for now.


Once you've installed this package and its dependencies, you can use the scripts to convert image(s) to jpeg2000 format and stash them on S3, ready for Loris to use. The scripts described below are specific to the UCLDC project. They assume that the images are stored in our Nuxeo instance and so take a Nuxeo path as their input.

    cd ucldc-iiif
    python setup.py s3/stash_collection.py /asset-library/UCM/Ramicova
    
You should get a logfile and a report with useful info on what happened. If all goes well, all of the images for this collection (including component images) will have been converted to jpeg2000 and stashed on S3.
