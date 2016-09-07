#!/usr/bin/python

from __future__ import print_function
import os
import threading, Queue
import sys
import netaddr
import requests

import socket
import subprocess


# bad global
safePrint = threading.Lock()

"""
def multiWrapper(func, redirect=None, *args):
	print('i was called')
	while not dataQueue.empty():
		item = dataQueue.get()
		if redirect:
			with open(redirect) as stdout:
				func(item, stdout=stdout, verbose=verbose)
		else:
			stdout = sys.stdout
			func(item, stdout=stdout, verbose=verbose)
"""

def ping_ips(dataQueue, stdout, verbose=False):

	while not dataQueue.empty():
		host = dataQueue.get()
		if 'linux' in sys.platform:
			command = ['/bin/ping', '-c', '1', '%s' % host]
			devnull = open(os.devnull, 'w')
		elif 'win' in sys.platform:
			command = ['c:/windows/system32/ping', '-n', '1', '%s' % host]
			devnull = open('nul', 'w')
		else:
			with safePrint:
				print("I don't know your OS -- exiting")
				return
		if verbose:
			with safePrint:
				print('from queue: %s' % host)
		try:
			subprocess.check_call(command, stdout=devnull, stderr=devnull)
			with safePrint:
				print('%s UP' % host, file=stdout)
		except subprocess.CalledProcessError as e:
			with safePrint:
				print('%s DOWN' % host, file=stdout)
		except Exception as e:
			with safePrint:
				print('%s "ERROR: %s"' % (host,e), file=stdout)

def make_request(url, headers=None, allow_redirects=False):
  r = requests.get(url, headers=headers, allow_redirects=allow_redirects)
  return r

def http_request(dataQueue, stdout, verbose=False, headers=None, allow_redirects=False):
    while not dataQueue.empty():
		url = dataQueue.get()
		try:
			r = make_request(url, headers=headers, allow_redirects=allow_redirects)	 
		except Exception as e:
			print("Failed to make request for %s: %s" % (url, e))
			continue
		with safePrint:
			if headers == None:
				print(url, r.status_code)
			else:
				print(url, r.headers)

def test_port(dataQueue, stdout, verbose=False):
	""" check if port is reachable """
	
	### assuming tcp for now, need to front-load protocols
	### and command-line arg for udp
	""""
	if protocol == 'tcp':
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	else:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	"""
	while not dataQueue.empty():
		host, port = dataQueue.get()
		if verbose:
			with safePrint:
				print('from queue: %s port %s' % (host, port))
		try:
			socket.setdefaulttimeout(1)
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect((unicode(host), int(port)))
		except (socket.error, socket.timeout):
			with safePrint:
				print('%s %s CLOSED' % (host, port), file=stdout)
		except Exception as e:
			with safePrint:
				print('%s %s "ERROR: %s"' % (host,port,e), file=stdout)
		else:
			with safePrint:
				print('%s %s OPEN' % (host, port), file=stdout)
		finally:
			s.close()

def initialize(func, dataArray, numThreads, verbose=False, stdout=sys.stdout):
	""" expects to be passed a function and an array of 
		data that is loaded into the queue and divied out
		to worker threads
	"""	

	dataQueue = Queue.Queue()
	# populate queue with data:
	[ dataQueue.put(item) for item in dataArray ]

	threads = []
	for i in range(numThreads):
		thread = threading.Thread(target=func, args=(dataQueue, stdout, verbose, ))
		threads.append(thread)
		thread.start()

	for thread in threads: thread.join()

def parse_host_list(rawHostList):
	""" clean up host LIST (should be passed as such) 
		that may be IPs, host names, or some combination of both """
	host_list = []
	for item in rawHostList:
        # first, check if it can be turned into netaddr.IPNetwork object:
		try:
			host_list.extend([i for i in netaddr.IPNetwork(item)])
		# presumably, a hostname was passed rather than an IP / IP block:
		except netaddr.core.AddrFormatError:
			#print("Error parsing %s: assuming it's a hostname" % item)
			host_list.append(item)
		# unknown exception:
		except Exception as e:
			print('Unknown exception: %s' % e)
	return host_list

def parsePortList(host_list, portList):
	""" take an already parsed list of hosts and create unique
		host-port tuples"""
	hostPortMap = []
	for host in host_list:
		for port in portList:
			# host-port tuple:
			hostPortMap.append((host, port))
	return hostPortMap
		
if __name__ == '__main__':

	import argparse

	NUMTHREADS = 10

	parser = argparse.ArgumentParser(description='Multi-threaded host ping and/or port check')
	parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose")
	parser.add_argument("host_list", nargs="+", help="specify IPs, subnet (in cidr), or hostnames")
	parser.add_argument("--ping", action="store_true", help="ping specified hosts ONLY (no port check)")
	parser.add_argument("--ports", nargs="+", help="ports to check: separated by spaces, no quotes")
	parser.add_argument("--http", action="store_true", default=False, help="test http respones / see header info")
	parser.add_argument("--threads", type=int, help="number of concurrent threads")
	parser.add_argument("--redirect", help="redirect to file")
	parser.add_argument("--append", action="store_true", help="append to redirect file, not overwrite")
	args = parser.parse_args()
		
	parsed_host_list = parse_host_list(args.host_list)
	numThreads = args.threads if args.threads else NUMTHREADS
	if args.redirect:
		if args.append: MODE = 'a'
		else: MODE = 'w'	
		stdout = open(args.redirect, MODE)
	else:
		stdout = sys.stdout
	if args.ports is True:
		hostPortMap = parsePortList(parsed_host_list, args.ports)
		initialize(test_port, hostPortMap, numThreads, args.verbose, stdout)
	elif args.ports is True:
		initialize(ping_ips, parsed_host_list, numThreads, args.verbose, stdout)
	elif args.http is True:
		initialize(http_request, parsed_host_list, numThreads, args.verbose, stdout)
	else:
		print("I can't figure out what you want me to do. Exiting")
		sys.exit(1)	
