# set up in beanstalk

1. In IAM, create a new empty EC2 role.  `iiifLoris` is IAM role that
will have access to read S3 buckets with jpeg2000s.

2. upload .zip 

3. in Elastic Beanstalk, Create New Application `ucldc-iiif-west`; use
`iiifLoris` role, and the .zip from above.  Use `ucldc_image_server` VPC 
security group.
