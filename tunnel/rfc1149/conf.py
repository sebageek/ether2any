#  ___________________________________________________
# |                                                   |
# | ircvpn - irc virtual public network configuration |
# |___________________________________________________|

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
			'mtu': 1400,
		},
	
	# ======== Twitter settings ========
	'twitter':
	{
		# account to read network traffic from
		'endpoint': None,
		
		# if set to None, these will be overwritten by config_auth.py
		# if they are set to none there, this script will give you an
		# url to authorize this script to twitter and write the
		# access key / access secret to config_auth.py
		'ACCESS_KEY': None,
		'ACCESS_SECRET': None,
	},
}

import conf_auth
