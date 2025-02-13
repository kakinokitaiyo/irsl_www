#!/bin/bash

##
echo "serverName simserver.irsl.eiiris.tut.ac.jp" > /etc/apache2/conf-available/fqdn.conf

##
/usr/sbin/a2enconf fqdn && \
/usr/sbin/a2ensite 000-default && \
/usr/sbin/a2ensite default-ssl && \
/usr/sbin/a2enmod ssl && \
/usr/sbin/a2enmod authnz_ldap && \
/usr/sbin/a2enmod rewrite

##
apachectl -D FOREGROUND
