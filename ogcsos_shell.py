#! /usr/bin/env python
# -*- coding:utf-8 -*-
#
# simple shell interface for OGC API 
#
# 2017-01-22 created by Satoru MIYAMOTO
#
#
from __future__ import print_function
import sys
if sys.version_info[0] == 2:
    user_input = raw_input
else:
    user_input = input
import argparse
import os
import ogcsosapi
from ogcsosapi import SOSServer
from datetime import datetime, timedelta
import readline

HISTORY_FILE = '.ogcsos_shell_history'

class AP(argparse.ArgumentParser):
    """inherits ArgumentParser to prevent it to exit after printing help.

    """
    def exit(self, status=0, message=None):
        raise argparse.ArgumentError(None, '')


def parse_args():
    parser = argparse.ArgumentParser(description='Simple Shell Interface for OGC SOS API')
    parser.add_argument("--token", required=True, help="your Token to use SOS API")
    parser.add_argument("--is_token_header", action='store_true')
    parser.add_argument("--endpoint", help="endpoint of SOS Server",
                        default='https://cs.listenfield.com/OGCAPIV2.jsp')
    parser.add_argument('--command', help='command to execute')
    parser.add_argument('--debug', action='store_true', help='enable debug mode')
    parser.add_argument('--instant', action='store_true',
                        help='prevent to call GetCapability, you must specify node or sensor by name.')
    args = parser.parse_args()
    return args

def print_help():
    print('''
    nodes                          : list all sensor nodes served by the server
    sensors [node]                 : list all sensors in the node
    measures -n [node] [sensors..] : get measurements of sensors of a node
    put-measures -n [node] [date,property,value,uom]
                                   : put measurement to a sensor of a node
    server                         : show server info
    provider                       : show provider info
    help                           : print this help
''')

def list_nodes(args, sosserver):
    parser = AP(prog='nodes')
    parser.add_argument('-l', action='store_true')
    try:
        opts = parser.parse_args(args)
    except:
        return 
    for i, node in enumerate(sosserver.observations):
        if opts.l:
            print('%2d: %s : %s' % (i+1, node.name, node.description))
        else:
            print('%2d: %s' % (i+1, node.name))

def show_server(sosserver):
    print('%s: ' % (sosserver.server.name))
    print(' service type     : %s' % (sosserver.server.service_type))
    print(' service version  : %s' % (sosserver.server.service_version))
    print(' service fees     : %s' % (sosserver.server.fees))
    print(' served operations:')
    print('       %s' % (','.join(sosserver.operations)))

def show_provider(sosserver):
    print('%s: ' % (sosserver.provider.name))
    print(' administrator  : %s' % (sosserver.provider.indiviual_name))
    print(' address:')
    print('    %s' % (sosserver.provider.point))
    print('    %s, %s, %s' % (sosserver.provider.city, 
                              sosserver.provider.pref, sosserver.provider.country))

def get_node_from_name_or_number(ind, nodes):
    the_node = None
    if ind.isdigit():
        # node number
        try:
            the_node = nodes[int(ind)-1]
        except IndexError:
            pass
    else:
        for node in nodes:
            if node.name == ind:
                the_node = node
                break
        else:
            return ind
                
    return the_node

def get_prop_from_name_or_number(ind, node):
    the_prop = None
    if ind.isdigit():
        # sensor number
        try:
            the_prop = node.properties[int(ind)-1]
        except IndexError:
            pass
    elif node and type(node) != str:
        for prop in node.properties:
            if prop == ind:
                the_prop = prop
                break
    else:
        return ind
    return the_prop

def list_sensors(args, sosserver):
    parser = AP(prog='sensors')
    parser.add_argument('sensor', help='number or name of sensor')
    try:
        opts = parser.parse_args(args)
    except:
        return
    
    print(opts.sensor)
    the_node = get_node_from_name_or_number(opts.sensor, sosserver.observations)
    if the_node:
        for i, prop in enumerate(the_node.properties):
            print('%2d: %s' % (i+1, prop))
    else:
        print('No node was found !!')

def parse_cmd_datetime(dtstr):
    tries = [
        ('%Y%m%d%H%M%S', False),
        ('%Y%m%d%H%M', False),
        ('%Y-%m-%dT%H:%M:%S', False),
        ('%Y-%m-%dT%H:%M', False),
        ('%Y-%m-%d', False),
        ('%H:%M:%S', True),
        ('%H:%M', True),
        ('%H%M', True),
    ]

    for t in tries:
        try:
            dt = datetime.strptime(dtstr, t[0])
            if t[1]:
                # need to set date
                now = datetime.now()
                return dt.replace(year=now.year, month=now.month, day=now.day)
            else:
                return dt
        except ValueError:
            pass

    raise ValueError

def get_measurements(args, sosserver):
    parser = AP(prog='measurements')
    parser.add_argument('-s', help='start datetime')
    parser.add_argument('-e', help='end datetime')
    parser.add_argument('-n', help='node name or number', required=True)
    parser.add_argument('-r', action='store_true', help='use GetResult')
    #parser.add_argument('--header', action='store_true', help='with header')
    parser.add_argument('sensors', nargs='+', help='sensors to get')
    try:
        opts = parser.parse_args(args)
    except:
        return

    try:
        if opts.s:
            s_dt = parse_cmd_datetime(opts.s)
            if opts.e:
                e_dt = parse_cmd_datetime(opts.e)
            else:
                e_dt = datetime.now()
            if s_dt >= e_dt:
                print('start datetime must be less than end datetime !')
                return
    except ValueError:
        print('invalid datetime is specified. Please use format, 2016-10-26T00:00:00')
        return

    the_node = get_node_from_name_or_number(opts.n, sosserver.observations)
    if not the_node:
        print('No node was found !!')
        return

    if not opts.s:
        e_dt = datetime.now()
        s_dt = e_dt - timedelta(seconds=10*60)

    properties = []
    for sensor in opts.sensors:
        prop = get_prop_from_name_or_number(sensor, the_node)
        if not prop:
            'No sensor was found in %s !!' % (the_node.name)
            return
        properties.append(prop)

    if opts.r:
        measurements = sosserver.get_result(the_node, properties, [s_dt, e_dt])
    else:
        measurements = sosserver.get_observation(the_node, properties, [s_dt, e_dt])

    print('time,%s' % (','.join(properties)))
    for dt, measure in sorted(measurements.items()):
        line = []
        line.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
        for prop in properties:
            if prop in measure:
                line.append(str(measure[prop]['value']))
            else:
                line.append('')
        print(','.join(line))

def put_measurements(args, sosserver):
    parser = AP(prog='put-measurements')
    parser.add_argument('-n', help='node name or number', required=True)
    parser.add_argument('measures', nargs='+', help='<date,observed property,value,uom> to put')
    try:
        opts = parser.parse_args(args)
    except:
        return

   
    the_node = get_node_from_name_or_number(opts.n, sosserver.observations)
    if not the_node:
        print('No node was found !!')
        return

    measurements = {}
    dt = None
    for measure in opts.measures:
        elms = measure.split(',')
        if dt is None or len(elms) == 4:
            # use same datetime
            try:
                dt = parse_cmd_datetime(elms[0])
            except ValueError:
                print('invalid datetime is specified. Please use format, 2016-10-26T00:00:00')
                return

            offset = 1
        elif len(elms) == 3:
            offset = 0

        if dt not in measurements:
            measurements[dt] = {}

        prop = get_prop_from_name_or_number(elms[offset], the_node)
        if prop not in measurements[dt]:
            measurements[dt][prop] = {}

        measurements[dt][prop]['value'] = elms[offset+1]
        measurements[dt][prop]['uom'] = elms[offset+2]

    response = sosserver.insert_observation(the_node, measurements)
    print(response)


def exec_command(cmd, sosserver):
    if len(cmd) == 0:
        return True

    args = cmd.split()
    if args[0] == 'h' or args[0] == 'help':
        print_help()
    elif args[0] == 'q' or args[0] == 'quit' or args[0] == 'exit':
        return False
    elif args[0] == 'server':
        show_server(sosserver)
    elif args[0] == 'provider':
        show_provider(sosserver)
    elif args[0] == 'nodes':
        list_nodes(args[1:], sosserver)
    elif args[0] == 'sensors':
        list_sensors(args[1:], sosserver)
    elif args[0] == 'measurements' or args[0] == 'measures':
        get_measurements(args[1:], sosserver)
    elif args[0] == 'put-measurements' or args[0] == 'put-measures':
        put_measurements(args[1:], sosserver)
    else:
        print_help()
    return True

def main():
    opts = parse_args()

    if opts.debug:
        ogcsosapi.debug = True

    if not opts.command:
        print('Simple Shell Interface for OGC SOS API by Satoru MIYAMOTO\n')
        
    sosserver = SOSServer(opts.endpoint, opts.token, opts.is_token_header)
    if not opts.instant:
        sosserver.update_capabilities()
        if not opts.command:
            print('Welcome to %s by %s !' % (sosserver.server.name, sosserver.provider.name))

    if opts.command:
        exec_command(opts.command, sosserver)
        return

    # read history file
    histfile = os.path.join(os.path.expanduser('~'), HISTORY_FILE)
    if os.path.exists(histfile):
        readline.read_history_file(histfile)
    readline.set_history_length(1000)

    prompt = '\nSOS: ' if os.name == 'nt' else '\n\033[1;32mSOS: \033[1;m'
    while True:
        cmd = user_input(prompt)
        if not exec_command(cmd, sosserver):
            break

    # write history file
    readline.write_history_file(histfile)

if __name__ == '__main__':
    main()
