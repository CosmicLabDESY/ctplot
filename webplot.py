#!/opt/bin/python
# -*- coding: utf-8 -*-
#    pyplot - python based data plotting tools
#    created for DESY Zeuthen
#    Copyright (C) 2012  Adam Lucke  software@louisenhof2.de
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import matplotlib
matplotlib.use('Agg')

import json, os, cgitb, cgi, sys, subprocess, time, random, string
from plot import Plot, available_tables
from utils import hashargs, getCpuLoad, getRunning
from datetime import datetime
from config import *

cgitb.enable(context = 1, format = 'html')




def make_plot(settings):
    name = os.path.join(plotdir, 'plot{}'.format(hashargs(settings))).replace('\\', '/')

    # wait until there is free capacity
    for i in xrange(1000):
        # try to get plot from cache
        if usecache and os.path.isfile(name + '.png'):
            return dict([(e, name + '.' + e) for e in ['png', 'svg', 'pdf']])
        time.sleep(random.random())
        # if getCpuLoad() < .8: break # cpu usage <80%
        if getRunning('webplot') <= 2: break  # max 3 processes


    # lower priority and create the plot
    if os.name == 'posix':
        os.nice(5)

    p = Plot(**settings)
    return p.save(name)


contenttypes = {'png': 'image/png'  , 'svg': 'image/svg+xml'  , 'pdf':'application/pdf'   }


def countInstances(process):
    if os.name == 'nt':
        ps = ['tasklist']
    elif os.name == 'psix':
        ps = ['ps', '-fe']
    else:
        raise RuntimeError('no tasklist command for {} defined'.format(os.name))
    p = subprocess.Popen(ps, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    count = 0
    for line in p.stdout:
        if process in line:
            print line.strip()
            count += 1
    return count

_chars = string.ascii_letters + string.digits

def randomChars(n):
    return ''.join(random.choice(_chars) for i in xrange(n))


if __name__ == '__main__':
    fields = cgi.FieldStorage()
    action = fields.getfirst('a')

    if action in ['plot', 'png', 'svg', 'pdf']:

        settings = {}
        for k in fields.keys():
            if k[0] in 'xyzcmsorntwhfgl':
                settings[k] = fields.getfirst(k).strip().decode('utf8', errors = 'ignore')
#            else: print >> sys.stderr, 'discarded', k, '=', fields.getfirst(k).strip()

        images = make_plot(settings)
        images['timestamp'] = '{}'.format(datetime.now())

        if action == 'plot':
            print "Content-Type: text/plain;charset=utf-8\n"
            print json.dumps(images)

        elif action in ['png', 'svg', 'pdf']:
            ct = action
            imgfile = images[ct]
            if sys.platform == "win32":
                import msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            with open(imgfile, 'rb') as img:
                data = img.read()
                print 'Content-Type: {}\n'.format(contenttypes[ct])
                print data,

    elif action == 'list':
        print "Content-Type: text/plain;charset=utf-8\n"
        print json.dumps(available_tables(h5dir))

    elif action == 'save':
        id = fields.getfirst('id').strip()
        if len(id) < 8: raise RuntimeError('session id must have at least 8 digits')
        data = fields.getfirst('data').strip()
        with open(os.path.join(sessiondir, '{}.session'.format(id)), 'w') as f:
            f.write(data.replace('},{', '},\n{'))
        print "Content-Type: text/plain;charset=utf-8\n"
        print json.dumps('saved {}'.format(id))

    elif action == 'load':
        id = fields.getfirst('id').strip()
        if len(id) < 8: raise RuntimeError('session id must have at least 8 digits')
        print "Content-Type: text/plain;charset=utf-8\n"
        try:
            with open(os.path.join(sessiondir, '{}.session'.format(id))) as f:
                for l in f: print l.strip()
        except:
            print 'no data for {}'.format(id)

    elif action == 'newid':
        id = randomChars(8)
        while os.path.isfile(os.path.join(sessiondir, '{}.session'.format(id))):
            id = randomChars(8)
        print "Content-Type: text/plain;charset=utf-8\n"
        print id
    else:
        raise ValueError('unknown action {}'.format(action))
