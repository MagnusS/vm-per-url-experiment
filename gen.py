#!/usr/bin/env python

import os

print( "Indexing...")

def make_url(path):
    s = path.replace('_','-').split('/')[::-1]
    return '.'.join(s)

def process(path,files,ip):
    if len(files) == 0:
        return

    url = make_url(path)
    for f in files:
        return {"url": "%s" % url, "path": '%s' % path, "filename" : '%s' % f, "ip" : '%s' % ip}

i = 10
for f in os.walk('www.skjegstad.com'): 
    path, dirs, files = f
    if len(files) > 0:
        print(process(path,files,"192.168.56.%d" % i))
        i = i + 1
