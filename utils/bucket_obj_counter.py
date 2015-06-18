#!/usr/bin/env python
import boto

#boto.set_stream_logger('boto')
s3 = boto.connect_s3()
s3bucket = s3.get_bucket('ucldc-nuxeo-ref-images')

size = 0
totalCount = 0

for key in s3bucket.list():
    totalCount += 1
    size += key.size

print 'total size:'
print "%.3f GB" % (size*1.0/1024/1024/1024)
print 'total count:'
print totalCount
