#  ___________________________________________________
# |                                                   |
# | ircvpn - irc virtual public network configuration |
# |___________________________________________________|

# config options
# IRC
#    - server (ip, port, ssl)
#	 - channel
#	 - nick prefix
#	 - maximum line length
# Network
#    - device: ip, netmask, mtu
#    - dhclient instead of static ip?
#    - routing?
#	 - dns?
# Tunnel
#	 - security settings
#	 - mode (hub or switch)

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
	#ircserver = ('irc.someserver.de', 6667)
	#ircserver = ('testine.someserver.de', 6667)
	#ircserver = ('192.168.56.1', 6667)
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
	# arguments: <command> <device>
	'postConnectCmd': '/sbin/dhclient -v %s',
}
