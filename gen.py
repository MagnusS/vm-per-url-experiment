#!/usr/bin/env python

import os
import hashlib
import shutil


def make_url(path,filename):
    filename=filename.split("?")[0] # strip ?...
    s = (filename + "." + path).replace('_','-').split('/')[::-1]
    return '.'.join(s)

def process(path,filename,ip,netmask,gw):
    url = make_url(path,filename)
    return {"url": "%s" % url, 
            "oldurl": "%s" % path,
            "path": '%s' % path, 
            "filename" : '%s' % filename, 
            "ip" : '%s' % ip, 
            "netmask" : netmask, 
            "gw" : gw, 
            "unikernel": hashlib.sha224((url+filename).encode("utf-8")).hexdigest()[0:20]}

def replace_copy(src, dst, replacemap):
    # this function is not very efficient, new copy of string per replace...
    with open(src, "r") as sf:
        data = sf.read()
        for (k,v) in sorted(replacemap.items(), lambda x,y: cmp(-len(x[0]), -len(y[0]))): # replace longest item first
            data = data.replace(k, v)
        with open(dst, "w") as df:
            df.write(data)

def stage_unikernel(meta,urlmap):
    path = "staging/%s" % meta['unikernel']
    print("Preparing unikernel for %s/%s in %s" % (meta['url'], meta['filename'], path))
    try:
        os.makedirs("%s/htdocs" % path)
    except:
        pass

    if meta['filename'] == "index.html":
        replace_copy("%s/%s" % (meta['path'], meta['filename']), "%s/htdocs/%s" % (path, meta['filename']), urlmap)
    else:
        shutil.copy("%s/%s" % (meta['path'], meta['filename']), "%s/htdocs" % path)
    shutil.copy("mirage/dispatch.ml", "%s/dispatch.ml" % path)
    replace_copy("mirage/config.ml", "%s/config.ml" % path, {'%IP%': meta['ip'], '%NETMASK%' : meta['netmask'], '%GATEWAY%' : meta['gw']})

def process_static_webpage_path(rootdir,domain):
    i = 10
    results = []
    urlmap = {}
    for f in os.walk(rootdir): 
        path, dirs, files = f
        if len(files) > 0:
            for x in files:
                result = process(path,x,"192.168.56.%d" % i, "255.255.255.0", "192.168.56.1")

                oldurl = '"http://' + result["oldurl"] + '"'
                urlmap[oldurl] = '"http://' + result["ip"] + '/' + result["filename"] + '"'

                oldurl = '"http://' + result["oldurl"] + '/"'
                urlmap[oldurl] = '"http://' + result["ip"] + '/' + result["filename"] + '"'

                oldurl = oldurl.replace("http://%s" % domain, "")
                if len(oldurl) > 1:
                    urlmap[oldurl] = '"http://' + result["ip"] + '/' + result["filename"] + '"'

                oldurl = '"http://' + result["oldurl"] + '/' + result["filename"] + '"'
                urlmap[oldurl] = '"http://' + result["ip"] + '/' + result["filename"] + '"'

                oldurl = oldurl.replace("http://%s" % domain, "")
                if len(oldurl) > 1:
                    urlmap[oldurl] = '"http://' + result["ip"] + '/' + result["filename"] + '"'

                results.append(result)
                #print(result)
                i = i + 1
                
    #print(sorted(urlmap.items(), lambda x,y: cmp(-len(x[0]), -len(y[0]))))

    for m in results:
        stage_unikernel(m, urlmap)

    return results

def create_makefile(metadata):
    with open("Makefile", "w") as makefile:
        # all
        targets = []
        for r in metadata:
            targets.append("staging/%s/mir-www.xen" % (r['unikernel']))
        makefile.write(".PHONY: all clean run destroy dns\n\n")
        makefile.write("all: serve_dns " + ' '.join(targets) + "\n\n")

        # dns server
        makefile.write("serve_dns: serve_dns.ml\n")
        makefile.write("\tocamlfind ocamlopt serve_dns.ml -o serve_dns -package lwt.unix -package dns -package dns.lwt -linkpkg\n\n")

        # make targets
        for r in metadata:
            makefile.write("staging/%s/mir-www.xen: staging/%s/htdocs/%s\n\tcd staging/%s ; mirage configure --xen\n\tcd staging/%s ; make\n\n" % (r['unikernel'], r['unikernel'], r['filename'], r['unikernel'], r['unikernel'])) 

        # clean
        makefile.write("clean:\n")
        makefile.write("\trm -f serve_dns.cmi serve_dns.cmx serve_dns.o serve_dns\n")
        for r in metadata:
            makefile.write("\tcd staging/%s ; make clean\n" % (r['unikernel'])) 

        # run
        makefile.write("run:\n")
        for r in metadata:
            makefile.write("\tcd staging/%s ; sudo xl create www.xl memory=32 \"vif=['bridge=br0']\" \"name='%s'\"\n" % (r['unikernel'], r['unikernel']))
        makefile.write("\tsudo xl list\n")

        # destroy
        makefile.write("destroy:\n")
        for r in metadata:
            makefile.write("\tsudo xl destroy %s || true\n" % r['unikernel'])
        makefile.write("\tsudo xl list\n")

        #dns
        makefile.write("dns: serve_dns\n")
        makefile.write("\tsudo ./serve_dns\n")

def create_zone(zonefile, domain, meta):
    with open(zonefile, "w") as z:
        z.write ("@   IN  SOA     ns.%s.  postmaster.%s. (1 600 600 600 60)\n" % (domain, domain))
        z.write ("%s.\tIN\tCNAME\tindex.html.%s.\n" % (domain, domain))
        for r in meta:
            z.write ('%s\tIN\tA\t%s\n' % (r['url'], r['ip']))

domain = 'www.skjegstad.com'
print( "Indexing %s..." % domain)
meta = process_static_webpage_path(domain, domain)
create_makefile(meta)
print("\nMakefile generated. Type 'make' to build, 'make run' to run and 'make destroy' to stop. Start DNS server with 'make dns'")
create_zone("%s.zone" % domain, domain, meta)
print("\nZone file generated in %s.zone." % domain)


