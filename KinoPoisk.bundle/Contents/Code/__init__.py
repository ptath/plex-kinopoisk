# -*- coding: utf-8 -*- 
import datetime, re, time, unicodedata

KINOPOISK_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_SEARCH = 'http://www.kinopoisk.ru/index.php?first=no&kp_query=%s'
KINOPOISK_MAIN = 'http://www.kinopoisk.ru/level/1/film/%s/'
KINOPOISK_PEOPLE = 'http://www.kinopoisk.ru/level/19/film/%s/'
KINOPOISK_STUDIO = 'http://www.kinopoisk.ru/level/91/film/%s/'
KINOPOISK_POSTERS = 'http://www.kinopoisk.ru/level/17/film/%s/page/%d/'
KINOPOISK_ART = 'http://www.kinopoisk.ru/level/13/film/%s/page/%d/'
DEFAULT_MPAA = u'R'
MPAA_AGE = {u'G': 0, u'PG': 11, u'PG-13': 13, u'R': 16, u'NC-17': 17}

RU_MONTH = {u'января': '01', u'февраля': '02', u'марта': '03', u'апреля': '04', u'мая': '05', u'июня': '06', u'июля': '07', u'августа': '08', u'сентября': '09', u'октября': '10', u'ноября': '11', u'декабря': '12'}

UserAgent = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us) AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16'

def Start():
  HTTP.CacheTime = CACHE_1DAY
  
class KinopoiskAgent(Agent.Movies):
  name = 'KinoPoisk'
  # Надо облагородить, а то так и отображается — ru
  languages = [Locale.Language.Russian]
  
  def httpRequest(self, url):
    time.sleep(1)
    res = None
    for i in range(5):
      try: 
        res = HTTP.Request(url, headers = {'User-agent': UserAgent})
      except: 
        Log("Error hitting HTTP url:", url)
        time.sleep(1)
        
    return res
      
  def XMLElementFromURLWithRetries(self, url, code_page = None):
    res = self.httpRequest(url)
    if res:
      if code_page:
        res = str(res).decode(code_page)
      return HTML.ElementFromString(res)
    return None

  def replace_gomno(self, text_):
   # блядская замена 3-х точек и т.д.
    res = text_.replace(u'\x85', u'...')
    res = res.replace(u'\x97', u'-')
    return res

  def search(self, results, media, lang):
   
    normalizedName = media.name.decode('utf-8')
    normalizedName = unicodedata.normalize('NFC', normalizedName)
    normalizedName = String.Quote(normalizedName.encode('cp1251'),True)
    
    page =  self.XMLElementFromURLWithRetries(KINOPOISK_SEARCH % normalizedName)
    if page:
      info_buf = page.xpath(u'//self::div[@class="info"]/p[@class="name"]/a[contains(@href,"/level/1/film/")]/..')
      score = 99
      if not len(info_buf):
      #Только одна страница
        try:
          title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
          id = re.search('\/film\/(.+?)\/', page.xpath('//a[contains(@href,"/level/19/film/")]/attribute::href')[0]).groups(1)[0]
          year = page.xpath('//a[contains(@href,"year")]/text()')[0].strip()

          results.Append(MetadataSearchResult(id = id, name  = title, year = year, lang  = lang, score = score))              
          score = score - 4

        except:
          pass
          
      else:
      # Нормально
        for td_ in info_buf:
          try:
            # получение ID
            id = re.search('\/film\/(.+?)\/', td_.xpath('./a[contains(@href,"/level/1/film/")]/attribute::href')[0]).groups(1)[0]
    
            title = td_.xpath('.//a[contains(@href,"/level/1/film/")]/text()')[0]
            year = td_.xpath('.//span[@class="year"]/text()')[0]
            #(title, year) = td_.xpath('.//a/text()')
    
            results.Append(MetadataSearchResult(id = id, name  = title, year = year, lang  = lang, score = score))              
            score = score - 4
              
          except:
            pass
            

    results.Sort('year', descending=True)
    
  #
  # 
  #     
  def update(self, metadata, media, lang):

    # Set the title.
    metadata.title = media.title
#    metadata.year = year
	
    if metadata.id:
		# Получаем основную страницу с кинопоиска
      page =  self.XMLElementFromURLWithRetries(KINOPOISK_MAIN % metadata.id)
      if page:
        
        #Сброс рейтинга MPAA
        metadata.content_rating = None
        
        lactors = page.xpath('//td[@class="actor_list"]/span')
        metadata.roles.clear()
        for inf_ in lactors:
          info_buf = inf_.xpath('./a[contains(@href,"/level/4/people/")]/text()')
          if len(info_buf):
            for actor in info_buf:
              if actor != u'...':
                role = metadata.roles.new()
                role.actor = actor
 
        otitle = page.xpath('//span[@style="color: #666; font-size: 13px"]/text()')
        if len(otitle):
          otitle = ' '.join(otitle)
          otitle = self.replace_gomno(otitle)
          metadata.original_title = otitle.strip('- ')
      
        info = page.xpath('//table[@class="info"]/tr')
        for inf_ in info:
          info_buf =  inf_.xpath('./td[@class="type"]/text()')
          if len(info_buf) == 1:
          #Режиссер
            if info_buf[0] == u'режиссер':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                for director in info_buf:
                  if director != u'...':
                    metadata.directors.add(director)
                    Log("======= Director found " + director)
          #Сценаристы
            if info_buf[0] == u'сценарий':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                for writer in info_buf:
                  if writer != u'...':
                    metadata.writers.add(writer)
          #Год
            if info_buf[0] == u'год':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf) == 1:
                metadata.year = int(info_buf[0])
          #Жанры
            elif info_buf[0] == u'жанр':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                for genre in info_buf:
                  if genre != u'...':
                    metadata.genres.add(genre)
          #Слоган
            elif info_buf[0] == u'слоган':
              info_buf = inf_.xpath('./td[@style]/text()')
              if len(info_buf):
                info_buf = ' '.join(info_buf)
                info_buf = self.replace_gomno(info_buf)
                metadata.tagline = info_buf.strip('- ')
          #рейтинг MPAA
            elif info_buf[0] == u'рейтинг MPAA':
              info_buf = inf_.xpath('.//a/img/attribute::src')
              if len(info_buf) == 1:
                info_buf = re.search('\/([^/.]+?)\.gif$',info_buf[0])
                if info_buf:
                  metadata.content_rating = info_buf.groups(1)[0]

          #Время
            elif info_buf[0] == u'время':
              info_buf = inf_.xpath('./td[@class="time"]/text()')
              if len(info_buf) == 1:
                try:
                  metadata.duration = int(info_buf[0].rstrip(u' мин.')) * 60 * 1000
                except:
                  pass
                  
          # Премьера в мире
            elif info_buf[0] == u'премьера (мир)':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf) == 1:
                try:
                  (dd, mm, yy) = info_buf[0].split()
                  if len(dd) == 1: dd = '0' + dd 
                  mm = RU_MONTH[mm]
                  metadata.originally_available_at = Datetime.ParseDate(yy+'-'+mm+'-'+dd).date()
                except:
                  pass
            

        #рейтинг MPAA defaults
        
        if (metadata.content_rating) == 'None':
          metadata.content_rating = DEFAULT_MPAA
        #рейтинг MPAA age
        try:
          metadata.content_rating_age = MPAA_AGE[metadata.content_rating]
        except:
          pass
        
    # Рейтинг
        info_buf = page.xpath('//form[@class="rating_stars"]/div[@id="block_rating"]//a[@href="/level/83/film/'+metadata.id+'/"]/text()')
        if len(info_buf) == 1:
          metadata.rating = float(info_buf[0])
    # Описание      
        info_buf = page.xpath('//div[@class="block_left_padtop"]/table/tr/td/table/tr/td/span[@class="_reachbanner_"]/div/text()')
        if len(info_buf):
          info_buf = ' '.join(info_buf)
          info_buf = self.replace_gomno(info_buf)
          metadata.summary = info_buf.strip()
          
     
    # Постеры
      page =  self.XMLElementFromURLWithRetries(KINOPOISK_POSTERS % (metadata.id, 1))
      pages =[]
      
      # получение урлов
      if page:
        pages.append(page)
        nav = page.xpath('//div[@class="navigator"]/ul/li[@class="arr"]/a')
        if nav:
          nav = nav[-1].xpath('./attribute::href')[0]
          nav = re.search('page\/(\d+?)\/$', nav)
          try:
            for p_i in range(2, int(nav.groups(1)[0]) + 1):
              page =  self.XMLElementFromURLWithRetries(KINOPOISK_POSTERS % (metadata.id, p_i))
              if page:
                pages.append(page)
          except:
            pass
      
      # Получение урлов постеров            
      if len(pages):
        for page in pages:
          info_buf = page.xpath('//table[@class="fotos" or @class="fotos fotos1" or @class="fotos fotos2"]/tr/td/a/attribute::href')
          for imageUrl in info_buf:
           # Получаем страницу с картинкою
            page = self.XMLElementFromURLWithRetries(KINOPOISK_BASE + imageUrl.lstrip('/'))
            imageUrl = page.xpath('//table[@id="main_table"]/tr/td/a/img/attribute::src')
            if len(imageUrl) == 0:
               imageUrl = page.xpath('//table[@id="main_table"]/tr/td/img/attribute::src')
            if len(imageUrl) == 1:
              imageUrl = imageUrl[0]
              name = imageUrl.split('/')[-1]
              if name not in metadata.posters:
                try:
                  metadata.posters[name] = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
                except:
                  pass
          
    # Задники
      page =  self.XMLElementFromURLWithRetries(KINOPOISK_ART % (metadata.id, 1))
      pages =[]
      
      # получение урлов
      if page:
        pages.append(page)
        nav = page.xpath('//div[@class="navigator"]/ul/li[@class="arr"]/a')
        if nav:
          nav = nav[-1].xpath('./attribute::href')[0]
          nav = re.search('page\/(\d+?)\/$', nav)
          try:
            for p_i in range(2, int(nav.groups(1)[0]) + 1):
              page =  self.XMLElementFromURLWithRetries(KINOPOISK_ART % (metadata.id, p_i))
              if page:
                pages.append(page)
          except:
            pass
      
      # Получение урлов задников            
      if len(pages):
        for page in pages:
          info_buf = page.xpath('//table[@class="fotos" or @class="fotos fotos1" or @class="fotos fotos2"]/tr/td/a/attribute::href')
          for imageUrl in info_buf:
           # Получаем страницу с картинкою
            page = self.XMLElementFromURLWithRetries(KINOPOISK_BASE + imageUrl.lstrip('/'))
            imageUrl = page.xpath('//table[@id="main_table"]/tr/td/a/img/attribute::src')
            if len(imageUrl) == 0:
               imageUrl = page.xpath('//table[@id="main_table"]/tr/td/img/attribute::src')
            if len(imageUrl) == 1:
              imageUrl = imageUrl[0]
              name = imageUrl.split('/')[-1]
              if name not in metadata.art:
                try:
                  metadata.art[name] = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
                except:
                  pass

    # Студия
      page = self.XMLElementFromURLWithRetries(KINOPOISK_STUDIO % metadata.id)
      if page:
        info_buf = page.xpath(u'//table/tr/td[b="Производство:"]/../following-sibling::tr/td/a/text()')
        if len(info_buf):
          # Берем 1 студию
          metadata.studio = info_buf[0].strip()
 
 
    #metadata.trivia = ""
    #metadata.quotes = ""
    #metadata.originally_available_at = Datetime.ParseDate(info_dict["Release Date"].text.strip().split('(')[0]).date()
    #metadata.tags.add(tag)
    
