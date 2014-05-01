#!/bin/sh
#
# UPDATE DJANGO FROM REPO

rm -rf /var/django/*
cp -rf /vagrant/conf/django/* /var/django/