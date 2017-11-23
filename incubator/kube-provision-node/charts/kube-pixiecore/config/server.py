from flask import Flask, Response
import os
import json
import urllib, urllib.error, urllib.request
import ssl
import codecs

app = Flask(__name__)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
#FIXME Make this configurable.
#ctx.load_verify_locations(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

@app.route('/v1/boot/<mac>')
def get_boot(mac):
#FIXME make this configurable and add v1
    url = "http://config-engine/v1/pxe/dhcp/%s" % mac
    print("Going to call %s" %(url))
    r = urllib.request.Request(url)
    req = urllib.request.urlopen(r)
    reader = codecs.getreader("utf-8")
    data = json.load(reader(req))
    if 'cmdline' in data:
        cmdline = data['cmdline']
        l = []
        for i in cmdline:
            if isinstance(i, str):
                l.append(i)
            else:
                for j in i:
                    print(j, i[j])
                    if i[j].find(' ') != -1:
                        # FIXME can you escape "'s?
                        l.append("%s=\"%s\"" %(j, i[j]))
                    else:
                        l.append("%s=%s" %(j, i[j]))
        data['cmdline'] = ' '.join(l)

    js = json.dumps(data)

    resp = Response(js, status=200, mimetype='application/json')

    return resp

if __name__ == '__main__':
    app.run()
