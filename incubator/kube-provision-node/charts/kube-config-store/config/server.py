from flask import Flask, Response
import os
import json
import yaml
import urllib, urllib.error, urllib.request
import ssl
import codecs

app = Flask(__name__)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ctx.load_verify_locations(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

kindMap = yaml.load(open('/etc/config-store.yaml'))

def get_kind_req(kind, name=""):
    f = open('/var/run/secrets/kubernetes.io/serviceaccount/token')
    token = f.readlines()[0]
    f.close()
    prefix = ""
    newname = name
    if name == "":
        newname = kindMap[kind]['fallback']
    else:
        if "namePrefix" in kindMap[kind]:
            prefix = "%s-" % kindMap[kind]["namePrefix"]
        if "nameManip" in kindMap[kind]:
            for x in kindMap[kind]["nameManip"]:
                if isinstance(x, str):
                   if x == "lower":
                       newname = newname.lower()
                   else:
                       raise Exception("unknown name manip function %s" % x)
                else:
                   if x['func'] == "replace":
                       newname = newname.replace(x["in"], x["out"])
                   else:
                       raise Exception("unknown name manip function %s" % x['func'])
      
    url = "https://%s:%s/apis/%s/%s/namespaces/%s/%s/%s%s" %(
        os.environ['KUBERNETES_SERVICE_HOST'],
        os.environ['KUBERNETES_SERVICE_PORT_HTTPS'],
        kindMap[kind]["api"],
        kindMap[kind]["version"],
        kindMap[kind]["namespace"],
        kindMap[kind]["kind"],
        prefix,
        newname
    )
    print("Going to call %s" %(url))
    r = urllib.request.Request(url, None, {'Authorization': "Bearer %s" % token})
    req = urllib.request.urlopen(r, context=ctx)
    return req

@app.route('/v1/<kind>/<name>')
def get_article(kind, name):
    try:
        req = get_kind_req(kind, name)
    except urllib.error.HTTPError as e:
        if e.code != 404 and kind not in kindMap:
            raise
        req = get_kind_req(kind)
    reader = codecs.getreader("utf-8")
    j = json.load(reader(req))

    data = j['spec']

    js = json.dumps(data)

    resp = Response(js, status=200, mimetype='application/json')

    return resp

if __name__ == '__main__':
    app.run()
