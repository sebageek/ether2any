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
	
	# hubbed ("HUB")/switched("SWITCH") Network
	# 	HUB:    communicate only over broadcastchan
	#   SWITCH: use query for non broadcast packages
	'mode': "HUB",
		
	# ======== IRC settings ========
	# irc-server to use
	'ircserver': ('testine.someserver.de', 6667),
	
	# broadcast domain (where to meet other clients)
	'broadcastchan': '#broadcastchan',
	
	# nick prefix (needs to be the same on all clients)
	'nickPrefix': 'VPN',
	
	# maximum msg len
	'ircmsglen': 400,
	
	# NOT IMPLEMENTED: reconnect on server disconnect
	'ircReconnect': False,
	'ircReconnectDelay': 3,
	

	# ======== security settings ========
	# accept packages if virtual mac != package mac
	'acceptNonMatchingMac': True,
	
	# ignore messages from non-mac user names
	'ignoreNonMacUser': True,
	
	# drop non broadcast packages from broadcast when
	# in switched network mode
	'strictSwichedNetwork': False,
	
	# ======== extra tools settings ========
	'voicebot':
		{
			'name': 'flowControl',
			'voiceword': 'requesting network access',
		},
	
	# ======== misc settings ========
	# executed after being connected to the server
	# %s will be replaces with the device name
	'postConnectCmd': '/sbin/dhclient -v %s',
}
