from flask import Flask, Response
import os
import json
import urllib, urllib.error, urllib.request
import ssl
import codecs
import collections
import jsonpatch

app = Flask(__name__)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
#FIXME This should be made a config file option...
#ctx.load_verify_locations(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

def union(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = union(d.get(k, {}), v)
        else:
            d[k] = v
    return d

#FIXME make this a configfile thing.
engineConfig = {
    'configStore': {
        'url': "http://kube-config-store"
    }
}

def get_cs_data(group, name):
    url = "%s/v1/%s/%s" % (engineConfig['configStore']['url'], group, name)
    print("Going to call %s" %(url))
    r = urllib.request.Request(url)
    req = urllib.request.urlopen(r)
    reader = codecs.getreader("utf-8")
    data = json.load(reader(req))
    return data

def engine_match(enginekind, name):
    if isinstance(name, str):
        if name == 'default' or name == enginekind:
            return True
    else:
        if enginekind in name:
            return True
    return False

def process_doc(data_list, data, kind):
    data_list.insert(0, data)
    # Walk default and kind entries (dhcps). get all includes and pull each document.
    for t in data['config']:
        if engine_match(kind, t['name']):
           if 'include' in t:
               for g in t['include']:
                   d = get_cs_data(g['name'], g['value'])
                   process_doc(data_list, d, kind)

def process_union_data(built_data, data, kind):
    for t in data['config']:
        if engine_match(kind, t['name']):
           if 'set' in t:
               #FIXME we can implement t['set']['merger'] = overwrite (current), failifset, arrayzipper, etc.
               union(built_data, t['set']['data'])
           if 'jsonPatch' in t:
               patch = jsonpatch.JsonPatch.from_string(json.dumps(t['jsonPatch']))
               built_data = patch.apply(built_data)
    return built_data

@app.route('/v1/<enginekind>/<kind>/<name>')
def get_ce(enginekind, kind, name):

    data = get_cs_data(kind, name)

    data_list = []

    # Include all include data in the list.
    process_doc(data_list, data, enginekind)

    built_data = {}
    # Walk all the downloaded lists and find all the enginekind entries
    for d in data_list:
        built_data = process_union_data(built_data, d, 'default')
        built_data = process_union_data(built_data, d, enginekind)

    js = json.dumps(built_data)

    resp = Response(js, status=200, mimetype='application/json')

    return resp

if __name__ == '__main__':
    app.run()
