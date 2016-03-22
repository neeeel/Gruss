__author__ = 'neil'

''' Functions to deal with Gruss Betting Assistant, opening markets, getting prices etc '''


import win32com.client
import sqlite3
import datetime
import time


current_market = 0
ba = None
marketOpenAttemptTimeout = 5
conn = None
cur = None


def get_no_of_runners():
    prices = get_prices()
    count = 0
    for p in prices:
        print(p.selection)
        if "(NR)" not in p.selection:
            count += 1
    return count


def get_prices():
    '''
    get a list of prices from the currently open market. Its a list of gruss prices objects.
    :return: the list of prices. Or empty list if no prices available
    '''
    prices = ba.getprices
    if prices == None or prices[0].closed:
        return []
    return prices

def load_horse_racing_markets(countries):
    '''
    Load the days horse racing markets into the Db
    :param countries: A list containing country codes that we want to load
    :return:
    '''
    global conn
    if ba == None or conn == None:
        return
    sports = ba.getsports
    for s in sports:
        if s.sport == "Horse Racing":
            events = ba.getevents(s.sportid)
            for e in events:
                if e.eventname in countries:
                    iterate_through_sport(e,e.eventid,e.eventname)
    conn.commit()

def load_markets(sport):
    global conn
    if ba == None or conn == None:
        return
    sports = ba.getsports
    for s in sports:
        if s.sport == sport:
             iterate_through_sport(None,s.sportid,sport)
    conn.commit()

def initialise_Db():
    '''
    Connect to DB, clear it, and set up tables ready to store market details
    '''
    global conn,cur
    conn = sqlite3.connect('markets.sqlite')
    conn.execute('pragma foreign_keys=ON')
    cur = conn.cursor()
    cur.execute('''DROP TABLE IF EXISTS submarket''')
    cur.execute('''DROP TABLE IF EXISTS market ''')
    cur.execute('''CREATE TABLE market (name TEXT, startTime DATE, ID TEXT UNIQUE PRIMARY KEY)''')
    cur.execute('''CREATE TABLE submarket (name TEXT, market_ID TEXT PRIMARY KEY,parent_ID TEXT, startTime DATE, FOREIGN KEY(parent_ID) REFERENCES market(ID))''')

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

def iterate_through_sport(event,parentID,parentName):
    '''
    Iterates through the Gruss event list for a specified sport. exits iteration when the event is an actual market.
    Adds markets and sub markets to a sqlite3 database for future use
    '''
    global cur
    if event == None:
        events = ba.getevents(parentID)
        for e in events:
            iterate_through_sport(e,e.eventid,e.eventname)
        return
    if event.isMarket:
        cur.execute("INSERT OR IGNORE INTO market  VALUES (?,?,?)",(parentName,convert_date_format(event.starttime),str(parentID)))
        cur.execute("INSERT OR IGNORE INTO submarket VALUES (?,?,?,?)",(event.eventname,event.eventid,parentID,convert_date_format(event.starttime)))
        print("Adding ",(parentName,event.eventname,event.eventid,str(parentID)))
        return
    else:
        events = ba.getevents(event.eventID)
        for e in events:
            iterate_through_sport(e,event.eventid,event.eventname)

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

try:
    ba = win32com.client.Dispatch("BettingAssistantCom.Application.ComClass")
except Exception as e:
    print("failed",e)
    exit()



