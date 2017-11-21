from flask import Flask, Response
import os
import json
import urllib, urllib.request
import ssl
import codecs

app = Flask(__name__)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ctx.load_verify_locations(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

@app.route('/v1/boot/<mac>')
def mac_article(mac):
    f = open('/var/run/secrets/kubernetes.io/serviceaccount/token')
    token = f.readlines()[0]
    f.close()
    url = "https://%s:%s/apis/kubedhcp.github.com/v1/namespaces/default/dhcps/mac-%s" %(
        os.environ['KUBERNETES_SERVICE_HOST'],
        os.environ['KUBERNETES_SERVICE_PORT_HTTPS'],
        mac.lower().replace(':','-')
    )
    #print("Going to call %s with %s" %(url, token))
    r = urllib.request.Request(url, None, {'Authorization': "Bearer %s" % token})
    req = urllib.request.urlopen(r, context=ctx)
    reader = codecs.getreader("utf-8")
    j = json.load(reader(req))

    data = j['spec']['pxe']
    js = json.dumps(data)

    resp = Response(js, status=200, mimetype='application/json')

    return resp

if __name__ == '__main__':
    app.run()
