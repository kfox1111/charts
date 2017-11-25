from flask import Flask, Response
import os
import json
import urllib, urllib.error, urllib.request
import ssl
import codecs
import collections
import jsonpatch
import jsonpointer

app = Flask(__name__)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
#FIXME This should be made a config file option...
#ctx.load_verify_locations(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

#FIXME make this a configfile thing.
engineConfig = {
    'configStore': {
        'url': "http://kube-config-store"
    }
}

def union(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = union(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def tags_match(requested_tag, specified_tags):
    if isinstance(specified_tags, str):
        if specified_tags == 'default' or specified_tags == requested_tag:
            return True
    else:
        if requested_tag in specified_tags:
            return True
    return False


def get_cs_data(group, name):
    url = "%s/v1/%s/%s" % (engineConfig['configStore']['url'], group, name)
    print("Going to call %s" %(url))
    r = urllib.request.Request(url)
    req = urllib.request.urlopen(r)
    reader = codecs.getreader("utf-8")
    data = json.load(reader(req))
    return data

def get_ce_doc(data, requested_tag, kind, name):
    doc_data = get_cs_data(kind, name)
    for t in doc_data['config']:
        if tags_match(requested_tag, t['tags']):
           for op in t['ops']:
               dst_data = data
               dst_path = ""
               if 'dstPath' in op:
                   dst_path = op['dstPath']
               if dst_path and dst_path != "":
                   dst_data = jsonpointer.resolve_pointer(data, dst_path) 
               if 'include' in op:
                   #FIXME if we want to support srcSath, here's where to do it.
                   key = list(op['include'].keys())[0]
                   dst_data = get_ce_doc(dst_data, requested_tag, key, op['include'][key])
               elif 'set' in op:
                   #FIXME we can implement op['merger'] = overwrite (current, default), keep, failifset, arrayzipper, etc.
                   union(dst_data, op['set'])
               elif 'jsonPatch' in op:
                   patch = jsonpatch.JsonPatch.from_string(json.dumps(op['jsonPatch']))
                   dst_data = patch.apply(dst_data)
               if dst_path and dst_path != "":
                   jsonpointer.set_pointer(data, dst_path, dst_data)
               else:
                   data = dst_data
    return data

@app.route('/v1/<tags>/<kind>/<name>')
def get_ce(tags, kind, name):
    data = {}
    data = get_ce_doc(data, tags, kind, name)

    js = json.dumps(data)

    resp = Response(js, status=200, mimetype='application/json')

    return resp

if __name__ == '__main__':
    app.run()
