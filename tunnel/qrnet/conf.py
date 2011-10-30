
import os


Conf = {
	# ======== network settings ========
	# ipsettings for the device
	'devname': '',
	'network':
		{
			'address': '10.10.10.74',
			'netmask': '255.255.255.0',
			#gateway: '',
			'mtu': 417,
		},
	# number of video device, mostly /dev/video<num> (value needed for opencv)
	'camnum': 0,
	
	# drop outgoing packets if more than X are in the queue
	'packetDrop': 20,
}

