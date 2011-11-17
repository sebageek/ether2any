#!/usr/bin/python

import time
import asyncore
import select
import smtpd
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
import threading
import sys
sys.path.append("../../../")

from wtbase import SpamGenerator, DecodingException
from ether2any import Ether2Any
from ether2any.helper import getDstMacFromPkt, isBroadcast, binToHexStr
from conf import Conf, ENCRYPTION_NONE, ENCRYPTION_STARTTLS, ENCRYPTION_SSL

# Todo
#	Error checking at some places
#	Check for closed imap/smtp connections

class NetMailHandler():
	devWriteMutex = threading.Lock()
	""" Parse, decode and write incoming mails to output. """
	def __init__(self, dev, allowFrom, allowTo):
		self.dev = dev
		self.allowFrom = allowFrom
		self.allowTo = allowTo
		self.generator = SpamGenerator()
	
	def receiveMail(self, mailfrom, mailto, data):
		# FIXME: mailfrom can be None
		mail = email.email.message_from_string(data)
		
		# try to harvest text/plain part of mail
		if mail.get_content_type() == "text/plain":
			self._handleText(mail.get_payload())
		elif mail.get_content_type() == "multipart/alternative":
			for msg in mail.get_payload():
				if msg.get_content_type() == "text/plain":
					self.handleText(msg.get_payload())
		elif self.allowFrom == None and self.allowTo == None:
			self._handleText(data)
		else:
			pass
	
	def _handleText(self, text):
		data = None
		# FIXME: Where do these "\n " or 0a 20 come from?
		#        Seem to occure only when smtplib sends (long) mails to smtpd
		text = text.replace("\n ", "")
		try:
			#tmpTime = time.time()
			data = self.generator.decode(text)
			#print "DECODE", time.time() - tmpTime
		except DecodingException, e:
			print "Error: Could not decode text! See error below"
			print " < ----------- 8< ----------- > "
			print e
			print " < ----------- 8< ----------- > "
		if data:
			self.devWriteMutex.acquire()
			self.dev.write(data)
			self.devWriteMutex.release()

class SimpleSMTPServer(smtpd.SMTPServer):
	""" Simple small SMTP Server, gives mails to a handler. """
	def __init__(self, handler, *args, **kwargs):
		smtpd.SMTPServer.__init__(self, *args, **kwargs)
		self._handler = handler
	def process_message(self, peer, mailfrom, mailto, data):
		# give mail to handler
		self._handler.receiveMail(mailfrom, mailto, data)

class SMTPServerThread(threading.Thread):
	def __init__(self, listen, handler):
		threading.Thread.__init__(self)
		self.server = SimpleSMTPServer(handler, listen, None)
	
	def run(self):
		asyncore.loop()

class SimpleIMAPClient(threading.Thread):
	def __init__(self, imapConf, mailTo, handler):
		threading.Thread.__init__(self)
		self.imapConf = imapConf
		self.imap = None
		self.quit = False
		self.mailTo = mailTo
		self.handler = handler
		
		self.idleTagNum = 0
	
	def connect(self):
		if self.imapConf['crypto'] == ENCRYPTION_SSL:
			self.imap = imaplib.IMAP4_SSL(self.imapConf['server'], 993)
		else:
			self.smtp = imaplib.IMAP4(self.imapConf['server'])
		
		if self.imapConf['crypto'] == ENCRYPTION_STARTTLS:
			self.imap.starttls()
		
		if self.imapConf['authentication']:
			self.imap.login(self.imapConf['user'], self.imapConf['password'])
		
		ret = self.imap.select(self.imapConf['folder'])
		if ret[0] != 'OK':
			print "Error!"
	
	def fetchNewMailToDev(self):
		t = time.time()
		decTime = 0.0
		l = self.imap.search(None, 'UNSEEN')
		newMsgIds = l[1][0].replace(" ", ",")
		if newMsgIds == '':
			return False
		msgs = self.imap.fetch(newMsgIds, '(RFC822)')
		print "Imap: Found %d new messages" % len(newMsgIds.split(",")), "Fetch done:", time.time()-t
		for msg in msgs[1]:
			if msg == ")":
				# where does this come from...?
				continue
			if len(msg) != 2:
				print "Warning: Message broken, %d values in list, text '%s'" % (len(msg), msg)
				continue
			(flags, data) = msg
			tmpTime = time.time()
			self.handler.receiveMail(None, self.mailTo, data)
			decTime += time.time() - tmpTime
			#print "\t Recvd mail", time.time()-t, "decoding", decTime, "non acc", time.time() - tmpTime
		if self.imapConf['deleteAfterwards']:
			for msgid in newMsgIds.split(","):
				self.imap.store(msgid, "+FLAGS", r"\DELETED")
			self.imap.expunge()
		print "Processing of %d messages in %fs (decoding took %fs)" % (len(newMsgIds.split(",")), time.time()-t, decTime)
		return (len(msgs) > 0)
	
	def run(self):
		self.connect()
		
		while not self.quit:
			print "New IMAP loop"
			tries = 0
			while tries < len(self.imapConf['mailWait']):
				# get new mail
				if self.fetchNewMailToDev():
					tries = 0
				else:
					time.sleep(self.imapConf['mailWait'][tries])
					tries += 1
			# go into idle mode
			if self.imapConf['useIDLE']:
				print "Going into IDLE mode..."
				self.idleTagNum += 1
				idleTag = "a%04d" % self.idleTagNum
				self.imap.send("%s IDLE\r\n" % (idleTag,))
				quitLoop = False
				while not quitLoop:
					(r, w, e) = select.select([self.imap.socket()], [], [])
					msg = self.imap.readline()
					# TODO: Check if this filters out all idle "no new message" status msgs
					if not msg.startswith("+") and not msg.startswith("* OK"):
					#if msg.find("RECENT") >= 0
						quitLoop = True
				self.imap.send("DONE\r\n")
				# clear away ack msg
				msg = self.imap.readline()
				while msg.find(idleTag) < 0:
					msg = self.imap.readline()

class MailTunnel(Ether2Any):
	def __init__(self):
		Ether2Any.__init__(self, tap=Conf.get('tunnelEthernet', True))
		
		handlerConf = Conf.get('handler', {'allowFrom': None, 'allowTo': None})
		self.mailHandler = NetMailHandler(self.dev, **handlerConf)
		self.mailTo = Conf.get('mailTo', None)
		self.mailFrom = Conf.get('mailFrom', None)
		
		self.smtpConf = Conf.get('smtp')
		smtpd = Conf.get("smtpd", {'enabled': False})
		if smtpd['enabled']:
			self.smtpd = SMTPServerThread(smtpd['listen'], self.mailHandler)
		else:
			self.smtpd = None
		
		imapConf = Conf.get("imap", {'enabled': False})
		if imapConf['enabled']:
			self.imap = SimpleIMAPClient(imapConf, self.mailTo, self.mailHandler)
		else:
			self.imap = None
		
		self.generator = SpamGenerator()
		
		network = Conf.get('network', {'mtu': 1400})
		self.dev.ifconfig(**network)
	
	def connectSMTP(self):
		if self.smtpConf['crypto'] == ENCRYPTION_SSL:
			self.smtp = smtplib.SMTP_SSL(self.smtpConf['server'], 465)
		else:
			self.smtp = smtplib.SMTP(self.smtpConf['server'])
		
		if self.smtpConf['crypto'] == ENCRYPTION_STARTTLS:
			self.smtp.starttls()
		
		if self.smtpConf['authentication']:
			self.smtp.login(self.smtpConf['user'], self.smtpConf['password'])
	
	def sendMail(self, fromAddr, toAddrs, subject, msg):
		e = MIMEText(msg)
		e['Subject'] = subject
		e['From'] = fromAddr
		e['To'] = ",\n".join(toAddrs)
		t = time.time()
		try:
			self.smtp.sendmail(fromAddr, toAddrs, e.as_string())
			#print "Mail took %fs" % (time.time()-t)
		except smtplib.SMTPServerDisconnected:
			self.connectSMTP()
			self.smtp.sendmail(fromAddr, toAddrs, e.as_string())
			print "Mail+reconnect took %fs" % (time.time()-t)
	
	def sendToNet(self, packet):
		data = self.generator.encode(packet)
		self.sendMail(self.mailFrom, [self.mailTo], "Ohai!", data) 
	
	def sendToDev(self, socket):
		pass
	
	def run(self):
		# start threads / connections
		self.connectSMTP()
		
		if self.imap:
			self.imap.start()

		if self.smtpd:
			self.smtpd.start()
		
		# call super method
		Ether2Any.run(self)

if __name__ == '__main__':
	mailtun = MailTunnel()
	import cProfile
	#p = cProfile.run('mailtun.run()')
	#p.sort_stats('time', 'cum').print_stats(.5, 'init')
	mailtun.run()

