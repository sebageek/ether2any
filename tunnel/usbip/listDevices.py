#!/usr/bin/python

import pyudev

context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem='block')
for action, device in monitor:
	if action == 'add':
		print device
		for k, v in device.items():
			print k.ljust(34), v
		print "-" * 80

