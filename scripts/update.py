#!/usr/bin/env python3
"""Daily conservative discovery of yet-to-open concert presales.
Never promote search/news candidates to verified events.
Ticketmaster AU: official Discovery API; other markets: manual verified records.
"""
import csv
import datetime as dt
import email.utils
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'data'/'events.json'
MANUAL=ROOT/'data'/'verified_events.json'
NOW=dt.datetime.now(dt.timezone.utc)
CUTOFF=NOW+dt.timedelta(days=90)
PLATFORMS=['Ticketmaster SG','Ticketmaster AU','ThaiTicketMajor','HK Ticketing','Cityline','Interpark / NOL','Melon Ticket']

def stamp(t):
    try:
        if not t: return None
        t=str(t).replace('Z','+00:00')
        z=dt.datetime.fromisoformat(t)
        if z.tzinfo is None: return None
        return z.astimezone(dt.timezone.utc)
    except (ValueError,TypeError): return None

def iso(t): return t.isoformat(timespec='seconds').replace('+00:00','Z')

def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'OpeningRadar/1.0 (public event index)'})
    with urllib.request.urlopen(req,timeout=18) as response:
        return json.load(response)

def get_bytes(url):
    req=urllib.request.Request(url,headers={'User-Agent':'OpeningRadar/1.0'})
    with urllib.request.urlopen(req,timeout=14) as response:
        return response.read()

def valid(item):
    """Only events with explicit *first* on-sale and reliable verification.
    We never treat 'public on-sale in future' as proof no earlier presale occurred.
    """
    if not item.get('verified') or not item.get('official_url') or not item.get('platform') or not item.get('artist'):
        return False
    first=stamp(item.get('first_sale_utc'))
    return first is not None and NOW < first <= CUTOFF

def load_manual():
    try:
        raw=json.loads(MANUAL.read_text(encoding='utf-8'))
        return raw if isinstance(raw,list) else []
    except (ValueError,OSError): return []

def tm_au():
    api=os.environ.get('TICKETMASTER_API_KEY','').strip()
    if not api: return [],'未配置 API Key',[]
    official=[];candidates=[];num=0
    for page in range(3):
        params={'apikey':api,'countryCode':'AU','classificationName':'music','size':200,'page':page,
                'sort':'onSaleStartDate,asc','onsaleStartDateTime':iso(NOW),
                'onsaleEndDateTime':iso(CUTOFF)}
        url='https://app.ticketmaster.com/discovery/v2/events.json?'+urllib.parse.urlencode(params)
        raw=get_json(url)
        items=raw.get('_embedded',{}).get('events',[])
        num+=len(items)
        for e in items:
            sales=e.get('sales') or {}
            public=stamp((sales.get('public') or {}).get('startDateTime'))
            presales=[stamp(x.get('startDateTime')) for x in sales.get('presales',[]) if x.get('startDateTime')]
            # presale record with malformed time -> cannot confidently verify first sale
            if len(presales)!=len([x for x in sales.get('presales',[]) if x.get('startDateTime')]):
                continue
            starts=[t for t in [public]+presales if t]
            if not starts: continue
            first=min(starts)
            if not (NOW<first<=CUTOFF): continue
            title=e.get('name','')
            if not title: continue
            official_url=e.get('url','')
            if not official_url: continue
            item={'id':'tm-au-'+str(e.get('id','')),'platform':'Ticketmaster AU','artist':title,
                  'title':title,'country':'Australia','timezone':e.get('dates',{}).get('timezone','Australia/Sydney'),
                  'first_sale_utc':iso(first), 'event_date_utc':(e.get('dates',{}).get('start',{}) or {}).get('dateTime'),
                  'official_url':official_url,'verified':True,'verification':'官方 Discovery API 首次销售日期（含 API 可见预售）',
                  'verified_at':NOW.date().isoformat(),'social_score':None}
            official.append(item)
        pages=raw.get('page',{}).get('totalPages',0)
        if not items or page+1>=pages: break
    return official,f'官方 API 更新成功（检索 {num} 场）',candidates

def discover():
    # Public news is only a candidate-generation source, never a sales verification source.
    queries={
      'Ticketmaster SG':'site:ticketmaster.sg concert presale 2027',
      'ThaiTicketMajor':'site:thaiticketmajor.com concert ticket sale 2027',
      'HK Ticketing':'site:hkt.hkticketing.com concert onsale 2027',
      'Cityline':'site:cityline.com concert 優先訂票 2027',
      'Interpark / NOL':'site:nol.yanolja.com ticket 콘서트 티켓오픈 2027',
      'Melon Ticket':'site:ticket.melon.com 콘서트 티켓오픈 2027',
    }
    items=[];statuses={}
    for platform,query in queries.items():
        url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'en','gl':'US','ceid':'US:en'})
        try:
            tree=ET.fromstring(get_bytes(url))
            for t in tree.findall('./channel/item')[:5]:
                title=t.findtext('title','').strip()
                link=t.findtext('link','').strip()
                if title and link: items.append({'platform':platform,'title':title,'url':link})
            statuses[platform]='新闻线索更新；官方需人工核实'
        except Exception as exc:
            statuses[platform]='线索源获取失败：'+type(exc).__name__
    return items[:30],statuses

def main():
    prior={}
    if OUT.exists():
        try: prior=json.loads(OUT.read_text(encoding='utf-8'))
        except ValueError: pass
    coverage={p:'需人工核实' for p in PLATFORMS}
    manual=[e for e in load_manual() if valid(e)]
    # Important: manual records should be periodically re-verified against the official page.
    # If last check older than 7 days, demote rather than maintain confirmed status.
    manual=[] if not manual else [e for e in manual if (stamp(e.get('verified_at')+'T00:00:00Z') and
                                  NOW-stamp(e.get('verified_at')+'T00:00:00Z')<dt.timedelta(days=7))]
    for x in manual:
        coverage[x['platform']]='人工核实资料（有效期7天）'
    au=[]
    try: au,coverage['Ticketmaster AU'],_=tm_au()
    except Exception as exc:
        coverage['Ticketmaster AU']='API 更新失败：'+type(exc).__name__
    candidates,statuses=discover()
    for p,state in statuses.items():
        if coverage[p]=='需人工核实':coverage[p]=state
    all_events={}
    for e in manual+au:
        if valid(e): all_events[e.get('id') or e['official_url']]=e
    candidates=candidates or prior.get('candidates',[])[:20]
    result={'generated_at':iso(NOW),'policy':'only future FIRST onsale dates, next 90 days',
            'events':sorted(all_events.values(),key=lambda x:x['first_sale_utc']),
            'candidates':candidates,'coverage':coverage}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Published',len(result['events']),'verified events and',len(candidates),'unverified candidates')

if __name__=='__main__': main()
