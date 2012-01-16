#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Sebastian Lohff <seba@seba-geek.de>
# Licensed under GPL v3 or later

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

