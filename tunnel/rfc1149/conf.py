#  ___________________________________________________
# |                                                   |
# |  rfc1149 - ip over avian carrier (quadrocopter)   |
# |___________________________________________________|

import os

Conf = {
	# ======== network settings ========
	# ipsettings for the device
	'devname': '',
	'network':
		{
			'address': '10.10.10.10',
			'netmask': '255.255.255.0',
			#gateway: '',
			'mtu': 1400,
		},
	
	# ======== printer settings ========
	'printerName': None,
	'serial': '/dev/ttyUSB0',

	# ======== printer settings ========
	'mountpoint': '/mnt/',
	'udevAttrs':
		{
			'ID_SERIAL': 'NIKON_D50-0:0',
			'UDISKS_PARTITION_NUMBER': '1',
		},
	# ======== misc settings ========
	'ackPackets': True,
}

