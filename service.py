# -*- coding: utf-8 -*-

import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import shutil
import unicodedata
import re
import string
import difflib
import HTMLParser
import time
import datetime
import urllib2
import gzip
import zlib
import StringIO
import cookielib
import socket

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('path')), 'utf-8')
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__resource__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')), 'utf-8')
__resource_dict__ = unicode(xbmc.translatePath(os.path.join(__cwd__, 'resources')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp')), 'utf-8')
time_script_begin = time.time()

def check_script_time():
    _curr_time = time.time();
    return _curr_time - time_script_begin

# prepare cookie url opener
cookies = cookielib.LWPCookieJar()
handlers = [
    urllib2.HTTPHandler(),
    urllib2.HTTPSHandler(),
    urllib2.HTTPCookieProcessor(cookies)
    ]
opener2 = urllib2.build_opener(*handlers)

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'),xbmc.LOGERROR)

# remove file and dir with 30 days before / now after time
def clear_tempdir(strpath):
    if xbmcvfs.exists(strpath):
        try:
            low_time = time.mktime((datetime.date.today() - datetime.timedelta(days=15)).timetuple())
            now_time = time.time()
            for file_name in xbmcvfs.listdir(strpath)[1]:
                if sys.platform.startswith('win'):
                    full_path = os.path.join(strpath, file_name)
                else:
                    full_path = os.path.join(strpath.encode('utf-8'), file_name)
                cfile_time = os.stat(full_path).st_mtime
                if low_time >= cfile_time or now_time <= cfile_time:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
        except:
            log(__scriptname__,"error on cleaning temp dir")

clear_tempdir(__temp__)

xbmcvfs.mkdirs(__temp__)

sys.path.append(__resource__)

from engchartohan import engtypetokor

base_page = "http://www.jamack.net"
load_page_enum = [1,2,3,4,5,6,7,8,9,10]
load_file_enum = [10,20,30,40,50,60,70,80,90]
max_pages = load_page_enum[int(__addon__.getSetting("max_load_page"))]
max_file_count = load_file_enum[int(__addon__.getSetting("max_load_files"))]
use_titlename = __addon__.getSetting("use_titlename")
user_agent = __addon__.getSetting("user_agent")
use_engkeyhan = __addon__.getSetting("use_engkeyhan")
use_se_ep_check = __addon__.getSetting("use_se_ep_check")
use_engkor_dict = __addon__.getSetting("use_engkor_dict")
file_engkor_dict = __addon__.getSetting("file_engkor_dict")
engkor_dict = {}

def dict_read(filename):
    dict = {}
    fin = open(filename, 'r')
    while True:
        line = fin.readline()
        if len(line)==0:
            break
        sh, sd = line.split('=',1)
        sd = sd.strip()
        if len(sd)>0:
            dict[sh]=sd
    fin.close()
    return dict

def find_dict(istr):
    ret = []
    a = istr.split()
    for sstr in a:
        if sstr.lower() in engkor_dict.keys():
            ret.append(engkor_dict[sstr.lower()])
    rs = ' '.join(ret)
    #log(__scriptname__,'find_dict res, %s' % rs.decode("utf-8"))
    return urllib.quote(rs)

# init dictionary
if file_engkor_dict=='':
    file_engkor_dict = os.path.join(__resource_dict__.encode("utf-8"),'engkor_dict.txt')
if use_engkor_dict=='true':
    try:
        engkor_dict = dict_read(file_engkor_dict)
    except:
        use_engkor_dict = 'false'
        log(__scriptname__,'cannot find file %s' % file_engkor_dict)
        pass

ep_expr = re.compile("[\D\S]+(\d{1,2})(\s+)?[^\d\s\.]+(\d{1,3})")
subtitle_txt = re.compile("\d+\:\d+\:\d+\:")
sub_ext_str = [".smi",".srt",".sub",".ssa",".ass",".txt"]

def smart_quote(str):
    ret = ''
    spos = 0
    epos = len(str)
    while spos<epos:
        ipos = str.find('%',spos)
        if ipos == -1:
            ret += urllib.quote(str[spos:])
            spos = epos
        else:
            ret += urllib.quote(str[spos:ipos])
            spos = ipos
            ipos+=1
            # check '%xx'
            if ipos+1<epos:
                if str[ipos] in string.hexdigits:
                    ipos+=1
                    if str[ipos] in string.hexdigits:
                        # pass encoded
                        ipos+=1
                        ret+=str[spos:ipos]
                    else:
                        ret+=urllib.quote(str[spos:ipos])
                else:
                    ipos+=1
                    ret+=urllib.quote(str[spos:ipos])
                spos = ipos
            else:
                ret+=urllib.quote(str[spos:epos])
                spos = epos
    return ret

def prepare_search_string(s):
    s = string.strip(s)
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    return s
    
jamack_query = "/?error_return_url=%%2F&vid=&mid=search&act=IS&where=document&search_target=title" #&is_keyword=%s&page=%d

# 메인 함수로 질의를 넣으면 해당하는 자막을 찾음.
def get_subpages(query,list_mode=0):
    file_count = 0
    page_count = 1
    # 한글은 인코딩되어서 전달됨
    if item['mansearch']:
        newquery = smart_quote(query)
    else:
        newquery = smart_quote(prepare_search_string(query))
    # first page
    url = base_page+jamack_query+"&is_keyword=%s" % (newquery)
    while page_count<=max_pages and file_count<max_file_count:
        if check_script_time()>29.5:
            # log(__scriptname__,"Time Limit Break")
            break
        f_count, l_count = get_list(url,max_file_count-file_count,list_mode)
        file_count += f_count
        if l_count==0:
            break
        # next page
        page_count+=1
        url = base_page+jamack_query+"&is_keyword=%s&page=%d" % (newquery,page_count)
    return file_count

def check_ext_pos(str):
    retval = -1
    for ext in sub_ext_str:
        retval=str.lower().find(ext)
        if retval!=-1:
            break
    return retval    

# support compressed content
def decode_content (page):
    encoding = page.info().get("Content-Encoding")    
    if encoding in ('gzip', 'x-gzip', 'deflate'):
        content = page.read()
        if encoding == 'deflate':
            data = StringIO.StringIO(zlib.decompress(content))
        else:
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
        page = data.read()
    else:
        page = page.read()
    return page

def read_url(url):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent',user_agent), ('Accept-Encoding','gzip,deflate')]
    rep = opener.open(url)
    res = decode_content(rep)
    rep.close()
    return res

# 페이지를 파싱해서 파일의 이름과 다운로드 주소를 얻어냄.
def get_files(url):
    ret_list = []
    file_pattern = "<a id=\"goUrl\".+ href=\"([^\"]+)\">(\s+)?<img [^>]+>([^<]+)<"
    content_file = read_url(url)
    files = re.findall(file_pattern,content_file)
    for flink,dummy,name in files:
        ret_list.append([url, name.strip(), base_page+flink.replace("&amp;","&")])
    return ret_list
    
def check_season_episode(str_title, se, ep):
    result = 0
    re_str = ep_expr.search(str_title)
    new_season = ""
    new_episode = ""    
    if re_str:
        new_season = re_str.group(1)
        new_episode = re_str.group(3)
    if new_season.strip()=="":
        new_season="0"
    if new_episode.strip()=="":
        new_episode="0"
    if se=="":
        se="0"
    if ep=="":
        ep="0"
    if int(new_season)==int(se):
        result = 1
        if int(new_episode)==int(ep):
            result = 2
    return result

# 페이지의 내용을 추출해서 링크를 얻어냄. 그리고 링크를 리스트에 추가.
def get_list(url, limit_file, list_mode):
    search_pattern = "<dt><a href=\"([^\"]+)\"[^>]+>(.+)</a>"
    content_list = read_url(url)
    result = 0
    link_count = 0
    # 링크를 파싱
    lists = re.findall(search_pattern,content_list)
    for link, title_name in lists:
        if result<limit_file:
            if check_script_time()>29.5:
                # log(__scriptname__,"Time Limit Break")
                break
            link_count+=1
            plink = base_page + "/subtitles"+ link
            try:
                list_files = get_files(plink)
            except socket.timeout:
                log(__scriptname__,"socket time out")
                continue
            except Exception as e:
                raise

            for furl,name,flink in list_files:
                if use_se_ep_check == "true":
                    if list_mode==1:
                        ep_check = check_season_episode(title_name,item['season'],item['episode'])
                        ep_check += check_season_episode(name,item['season'],item['episode'])
                        if ep_check < 2:
                            continue
                result+=1
                labelf="[KR]"
                listitem = xbmcgui.ListItem(label          = labelf,
                                            label2         = name if use_titlename == "false" else title_name,
                                            iconImage      = "0",
                                            thumbnailImage = ""
                                            )

                listitem.setProperty( "sync", "false" )
                listitem.setProperty( "hearing_imp", "false" )
                listurl = "plugin://%s/?action=download&url=%s&furl=%s&name=%s" % (__scriptid__,
                                                                                urllib2.quote(furl),
                                                                                urllib2.quote(flink),
                                                                                name
                                                                                )

                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=listurl,listitem=listitem,isFolder=False)

    return result, link_count

# 사이트에서 파일을 다운로드.
def download_file(url,furl,name):
    subtitle_list = []
    local_temp_file = os.path.join(__temp__.encode('utf-8'), name)
    # Get cookie
    req1 = urllib2.Request(url,headers={'User-Agent': user_agent})
    res1 = opener2.open(req1)
    # Download File
    req2 = urllib2.Request(furl,headers={'User-Agent': user_agent})
    res2 = opener2.open(req2)
    local_file_handle = open( local_temp_file, "wb" )
    local_file_handle.write(res2.read())
    local_file_handle.close()
    subtitle_list.append(local_temp_file)
    return subtitle_list
 
def search(item):
    filename = os.path.splitext(os.path.basename(item['file_original_path']))[0]
    lastgot = 0
    list_mode = 0
    titlename = ''
    if item['mansearch']:
        lastgot = get_subpages(item['mansearchstr'])
        if use_engkeyhan == "true":
            lastgot += get_subpages(engtypetokor(item['mansearchstr']))
    elif item['tvshow']:
        list_mode = 1
        titlename = item['tvshow']
        lastgot = get_subpages(titlename,1)
    elif item['title'] and item['year']:
        titlename = item['title']
        lastgot = get_subpages(titlename)
    #if lastgot == 0 and list_mode != 1:
    #   lastgot = get_subpages(filename)
    if use_engkor_dict=='true' and len(titlename)>0:
        titlename = find_dict(titlename).strip()
        if len(titlename)>0:
            lastgot += get_subpages(titlename,list_mode)
        
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
        ).encode('ascii', 'ignore')

def get_params(string=""):
    param=[]
    if string == "":
        paramstring=sys.argv[2]
    else:
        paramstring=string
    if len(paramstring)>=2:
        params=paramstring
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]

    return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path of a playing file
    item['3let_language']      = [] #['scc','eng']
    PreferredSub		      = params.get('preferredlanguage')

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        if lang == "Portuguese (Brazil)":
            lan = "pob"
        else:
            lan = xbmc.convertLanguage(lang,xbmc.ISO_639_2)
            if lan == "gre":
                lan = "ell"

    item['3let_language'].append(lan)

    if item['title'] == "":
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    search(item)

elif params['action'] == 'download':
    subs = download_file(urllib2.unquote(params['url']),urllib2.unquote(params['furl']),params['name'])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)


xbmcplugin.endOfDirectory(int(sys.argv[1]))
