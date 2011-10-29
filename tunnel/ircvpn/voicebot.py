#!/usr/bin/python
import irclib
from conf import Conf

def voiceThem(chan, voiceword, c, e):
	if e.arguments()[0] == voiceword:
		c.mode(chan, "+v "+irclib.nm_to_n(e.source()))

def main():
	botname = None
	voiceword = None
	ircserver = None
	broadcastchan = None
	try:
		cfg = Conf.get('voicebot')
		botname = cfg.get('name')
		voiceword = cfg.get('voiceword')
		ircserver = Conf.get('ircserver')
		broadcastchan = Conf.get('broadcastchan')
	except:
		print "Error: Bad Configuration!"
		print ""
		print "You need a voicebot section with a name and voiceword configured"
		print "Also, ircserver and broadcastchan are needed"
		return 1
	
	print "Voicebot is starting.."
	irc = irclib.IRC()
	irc.add_global_handler("pubmsg", lambda c, e: voiceThem(broadcastchan, voiceword, c, e), -20)
	server = irc.server()
	server.connect(ircserver[0], ircserver[1], botname)
	server.join(broadcastchan)
	print "Connected, joining eventloop."
	irc.process_forever()

if __name__ == '__main__':
	main()
