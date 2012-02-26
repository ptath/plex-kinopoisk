# -*- coding: utf-8 -*- 
import datetime, re, time, unicodedata

# Разные страницы сайта
KINOPOISK_BASE = 'http://www.kinopoisk.ru/'
KINOPOISK_MAIN = 'http://www.kinopoisk.ru/level/1/film/%s/'
KINOPOISK_PEOPLE = 'http://www.kinopoisk.ru/level/19/film/%s/'
KINOPOISK_STUDIO = 'http://www.kinopoisk.ru/level/91/film/%s/'
KINOPOISK_POSTERS = 'http://www.kinopoisk.ru/level/17/film/%s/page/%d/'
KINOPOISK_ART = 'http://www.kinopoisk.ru/level/13/film/%s/page/%d/'

# Страница поиска
KINOPOISK_SEARCH = 'http://www.kinopoisk.ru/index.php?first=no&kp_query=%s'

# Рейтинги
DEFAULT_MPAA = u'R'
MPAA_AGE = {u'G': 0, u'PG': 11, u'PG-13': 13, u'R': 16, u'NC-17': 17}

# Русские месяца, пригодится для определения дат
RU_MONTH = {u'января': '01', u'февраля': '02', u'марта': '03', u'апреля': '04', u'мая': '05', u'июня': '06', u'июля': '07', u'августа': '08', u'сентября': '09', u'октября': '10', u'ноября': '11', u'декабря': '12'}

# Под кого маскируемся =)
UserAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/534.53.11 (KHTML, like Gecko) Version/5.1.3 Safari/534.53.10'

def Start():
  HTTP.CacheTime = CACHE_1DAY
  
class KinopoiskAgent(Agent.Movies):
  name = 'KinoPoisk'
  languages = [Locale.Language.Russian]
  
  # Функция для получения html-содержимого
  def httpRequest(self, url):
    time.sleep(1)
    res = None
    for i in range(3):
      try: 
        res = HTTP.Request(url, headers = {'User-agent': UserAgent, 'Accept': 'text/html'})
      except: 
        Log("Error hitting HTTP url:", url)
        time.sleep(1)
    return res
  
  # Функция преобразования html-кода в xml-код    
  def XMLElementFromURLWithRetries(self, url, code_page = None):
    res = self.httpRequest(url)
    if res:
      if code_page:
        res = str(res).decode(code_page)
      return HTML.ElementFromString(res)
    return None
  
  # Функция для замены специальных символов
  def replace_gomno(self, text_):
    res = text_.replace(u'\x85', u'...')
    res = res.replace(u'\x97', u'-')
    return res
  
  # Начало собственно поиска  
  def search(self, results, media, lang):
   
    # Кодируем в понятный для сайта вид название фильма
    normalizedName = media.name.decode('utf-8')
    normalizedName = unicodedata.normalize('NFC', normalizedName)
    normalizedName = String.Quote(normalizedName.encode('cp1251'),True)
    
    # Получаем страницу поиска
    page =  self.XMLElementFromURLWithRetries(KINOPOISK_SEARCH % normalizedName)
    if page:
      
      # Если страница получена, берем с нее перечень всех названий фильмов
      info_buf = page.xpath(u'//self::div[@class="info"]/p[@class="name"]/a[contains(@href,"/level/1/film/")]/..')
      score = 99
      
      # Если не нашли там текст названия, значит сайт сразу дал нам страницу с фильмом (хочется верить =)
      if not len(info_buf):
        try:
          title = page.xpath('//h1[@class="moviename-big"]/text()')[0].strip()
          id = re.search('\/film\/(.+?)\/', page.xpath('//a[contains(@href,"/level/19/film/")]/attribute::href')[0]).groups(1)[0]
          year = page.xpath('//a[contains(@href,"year")]/text()')[0].strip()

          results.Append(MetadataSearchResult(id = id, name  = title, year = year, lang  = lang, score = score))              
          score = score - 4

        except:
          pass
      
      # Если    
      else:
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
            
    # Сортируем результаты
    results.Sort('year', descending=True)
  
  # Обновляем данные о фильме в медиатеке  
  def update(self, metadata, media, lang):
    
    # Название
    metadata.title = media.title
    	
    if metadata.id:
	  # Получаем страницу фильма
      page =  self.XMLElementFromURLWithRetries(KINOPOISK_MAIN % metadata.id)
      if page:
        
        #Сброс рейтинга MPAA
        metadata.content_rating = None
        
        # Актёры
        lactors = page.xpath('//td[@class="actor_list"]/div/span')
        metadata.roles.clear()
        for inf_ in lactors:
          info_buf = inf_.xpath('./a[contains(@href,"/level/4/people/")]/text()')
          if len(info_buf):
            for actor in info_buf:
              if actor != u'...':
                role = metadata.roles.new()
                role.actor = actor
 
        # Название на оригинальном языке
        otitle = page.xpath('//span[@style="color: #666; font-size: 13px"]/text()')
        if len(otitle):
          otitle = ' '.join(otitle)
          otitle = self.replace_gomno(otitle)
          metadata.original_title = otitle.strip('- ')
      
        info = page.xpath('//table[@class="info"]/tr')
        for inf_ in info:
          info_buf =  inf_.xpath('./td[@class="type"]/text()')
          if len(info_buf) == 1:
          
          # Режиссер
            if info_buf[0] == u'режиссер':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                for director in info_buf:
                  if director != u'...':
                    metadata.directors.add(director)
          
          # Год
            if info_buf[0] == u'год':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                metadata.year = int(info_buf[0])
          
          # Сценаристы
            if info_buf[0] == u'сценарий':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                for writer in info_buf:
                  if writer != u'...':
                    metadata.writers.add(writer)
          
          # Жанры
            elif info_buf[0] == u'жанр':
              info_buf = inf_.xpath('.//a/text()')
              if len(info_buf):
                for genre in info_buf:
                  if genre != u'...':
                    metadata.genres.add(genre)
          
          # Слоган
            elif info_buf[0] == u'слоган':
              info_buf = inf_.xpath('./td[@style]/text()')
              if len(info_buf):
                info_buf = ' '.join(info_buf)
                info_buf = self.replace_gomno(info_buf)
                metadata.tagline = info_buf.strip('- ')
          
          # Рейтинг MPAA
            elif info_buf[0] == u'рейтинг MPAA':
              info_buf = inf_.xpath('.//a/img/attribute::src')
              if len(info_buf) == 1:
                info_buf = re.search('\/([^/.]+?)\.gif$',info_buf[0])
                if info_buf:
                  metadata.content_rating = info_buf.groups(1)[0]

          # Время
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
              if len(info_buf):
                try:
                  (dd, mm, yy) = info_buf[0].split()
                  if len(dd) == 1: dd = '0' + dd 
                  mm = RU_MONTH[mm]
                  metadata.originally_available_at = Datetime.ParseDate(yy+'-'+mm+'-'+dd).date()
                except:
                  pass
            

        # Рейтинг MPAA defaults
        if (metadata.content_rating) == 'None':
          metadata.content_rating = DEFAULT_MPAA
        # Рейтинг MPAA age
        try:
          metadata.content_rating_age = MPAA_AGE[metadata.content_rating]
        except:
          pass
        
    # Рейтинг
        info_buf = page.xpath('//form[@class="rating_stars"]/div[@id="block_rating"]//a[@href="/level/83/film/'+metadata.id+'/"]/span/text()')
        if len(info_buf):
          try:
            metadata.rating = float(info_buf[0])
          except:
            pass
          
    # Описание      
        info_buf = page.xpath('//div[@class="block_left_padtop"]/table/tr/td/table/tr/td/span[@class="_reachbanner_"]/div/text()')
        if len(info_buf):
          info_buf = ' '.join(info_buf)
          info_buf = self.replace_gomno(info_buf)
          metadata.summary = info_buf.strip()
     
    # Постеры
      page = self.XMLElementFromURLWithRetries(KINOPOISK_POSTERS % (metadata.id, 1))
      pages = []
      
      # Получение адресов постеров
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
      
      # Последняя надежда — на всякий случай забираем картинку низкого качества
      try:
        imageUrl = 'http://st.kinopoisk.ru/images/film/' + metadata.id + '.jpg'
        name = imageUrl.split('/')[-1]
        metadata.posters[name] = Proxy.Media(HTTP.Request(imageUrl), sort_order = 1)
      except:
        pass
          
    # Задники
      page = self.XMLElementFromURLWithRetries(KINOPOISK_ART % (metadata.id, 1))
      pages = []
      
      # Получение адресов задников
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
          # Берем только первую студию
          metadata.studio = info_buf[0].strip() 