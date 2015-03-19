# set up in beanstalk

1. In IAM, create a new empty EC2 role.  `iiifLoris` is IAM role that
will have access to read S3 buckets with jpeg2000s.

2. upload .zip 

3. in Elastic Beanstalk, Create New Application `ucldc-iiif-west`; use
`iiifLoris` role, and the .zip from above.  Use `ucldc_image_server` VPC 
security group.



## Docker one-liners

tag your builds
```
docker build -t tag .
```

spin up to get a shell in the container
```
docker run --rm -e "AWS_ACCESS_KEY=$A1" -e "AWS_SECRET_KEY=$A2" -t -i tag /bin/bash
```

run a container in background, mapping some ports and a host directory.  (_If you are using Boot2Docker, your Docker daemon only has limited access to your OSX/Windows filesystem._)  `Dockerfile` most `EXPOSE` port on container.  host:container for `-p` and `-v`.
```
docker run -e "A=$a" -d -p 8888:8888 -v /Users/user/dir:/home --name container -t tag
```

In `Dockerfile` use `CMD` over `ENTRYPOINT` for more flexibility.
