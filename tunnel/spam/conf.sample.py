import os

ENCRYPTION_NONE, ENCRYPTION_STARTTLS, ENCRYPTION_SSL = range(3)

Conf = {
	# ======== network settings ========
	# select the kind of tunnel
	# True: tap-device, tunneling ethernet
	# False: tun-device, tunneling ip
	'tunnelEthernet': True,
	
	# ipsettings for the device
	'network':
		{
			'address':	'10.10.10.3',
			'netmask':	'255.255.255.0',
			#gateway:	'',
			'mtu':		1400,
		},
	
	# ========  mail settings   ========
	# mail adress to which all packets are sent
	'mailTo': '',
	
	# mail address to send mail from (only for the mailheader / display)
	'mailFrom': '',
	
	# extra address to handle broadcast packets
	# set to None if you want broadcasts also handled by mailTo addr
	# ATM this is not implemented
	'broadcastTo': None,
	
	# smtp data for outgoing packets
	'smtp':
		{
			'server':			'',
			'crypto':			ENCRYPTION_SSL,
			'authentication':	True,
			'user':				'',
			'password':			'',
		},
	
	# smtpd - a small mailserver to handle incoming packets
	'smtpd':
		{
			'enabled':			False,
			'listen':			('0.0.0.0', 25),
		},
	
	# imap - get incoming data from an imap server
	'imap':
		{
			'enabled':			False,
			'server':			'',
			'crypto':			ENCRYPTION_SSL,
			'authentication':	True,
			'user':				'',
			'password':			'',
			'folder':			'INBOX',
			'deleteAfterwards':	True,
			# intervals to wait when fetching mail fails
			# afterwards the fetcher will go into IMAPv4 IDLE mode
			'mailWait':			[0.25, 0.5, 0.75],
			'useIDLE':			True
		},
	
	# mail handler configuration
	# this is the part which handles incoming mail delivered by imap or smtpd
	'handler':
		{
			# list of all allowed senders, None for everyone
			# e.g. ["foo@somedomain.de", "bar@someserver.de"]
			'allowFrom':		None,
			
			# list of all allowed recipients, None for everyone
			# e.g. ["foo@somedomain.de", "bar@someserver.de"]
			'allowTo':			None,
		},
}

