FROM ubuntu:14.04

MAINTAINER Barbara Hui <barbara.hui@ucop.edu>

RUN apt-get update && apt-get install -y \
    apache2 \
    git \
    libapache2-mod-wsgi \
    libfreetype6 \
    libfreetype6-dev \
    libjpeg-turbo8 \ 
    libjpeg-turbo8-dev \
    liblcms2-2 \
    liblcms2-dev \
    liblcms-utils \
    libtiff5-dev \
    libwebp-dev \
    python-dev \
    python-pip \
    python-setuptools \
    zlib1g-dev 
    
RUN pip install \
    boto \
    configobj \
    mock \
    Pillow \
    requests \
    responses \
    werkzeug

# have to do this to get rid of "ImportError: No module named _winreg" error for six.py
RUN pip install --upgrade six

# install Loris
WORKDIR /opt
RUN git clone https://github.com/barbarahui/loris.git
WORKDIR /opt/loris
RUN git checkout ucldc 
RUN useradd -d /var/www/loris2 -s /sbin/false loris

# make image directories
RUN mkdir /usr/local/share/images
RUN mkdir /usr/local/share/images/loris
RUN chown loris:loris /usr/local/share/images
RUN chown loris:loris /usr/local/share/images/loris

# loris/setup.py should be doing this - not sure why it's broken
RUN cp bin/Linux/x86_64/kdu_expand /usr/local/bin/ 
RUN cp lib/Linux/x86_64/libkdu_v74R.so /usr/lib/

RUN python /opt/loris/setup.py install

# set up apache
RUN a2enmod headers expires
COPY apache-config.txt /etc/apache2/sites-enabled/000-default.conf

# cache maintenance - need to set up a cron job

EXPOSE 80 

CMD ["/usr/sbin/apachectl", "-D", "FOREGROUND"]
