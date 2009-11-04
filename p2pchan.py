import sys
import os
import sqlite3
import zlib
import urllib
import urllib2
import base64
import socket
import thread

from funcs import *
from kaishi import kaishi

import twisted
from twisted.web import static, server, resource
from twisted.internet import reactor

class P2PChanWeb(resource.Resource):
  isLeaf = True
  conn = sqlite3.connect(localFile('posts.db'))
  def render_GET(self, request):
    if getRequestPath(request).startswith('/manage'):
      return self.renderManage(request)
    else:
      return self.renderNormal(request)
    
  def render_POST(self, request):
    if getRequestPath(request).startswith('/manage'):
      return self.renderManage(request)
    else:
      return self.renderNormal(request)
    
  def renderNormal(self, request):
    global p2pchan
    replyto = False
    c = self.conn.cursor()
    c2 = self.conn.cursor()
    c3 = self.conn.cursor()
    request_path = getRequestPath(request)
    text = ""
    if 'message' in request.args:
      hostresponse = ['','']

      if 'file' in request.args:
        if request.args['file'][0] != '':
          imageinfo = getImageInfo(request.args['file'][0])
          if 'image/jpeg' in imageinfo[0] or 'image/png' in imageinfo[0] or 'image/gif' in imageinfo[0]:
            socket.setdefaulttimeout(60)
            params = urllib.urlencode({'key': '51d54904af112c52fc6b04f154134e7b', 'image': base64.b64encode(request.args['file'][0])})
            req = urllib2.Request("http://imgur.com/api/upload.xml", params)
            response = urllib2.urlopen(req)
            hostresponse = parseImageHostResponse(response.read())
            if hostresponse == []:
              return formatError('Unable to upload file')
          else:
            return formatError('Invalid file format')

      if request.args['parent'][0] == "" and hostresponse == ['','']:
        return formatError('You must upload an image to start a new thread')
      if request.args['parent'][0] != "" and hostresponse == ['',''] and request.args['message'][0] == '':
        return formatError('You must upload an image or enter a message to reply to a thread')
      
      post = [newGUID(),
              request.args['parent'][0],
              str(timestamp()),
              str(timestamp()),
              request.args['name'][0],
              request.args['email'][0],
              request.args['subject'][0],
              hostresponse[1],
              hostresponse[0],
              request.args['message'][0]]
      post = decodePostData(encodePostData(post))
      c.execute("insert into posts values ('" + "', '".join(post) + "')")
      if post[1] != "" and post[5].lower() != 'sage':
        c.execute("update posts set bumped = '" + post[2] + "' where guid = '" + post[1] + "'")
      self.conn.commit()
      p2pchan.kaishi.sendData('POST', encodePostData(post))
      if request.args['parent'][0] == '':
        return '<meta http-equiv="refresh" content="1;URL=/">--&gt; --&gt; --&gt;'
      else:
        return '<meta http-equiv="refresh" content="1;URL=/?res=' + request.args['parent'][0] + '">--&gt; --&gt; --&gt;'
    else:
      if 'res' in request.args:
        replyto = request.args['res'][0]
        c.execute('select * from posts where guid = \'' + request.args['res'][0] + '\' limit 1')
        for post in c:
          text += buildPost(post, self.conn)
        c.execute('select * from posts where parent = \'' + request.args['res'][0] + '\' order by timestamp asc')
        for post in c:
          text += buildPost(post, self.conn)
      else:
        c.execute('select * from posts where parent = \'\' order by bumped desc')
        for post in c:
          c2.execute('select count(*) from hiddenposts where guid = \'' + post[0] + '\'')
          for row in c2:
            if row[0] == 0:
              c3.execute('select count(*) from posts where parent = \'' + post[0] + '\'')
              for row in c3:
                numreplies = row[0]
                
              text += buildPost(post, self.conn, numreplies)

              replies = ''
              if numreplies > 0:
                c3.execute('select * from posts where parent = \'' + post[0] + '\' order by timestamp desc limit 5')
                for reply in c3:
                  replies = buildPost(reply, self.conn) + replies
                  
              text += replies + '<br clear="left"><hr>'
        
    return renderPage(text, p2pchan, replyto)

  def renderManage(self, request):
    global p2pchan
    replyto = False
    c = self.conn.cursor()
    request_path = getRequestPath(request)
    text = ''
    if 'getthread' in request.args:
      p2pchan.kaishi.sendData('THREAD', request.args['getthread'][0])
      text += 'Sent thread request. <a href="/?res=' + request.args['getthread'][0] + '">Go to thread</a>'
    elif 'fetchthreads' in request.args:
      p2pchan.kaishi.sendData('THREADS', "")
      text += 'Sent thread fetch request.'
    elif 'hide' in request.args:
      if not os.path.isfile(localFile('servermode')):
        c = self.conn.cursor()
        c.execute('select count(*) from hiddenposts where guid = \'' + request.args['hide'][0] + '\'')
        for row in c:
          if row[0] == 0:
            c.execute('insert into hiddenposts values (\'' + request.args['hide'][0] + '\')')
            self.conn.commit()
            text += 'Post hidden.'
          else:
            text += 'That post has already been hidden.'
    elif 'unhide' in request.args:
      c = self.conn.cursor()
      c.execute('delete from hiddenposts where guid = \'' + request.args['unhide'][0] + '\'')
      self.conn.commit()
      
    if text == '':
      text += """<form action="/manage" method="get">
      <fieldset>
      <legend>
      Fetch Full Thread
      </legend>
      <label for="getthread">Thread Identifier:</label> <input type="text" name="getthread"><br>
      <input type="submit" value="Fetch Thread" class="managebutton">
      </fieldset>
      </form>
      <fieldset>
      <legend>
      Hidden Posts
      </legend>"""
      c.execute('select count(*) from hiddenposts')
      for row in c:
        if row[0] > 0:
          c.execute('select * from hiddenposts order by guid asc')
          text += 'Click a post\'s guid to unhide it:'
          for row in c:
            text += '<br><a href="/manage?unhide=' + row[0] + '">' + row[0] + '</a>'
        else:
          text += 'You are not hiding any posts.'
      text += """
      </fieldset>
      <fieldset>
      <legend>
      Fetch Missing Threads
      </legend>"""
      missingthreads = []
      c = self.conn.cursor()
      c2 = self.conn.cursor()
      c.execute('select * from posts where parent != \'\'')
      for post in c:
        c2.execute('select count(*) from posts where guid = \'' + post[1] + '\'')
        for row in c2:
          if row[0] == 0 and post[1] not in missingthreads:
            missingthreads.append(post[1])
      if len(missingthreads) > 0:
        text += "You have " + str(len(missingthreads)) + " missing threads:"
        for missingthread in missingthreads:
          text += '<br>' + missingthread + ' - <a href="/manage?getthread=' + missingthread + '">Request thread</a>'
      else:
        text += "If you receive a reply to a thread which you do not yet have, it will appear in this list."
      text += """<br><br>
      Alternatively, you can send out a request for some of the latest threads which you have not yet received any replies for:<br>
      <form action="/manage" method="get"><input type="submit" name="fetchthreads" value="Fetch Threads" class="managebutton"></form>
      </fieldset>"""
    return renderManagePage(text)

class P2PChan(object):
  def __init__(self):
    print 'Initializing...'

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

    print 'Now available on the P2PChan network.'
    print 'Please ensure UDP port 44545 is open.'
    print 'Visit http://127.0.0.1:8080 to begin.'
    print 'There are currently ' + str(len(self.kaishi.peers)) + ' other users online.'
    
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

  root = resource.Resource()
  root.putChild("", P2PChanWeb())
  root.putChild("manage", P2PChanWeb())
  root.putChild("css", static.File(localFile('css')))
  site = server.Site(root)
  reactor.listenTCP(8080, site)

  reactor.run()

  
