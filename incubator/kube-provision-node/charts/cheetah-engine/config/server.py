from flask import Flask, Response
import os
import json
import urllib, urllib.error, urllib.request
import ssl
import codecs
import collections
import Cheetah.Template

app = Flask(__name__)

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
#FIXME This should be made a config file option...
#ctx.load_verify_locations(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

@app.route('/v1/<template>')
def get_template(template):
#FIXME unhardcode this url.
    url = "http://config-engine/v1/template/machine/%s" % template
    print("Going to call %s" %(url))
    r = urllib.request.Request(url)
    req = urllib.request.urlopen(r)
    reader = codecs.getreader("utf-8")
    data = json.load(reader(req))
#FIXME render data['snippets'] into templates.

    nameSpace = {
        "packages": [],
        "template": """
#for $command in $commands
#set str = ""
#set $v = $commands[$command]
#if "args" in $v
#set $args = $v["args"]
#for $arg in $args
#if $args[$arg] is None
#set str += " --" + $arg
#else
#set str += " --" + $arg + "=" + $args[$arg]
#end if
#end for
#end if
#if "opts" in $v
#set $opts = $v["opts"]
#for $opt in $opts
#set str += " " + $opt
#end for
#end if
$command$str
#end for

%pre
set -x
$snippets.pre
%end

%packages --nobase
#for $package in $packages
$package
#end for
%end

%post
set -x
$snippets.post
%end
""",
        "snippets": {
            "pre": "",
            "post": ""
        },
        "commands": {
            "url": {"args": {"url": "http://centos-7-1708-x86-64.coreprovision.cluster.local/"}},
            "rootpw": {"args": {"iscrypted": "default_password_crypted"}},
            ##FIXME need repo list...
            "auth": {"args": {"useshadow": None, "enablemd5": None}},
            "bootloader": {"args": {"location": "mbr"}},
            "clearpart": {"args": {"all": None, "initlabel": None}},
            "text": {},
            "firewall": {"args": {"enabled": None}},
            "firstboot": {"args": {"disable": None}},
            "keyboard": {"opts": ["us"]},
            "lang": {"opts": ["en_US"]},
            "reboot": {},
            "eula": {"args": {"agreed": None}},
            "services": {"args": {"enabled":"sshd"}},
            "selinux": {"args": {"disabled": None}},
        }
    }
    t = Cheetah.Template.Template(data['template'], searchList=[data])

    resp = Response(str(t), status=200, mimetype='text/plain')

    return resp

if __name__ == '__main__':
    app.run()
