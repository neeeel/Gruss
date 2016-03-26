__author__ = 'neil'

''' Functions to deal with Gruss Betting Assistant, opening markets, getting prices etc '''


import win32com.client
import sqlite3
import datetime
import time
import threading


current_market = 0
ba = None
marketOpenAttemptTimeout = 5
conn = None
log_prices = False

def initialise_Db():
    '''
    Connect to DB, clear it, and set up tables ready to store market details
    '''
    global conn,cur
    #conn = sqlite3.connect('markets.sqlite', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    #conn.execute('pragma foreign_keys=ON')
    cur = conn.cursor()
    cur.execute('''DROP TABLE IF EXISTS submarket''')
    cur.execute('''DROP TABLE IF EXISTS market ''')
    cur.execute('''CREATE TABLE market (name TEXT, startTime DATE, ID TEXT UNIQUE PRIMARY KEY)''')
    cur.execute('''CREATE TABLE submarket (name TEXT, market_ID TEXT PRIMARY KEY,parent_ID TEXT, startTime DATE, FOREIGN KEY(parent_ID) REFERENCES market(ID))''')

def get_no_of_runners():
    prices = get_prices()
    t = [p for p in prices if "{NR}" not in p.selection]
    return len(t)

def get_prices():
    '''
    get a list of prices from the currently open market. Its a list of gruss prices objects.
    :return: the list of prices. Or empty list if no prices available
    '''
    prices = ba.getprices
    if prices == None:
        return []
    if prices[0].closed:
        return []
    return prices

def get_prices_as_list():
    prices = get_prices()
    d = {}
    temp_list = []
    for p in prices:
        d = {}
        d["name"]=p.selection
        d["price"] = p.backodds1
        temp_list.append(d)
    return temp_list

def load_horse_racing_markets(countries):
    '''
    Load the days horse racing markets into the Db
    :param countries: A list containing country codes that we want to load, conn is an sqlite3 db
    :return:
    '''
    global conn
    if ba == None or conn == None:
        return
    cur = conn.cursor()
    sports = ba.getsports
    for s in sports:
        if s.sport == "Horse Racing":
            events = ba.getevents(s.sportid)
            for e in events:
                if e.eventname in countries:
                    iterate_through_sport(e,e.eventid,e.eventname,cur)
    conn.commit()

def load_markets(sport):
    global conn
    if ba == None or conn == None:
        return
    sports = ba.getsports
    for s in sports:
        if s.sport == sport:
             iterate_through_sport(None,s.sportid,sport)

def convert_date_format(d):
    '''
    :param d: pywintypes.datetime from gruss COM server
    :return: pywintypes date converted to datetime.datetime format
    '''
    convertedTime = datetime.datetime (
      year=d.year,
      month=d.month,
      day=d.day,
      hour=d.hour,
      minute=d.minute,
      second=d.second
    )
    return convertedTime

def iterate_through_sport(event,parentID,parentName,cur):
    '''
    Iterates through the Gruss event list for a specified sport. exits iteration when the event is an actual market.
    Adds markets and sub markets to a sqlite3 database for future use
    '''
    if event == None:
        events = ba.getevents(parentID)
        for e in events:
            iterate_through_sport(e,e.eventid,e.eventname,cur)
        return
    if event.isMarket:
        if "Stewards Enquiry" not in parentName and "(Dist)" not in parentName and "(AvB)" not in parentName and "(RFC)" not in parentName:
            cur.execute("INSERT OR IGNORE INTO market  VALUES (?,?,?)",(parentName,convert_date_format(event.starttime),str(parentID)))
            cur.execute("INSERT OR IGNORE INTO submarket VALUES (?,?,?,?)",(event.eventname,event.eventid,parentID,convert_date_format(event.starttime)))
            print("Adding ",(parentName,event.eventname,event.eventid,str(parentID)))
        return
    else:
        events = ba.getevents(event.eventID)
        for e in events:
            iterate_through_sport(e,event.eventid,event.eventname,cur)

def open_market(ID,exchange):
    ''' open a market in gruss. Has a 5 second timeout in case gruss fails to load the market.
    :param ID: Market ID to open in gruss
    :param exchange:  Exchange ID, 1 for UK, 2 for AUS
    :return: 0 if market open failed, 1 if market succesfully opened
    '''
    current_market = ba.marketid
    if current_market == ID:
        return 1
    ba.openmarket(ID,exchange)
    start = time.time()
    while time.time() - start <=5:
        if str(ba.marketid) == str(ID):
            prices = ba.getprices
            if prices==None:
                return 0
            if str(prices[0].marketid) == str(ID):
                if prices[0].closed:
                    return 0
                return 1
    return 0

def get_database():
    conn = sqlite3.connect('markets.sqlite')
    conn.execute('pragma foreign_keys=ON')
    return conn

def get_meetings():
    global conn
    cur = conn.cursor()
    races = cur.execute("SELECT name FROM market")
    races = races.fetchall()
    return [r[0].split(" ")[0] for r in races]

def get_movers(minMove):
    pricesDb = sqlite3.connect("pricesDb.sqlite", detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    pricesDb.execute('pragma foreign_keys=ON')
    cur = pricesDb.cursor()
    return[{"name":result[0],"move":result[1]} for result in cur.execute('''SELECT name,move FROM horses WHERE move >= (?)''',(float(minMove),))]
    #return [{"name":result[0],"move":result[1]} for r in result]

def get_win_markets(meeting):
    global conn
    if conn == None:
        return []
    cur = conn.cursor()
    races = cur.execute('''SELECT submarket.starttime as "d [timestamp]" FROM market INNER JOIN submarket ON market.id = submarket.parent_id
                            WHERE market.name LIKE (?) AND submarket.name NOT LIKE "%TBP%" and submarket.name NOT LIKE "%Each%" and submarket.name NOT LIKE "%To Be%"''',("%" + str(meeting) + "%",))
    races = races.fetchall()
    #print(races)
    return [{"time":r[0].strftime("%H:%M:%S")} for r in races]

def start_logging():
    global log_prices
    t = threading.Thread(target = log)
    log_prices = True
    t.start()

def log():
    conn = sqlite3.connect('markets.sqlite', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.execute('pragma foreign_keys=ON')
    cur = conn.cursor()
    pricesDb = sqlite3.connect("pricesDb.sqlite", detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    pricesDb.execute('pragma foreign_keys=ON')
    #pricesDb.execute('''DROP TABLE IF EXISTS horses''')
    pricesCur = pricesDb.cursor()
    pricesCur.execute('''CREATE TABLE IF NOT EXISTS horses (ID INTEGER PRIMARY KEY,
                         name TEXT, data TEXT, move REAL, initialPriceTime DATE )''')
    pricesDb.commit()
    while True: #log_prices == True:
        races = cur.execute('''SELECT market_ID from submarket WHERE submarket.name NOT LIKE "%TBP%" and
                           submarket.name NOT LIKE "%Each%" and submarket.name NOT LIKE "%To Be%"''')
        for r in races:
            print(r[0])
            open_market(str(r[0]),1)
            prices = get_prices()
            for p in prices:
                print("looking for ",p.selection)
                for horse in pricesCur.execute('''SELECT id,name,data,move,initialPriceTime as "d [timestamp]" FROM horses WHERE name=(?)''',(p.selection,)):
                    data = horse[2].split(",")
                    move = 0
                    firstPrice = float(data[0])
                    print("firstprice is ",firstPrice,p.backodds1)
                    if firstPrice !=0:
                        move = (firstPrice - p.backodds1)*100/firstPrice
                    move = "%.2f" % move
                    print("move is ",move)
                    data = horse[2] + "," + str(p.backodds1)
                    pricesCur.execute('''UPDATE horses SET data = (?), move = (?) WHERE ID = (?)''',(data,move,horse[0]))
                    break
                else:
                    print("didnt find it, adding to DB")
                    pricesCur.execute("INSERT OR IGNORE INTO horses  VALUES (NULL,?,?,?,?)",(p.selection,"" + str(p.backodds1),float(0),convert_date_format(datetime.datetime.now())))
            time.sleep(0.5)
        pricesDb.commit()
        time.sleep(600)

try:
    ba = win32com.client.Dispatch("BettingAssistantCom.Application.ComClass")
except Exception as e:
    print("failed",e)
    exit()
conn = sqlite3.connect('markets.sqlite', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
conn.execute('pragma foreign_keys=ON')