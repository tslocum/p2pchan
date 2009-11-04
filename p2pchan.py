import sys
import os
import sqlite3

from funcs import *
from kaishi import kaishi

class P2PChan(object):
  def __init__(self):
    self.kaishi = kaishi()
    self.kaishi.provider = 'http://p2p.paq.cc/provider.php' # kaishi chat provider
    self.kaishi.handleIncomingData = self.handleIncomingData
    self.kaishi.handleAddedPeer = self.handleAddedPeer
    self.kaishi.handlePeerNickname = self.handlePeerNickname
    self.kaishi.handleDroppedPeer = self.handleDroppedPeer
    
    if len(sys.argv) > 1: # peerid supplied by command line
      self.host, self.port = self.kaishi.peerIDToTuple(sys.argv[1])
      self.port = int(self.port)
      self.kaishi.peers = [self.host + ':' + str(self.port)]

    self.kaishi.start()
    
  #==============================================================================
  # kaishi hooks
  def handleIncomingData(self, peerid, identifier, uid, message):
    conn = sqlite3.connect(localFile('posts.db'))
    if identifier == 'POST':
      post = decodePostData(message)
      if not self.havePostWithGUID(post[0]):
        c = conn.cursor()
        c.execute('select count(*) from posts where timestamp = \'' + post[2] + '\' and file = \'' + post[8] + '\'')
        for row in c:
          if row[0] == 0:
            c.execute("insert into posts values ('" + "', '".join(post) + "')")
            conn.commit()
            if post[1] != "" and post[5].lower() != 'sage':
              c.execute("update posts set bumped = '" + str(timestamp()) + "' where guid = '" + post[1] + "'")
              conn.commit()
    elif identifier == 'THREAD':
      if self.havePostWithGUID(message):
        c = conn.cursor()
        c.execute('select * from posts where guid = \'' + message.replace("'", '&#39;') + '\' limit 1')
        for post in c:
          self.kaishi.sendData('POST', encodePostData(post), to=peerid, bounce=False)
        c.execute('select * from posts where parent = \'' + message.replace("'", '&#39;') + '\'')
        for post in c:
          self.kaishi.sendData('POST', encodePostData(post), to=peerid, bounce=False)
    elif identifier == 'THREADS':
      c = conn.cursor()
      c2 = conn.cursor()
      c.execute('select * from posts where parent = \'\' order by bumped desc limit 50')
      for post in c:
        self.kaishi.sendData('POST', encodePostData(post), to=peerid, bounce=False)
        c2.execute('select * from posts where parent = \'' + post[0] + '\'')
        for reply in c2:
          self.kaishi.sendData('POST', encodePostData(reply), to=peerid, bounce=False)
    conn.close

  def handleAddedPeer(self, peerid):
    if peerid != self.kaishi.peerid:
      print peerid + ' has joined the network.'

  def handlePeerNickname(self, peerid, nick):
    pass
    
  def handleDroppedPeer(self, peerid):
    print peerid + ' has dropped from the network.'
  #==============================================================================

  def havePostWithGUID(self, guid):
    conn = sqlite3.connect(localFile('posts.db'))
    c = conn.cursor()
    c.execute('select count(*) from posts where guid = \'' + guid.replace("'", '&#39;') + '\'')
    for row in c:
      if row[0] > 0:
        conn.close()
        return True
    conn.close()
    return False

  def terminate(self, dummy=None):
    print 'Goodbye.'
    self.kaishi.gracefulExit()

if __name__=='__main__':
  print 'Initializing...'
  conn = sqlite3.connect(localFile('posts.db'))
  initializeDB(conn)

  p2pchan = P2PChan()
  p2pchan.kaishi.debug = False

  try:
    if os.name == "nt":
      import win32api
      win32api.SetConsoleCtrlHandler(p2pchan.terminate, True)
    else:
      import signal
      signal.signal(signal.SIGTERM, p2pchan.terminate)
  except:
    pass

  print 'Now available on the P2PChan network.'
  print 'Please ensure UDP port 44545 is open.'

  if not os.path.isfile(localFile('nodemode')):
    from twisted.web import static, server, resource
    from twisted.internet import reactor
    from p2pweb import P2PChanWeb

    print 'There are currently ' + str(len(p2pchan.kaishi.peers)) + ' other users online.'
    print 'Visit http://127.0.0.1:8080 to begin.'
    
    root = resource.Resource()
    root.putChild("", P2PChanWeb(p2pchan))
    root.putChild("manage", P2PChanWeb(p2pchan))
    root.putChild("css", static.File(localFile('css')))
    site = server.Site(root)
    reactor.listenTCP(8080, site)
    reactor.run()
  else:
    print '----------------------------------------'
    print 'Notice: Running in node mode.'
    print 'Notice: No web server has been started.'
    print '----------------------------------------'

    try:
      while True:
        raw_input('')
    except:
      pass
  

  
