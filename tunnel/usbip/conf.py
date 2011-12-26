#  ___________________________________________________
# |                                                   |
# |            usbip - ip over usbsticks              |
# |___________________________________________________|

import os

Conf = {
	# ======== network settings ========
	# ipsettings for the device
	'devname': '',
	'network':
		{
			'address': '10.10.10.11',
			'netmask': '255.255.255.0',
			#gateway: '',
			'mtu': 1400,
		},
	
	# ======== USB-Stick settings ========
	# udev attributes to choose a device on input
	# make sure this only matches to mountable devices
	'udevAttrs':
		{
			'ID_SERIAL': u'VBTM_Store__n__Go_0DE1A361400298C2-0:0',
			'UDISKS_PARTITION_NUMBER': u'1',
		},
	# where to mount the usb stick
	'mountpoint':			'/mnt/',
	# relative path from mountpoint, where to write network files
	'usbNetworkDir':		'net/',
	# prexif for all files, suffixed 
	'networkFilePrefix':	'data',
	# sync after unmount?
	'sync':					True
}

