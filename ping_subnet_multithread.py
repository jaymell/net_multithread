#!/usr/bin/python

import netaddr
import subprocess
import os
import threading, Queue
import sys
import time
import argparse

parser = argparse.ArgumentParser(description='Multi-threaded host ping')
parser.add_argument("file_list", nargs="+")
args = parser.parse_args()

safeprint = threading.Lock()
dataQueue = Queue.Queue()

# used_file = '/tmp/used_ips'
# unused_file = '/tmp/unused_ips'

def ping_ips(dataqueue):
        while not dataQueue.empty():
                ip = dataqueue.get()
                command = ['/bin/ping', '-c', '1', '%s' % ip]
                devnull = open(os.devnull, 'w')
                # print('from queue: %s' % ip)
                try:
                        subprocess.check_call(command, stdout=devnull, stderr=devnull)
                        with safeprint:
                                print('In use: %s' % ip)
                                # with open(used_file, 'a') as f:
                                #         f.write('%s\n' % ip)
                except subprocess.CalledProcessError as e:
                        with safeprint:
                                print('Unused: %s' % ip)
                                # with open(unused_file, 'a') as f:
                                #         f.write('%s\n' % ip)
                except Exception as e:
                        print('Unknown error: %s: %s' % (ip,e))


#network = IPNetwork('10.0.8.1/27')

# this array holds IPs for individual IPs or subnets
# that may be passed on command line:
network_list = []
host_list = []

for item in args.file_list:
        # first, check if it can be turned into netaddr.IPNetwork object:
        try:
                network_list.extend([i for i in netaddr.IPNetwork(item)])
        # presumably, a hostname was passed rather than an IP / IP block:
        except netaddr.core.AddrFormatError:
                host_list.append(item)
        # unknown exception:
        except Exception as e:
                print('Unknown exception: %s' % e)

# populate queue with above:
for ip in network_list:
        dataQueue.put(ip)
for host in host_list:
        dataQueue.put(host)

numthreads=10
threads = []

for i in range(numthreads):
        thread = threading.Thread(target=ping_ips, args=(dataQueue, ))
	threads.append(thread)
        # thread.daemon = True
        thread.start()

for thread in threads: thread.join()
