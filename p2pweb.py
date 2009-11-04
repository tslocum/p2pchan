import zlib
import base64
import thread
import urllib
import urllib2
import socket
import sqlite3

from funcs import *

import twisted
from twisted.web import static, server, resource
from twisted.internet import reactor

class P2PChanWeb(resource.Resource):
  isLeaf = True
  conn = sqlite3.connect(localFile('posts.db'))
  
  def __init__(self, p2pchan):
    self.p2pchan = p2pchan
    
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
      self.p2pchan.kaishi.sendData('POST', encodePostData(post))
      if request.args['parent'][0] == '':
        return '<meta http-equiv="refresh" content="1;URL=/">--&gt; --&gt; --&gt;'
      else:
        return '<meta http-equiv="refresh" content="1;URL=/?res=' + request.args['parent'][0] + '">--&gt; --&gt; --&gt;'
    else:
      if 'res' in request.args:
        replyto = request.args['res'][0]
        c.execute('select * from posts where guid = \'' + request.args['res'][0] + '\' limit 1')
        for post in c:
          text += buildPost(post, self.conn, -1)
        c.execute('select * from posts where parent = \'' + request.args['res'][0] + '\' order by timestamp asc')
        for post in c:
          text += buildPost(post, self.conn, -1)
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
                  replies = buildPost(reply, self.conn, 0) + replies
                  
              text += replies + '<br clear="left"><hr>'
        
    return renderPage(text, self.p2pchan, replyto)

  def renderManage(self, request):
    replyto = False
    c = self.conn.cursor()
    request_path = getRequestPath(request)
    text = ''
    if 'getthread' in request.args:
      self.p2pchan.kaishi.sendData('THREAD', request.args['getthread'][0])
      text += 'Sent thread request. <a href="/?res=' + request.args['getthread'][0] + '">Go to thread</a>'
    elif 'fetchthreads' in request.args:
      self.p2pchan.kaishi.sendData('THREADS', "")
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
    elif 'peers' in request.args:
      self.p2pchan.kaishi.fetchPeersFromProvider()
      text += 'Refreshed peer provider.'
      
    if text == '':
      text += """<table width="100%" border="0"><tr width="100%"><td width="50%">
      <form action="/manage" method="get">
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
      </fieldset>
      <fieldset>
      <legend>
      Refresh Peer Provider
      </legend>
      <form action="/manage" method="get"><input type="submit" name="peers" value="Refresh Peers" class="managebutton"></form>
      </fieldset></td><td width="50%" valign="top">
      <fieldset>
      <legend>
      Help
      </legend>
      <p>To fetch some of the latest posts so you don't have a blank board, click "Fetch Threads" to the left.</p>
      <p>If you can not properly connect to any peers, or are connected but don't receive any posts from them, your computer or router may be blocking P2PChan's traffic. Try opening port 44545 on your router, or disabling your local firewall for P2PChan's process.</p>
      <p>Use > to quote some text: <span class="unkfunc">&gt;you, sir, are and idiot :)</span></p>
      <p>Use >> to reference another post in the same thread: <a href="#1a179">&gt;&gt;1a179</a></p>
      <p>Use >>> to reference another thread: <a href="/?res=b02de651-c923-11de-b7eb-001d72ed9aa8">&gt;&gt;&gt;&shy;b02de651-c923-11de-b7eb-001d72ed9aa8</a></p>
      </fieldset>
      </td></tr></table>"""
    return renderManagePage(text)
