#!/usr/bin/python

import netaddr
import subprocess
import os
import threading, Queue
import sys
import time

safeprint = threading.Lock()
dataQueue = Queue.Queue()

def ping_ips(dataqueue, verbose=False):
	""" thread function """

	while not dataQueue.empty():
		ip = dataqueue.get()
		command = ['/bin/ping', '-c', '1', '%s' % ip]
		devnull = open(os.devnull, 'w')
		if verbose:
			with safeprint:
				print('from queue: %s' % ip)
		try:
			subprocess.check_call(command, stdout=devnull, stderr=devnull)
			with safeprint:
				print('In use: %s' % ip)
		except subprocess.CalledProcessError as e:
			with safeprint:
				print('Unused: %s' % ip)
		except Exception as e:
			print('Unknown error: %s: %s' % (ip,e))

def initialize(raw_host_list, verbose=False, numthreads=10):
	""" parse raw_host_list and populate queues -- raw_host_list 
		can be comprised of subnets (if so,	first break them out 
		into indivdual IPs) or host names """

	host_list = []
	for item in raw_host_list:
		# first, check if it can be turned into netaddr.IPNetwork object:
		try:
			host_list.extend([i for i in netaddr.IPNetwork(item)])
		# presumably, a hostname was passed rather than an IP / IP block:
		except netaddr.core.AddrFormatError:
			host_list.append(item)
		# unknown exception:
		except Exception as e:
			print('Unknown exception: %s' % e)

	# populate queue with above:
	[ dataQueue.put(host) for host in host_list ]

	threads = []

	for i in range(numthreads):
		thread = threading.Thread(target=ping_ips, args=(dataQueue, verbose))
		threads.append(thread)
		# thread.daemon = True
		thread.start()

	for thread in threads: thread.join()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description='Multi-threaded host ping')
	parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose")
	parser.add_argument("host_list", nargs="+", help="specify IPs, subnet (in cidr), or hostnames")
	args = parser.parse_args()
	initialize(args.host_list, args.verbose)
