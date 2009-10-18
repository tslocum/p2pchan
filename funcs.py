import time
import datetime
import uuid
import struct
import re
from StringIO import StringIO

def initializeDB(conn):
  c = conn.cursor()
  try:
    c.execute("create table posts (guid text, parent text, timestamp text, bumped text, name text, email text, subject text, thumb text, file text, message text)")
  except:
    pass

def getRequestPath(request):
  request_split = str(request).split()
  return request_split[1]

def formatError(text):
  return str('<body style="background-color: #fbb;"><div style="text-align: center;font-size: 3em;"><span style="padding: 5px;border-bottom: 1px solid #7A1818;border-right: 1px solid #7A1818;background-color: #fdd;color: #7A1818;">' + text + '</span></div></body>')

def timestamp(t=None):
  if not t:
    t = datetime.datetime.now()
  return int(time.mktime(t.timetuple()))

def formatDate(t=None):
  if not t:
    t = datetime.datetime.now()
  return t.strftime("%y/%m/%d(%a)%H:%M:%S")

def formatTimestamp(t):
  """
  Format a timestamp to a readable date
  """
  return formatDate(datetime.datetime.fromtimestamp(int(t)))

def timeTaken(time_start, time_finish):
  return str(round(time_finish - time_start, 2))

def newGUID():
  return str(uuid.uuid1())

def renderPage(text, p2pchan, replyto=False):
  reshtml = ''
  parenthtml = '<input type="hidden" name="parent" value="">'
  if replyto:
    reshtml = '&#91;<a href="/">Return</a>&#93;<div class="replymode">Posting mode: Reply</div>'
    parenthtml = '<input type="hidden" name="parent" value="' + replyto + '">'
  return str("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
  <title>
    P2PChan
  </title>
  <link rel="stylesheet" type="text/css" href="/css/global.css">
  <link rel="stylesheet" type="text/css" href="/css/futaba.css" title="Futaba">
  <link rel="alternate stylesheet" type="text/css" href="/css/burichan.css" title="Burichan">
  <meta http-equiv="content-type" content="text/html;charset=UTF-8">
  <meta http-equiv="pragma" content="no-cache">
  <meta http-equiv="expires" content="-1">
</head>
<body>
    <div class="adminbar">
      [<a href="/manage">Manage</a>]
    </div>
    <div class="logo">
      P2PChan
    </div>
    <hr width="90%" size="1">""" + reshtml + """
    <div class="postarea">
      <form name="postform" id="postform" action="/" method="post" enctype="multipart/form-data">
      """ + parenthtml + """
      <table class="postform">
        <tbody>
          <tr>
            <td class="postblock">
              Name
            </td>
            <td>
              <input type="text" name="name" size="28" maxlength="75" accesskey="n">
            </td>
          </tr>
          <tr>
            <td class="postblock">
              E-mail
            </td>
            <td>
              <input type="text" name="email" size="28" maxlength="75" accesskey="e">
            </td>
          </tr>
          <tr>
            <td class="postblock">
              Subject
            </td>
            <td>
              <input type="text" name="subject" size="40" maxlength="75" accesskey="s">
              <input type="submit" value="Submit" accesskey="z">
            </td>
          </tr>
          <tr>
            <td class="postblock">
              Message
            </td>
            <td>
              <textarea name="message" cols="48" rows="4" accesskey="m"></textarea>
            </td>
          </tr>
          <tr>
            <td class="postblock">
              File
            </td>
            <td>
              <input type="file" name="file" size="35" accesskey="f">
            </td>
          </tr>
          <tr>
            <td colspan="2" class="rules">
              <ul>
                <li>Supported file types are: GIF, JPG, PNG</li>
                <li>Images greater than 90x90 pixels will be thumbnailed.</li>
                <li>Currently """ + str(len(p2pchan.kaishi.peers)) + """ other users online.</li>
              </ul>
            </td>
          </tr>
        </tbody>
      </table>
      </form>
    </div>
    <hr>
    """ + text + """
    <br clear="left">
    <div class="footer" style="clear: both;">
      - <a href="http://tj9991.github.com/p2pchan/">p2pchan</a> -
    </div>
</body>
</html>""")

def renderManagePage(text):
  return str("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
  <title>
    P2PChan
  </title>
  <link rel="stylesheet" type="text/css" href="/css/global.css">
  <link rel="stylesheet" type="text/css" href="/css/futaba.css" title="Futaba">
  <link rel="alternate stylesheet" type="text/css" href="/css/burichan.css" title="Burichan">
  <meta http-equiv="content-type" content="text/html;charset=UTF-8">
  <meta http-equiv="pragma" content="no-cache">
  <meta http-equiv="expires" content="-1">
</head>
<body>
    <div class="adminbar">
      [<a href="/">Return</a>]
    </div>
    <div class="logo">
      P2PChan
    </div>
    <hr width="90%" size="1">
    """ + text + """
    <br clear="left">
    <hr width="90%" size="1">
    <div class="footer" style="clear: both;">
      - <a href="http://tj9991.github.com/p2pchan/">p2pchan</a> -
    </div>
</body>
</html>""")

def buildPost(post, numreplies=-1):
  POST_GUID = 0
  POST_PARENT = 1
  POST_TIMESTAMP = 2
  POST_BUMPED = 3
  POST_NAME = 4
  POST_EMAIL = 5
  POST_SUBJECT = 6
  POST_THUMB = 7
  POST_FILE = 8
  POST_MESSAGE = 9
  html = ""


  message = re.compile(r'&gt;&gt;([0-9A-Za-z]+)').sub('<a href="#' + r'\1' + '">&gt;&gt;' + r'\1' + '</a>', post[POST_MESSAGE])
  message = re.compile(r'^&gt;(.*)$', re.MULTILINE).sub(r'<span class="unkfunc">&gt;\1</span>', message)
  message = message.replace("\n", "<br>")

  if post[POST_PARENT] == "" and post[POST_FILE] != "":
    html += '<a target="_blank" href="' + post[POST_FILE] + '"><img src="' + post[POST_THUMB] + '" alt="' + post[POST_GUID] + '" class="thumb"></a>'
  else:
    html += """<table>
    <tbody>
    <tr>
    <td class="doubledash">
      &#0168;
    </td>""" + \
    '<td class="reply" id="' + post[POST_GUID] + '">'
  html += '<a name="' + post[POST_GUID][0:5] + '"></a>' + \
  '<label>'
  if post[POST_SUBJECT] != '':
    html += '<span class="filetitle">' + post[POST_SUBJECT] + '</span> '
  html += '<span class="postername">'
  if post[POST_EMAIL] != '':
    html += '<a href="mailto:' + post[POST_EMAIL] + '">'
  if post[POST_NAME] != '':
    html += post[POST_NAME]
  else:
    html += 'Anonymous'
  if post[POST_EMAIL] != '':
    html += '</a>'
  html += '</span> ' + \
  formatTimestamp(post[POST_TIMESTAMP]) + \
  '</label> ' + \
  '<span class="reflink">' + \
  '<a href="#' + post[POST_GUID][0:5] + '">ID:' + post[POST_GUID][0:5] + '</a> ' + \
  '</span>'
  if post[POST_PARENT] == '':
    html += ' [<a href="/manage?getthread=' + post[POST_GUID] + '" title="Refresh thread (find missed replies)">Refresh</a>]'
    if numreplies > -1:
      html += ' [<a href="/?res=' + post[POST_GUID] + '">Reply</a>]'
  elif post[POST_FILE] != '':
    html += '<br>' + \
    '<a target="_blank" href="' + post[POST_FILE] + '"><img src="' + post[POST_THUMB] + '" alt="' + post[POST_GUID] + '" class="thumb"></a>'
  html += '<blockquote>' + message + '</blockquote>'
  if numreplies > 5:
    html += '<span class="omittedposts">' + str(numreplies - 5) + ' post'
    if numreplies > 6:
      html += 's'
    html += ' omitted.  Click Reply to view.</span>'
  if post[POST_PARENT] != '':
    html += '</td>' + \
    '</tr>' + \
    '</tbody>' + \
    '</table>'
  return html

def encodePostData(post):
  return chr(27).join(post)

def decodePostData(postdata):
  return [x.replace("'", '&#39;').replace('"', '&quot;').replace("<", '&lt;').replace(">", '&gt;') for x in postdata.split(chr(27))]

def parseImageHostResponse(response):
  if 'rsp' not in response or 'error_code' in response:
    return []
  
  original_image = response[(response.find("<original_image>") + 16):response.find("</original_image>")]
  small_thumbnail = response[(response.find("<small_thumbnail>") + 17):response.find("</small_thumbnail>")]
  return [original_image, small_thumbnail]

def havePostWithGUID(guid, conn):
  c = conn.cursor()
  c.execute('select count(*) from posts where guid = \'' + guid.replace("'", '&#39;') + '\'')
  for row in c:
    if row[0] > 0:
      return True
  return False

def getImageInfo(data):
    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''

    # handle GIFs
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif (size >= 2) and data.startswith('\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass

    return content_type, width, height
