"""Offline, explicitly labelled UI fixture. Run: python tests/preview_redesign.py"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from config import Settings, public_config
from models import Character, Artifact, Stat

root=Path(__file__).resolve().parents[1]
app=FastAPI()
app.mount('/static',StaticFiles(directory=root/'static'),name='static')
templates=Jinja2Templates(directory=root/'templates')
settings=Settings(hoyolab={'enabled':True,'game_uid':'899999999'})
names=['Kamisato Ayaka','Kaedehara Kazuha','Raiden Shogun','Nahida','Neuvillette','Furina','Alhaitham','Zhongli','Yelan','Hu Tao','Xiangling','Bennett']
elements=['Cryo','Anemo','Electro','Dendro','Hydro','Hydro','Dendro','Geo','Hydro','Pyro','Pyro','Pyro']
characters=[Character(id=i+1,name=n,element=elements[i],level=90,constellation=0,build_available=i!=11,
    stats=[Stat(label=k,value=v,percent=k in ['CRIT Rate','CRIT DMG','Energy Recharge']) for k,v in [('Max HP',20500),('ATK',2100),('DEF',800),('Elemental Mastery',0),('CRIT Rate',75),('CRIT DMG',220),('Energy Recharge',140)]],
    weapon={'name':'Weapon fixture','level':90,'refinement':1,'rarity':5,'stats':[]},talents={'10001':9,'10002':10,'10003':10},
    artifacts=[Artifact(slot=slot,name='Artifact fixture',set_name='Set fixture',level=20,rarity=5,main_stat=Stat(label='ATK',value=46.6,percent=True),substats=[Stat(label='CRIT Rate',value=10.1,percent=True),Stat(label='CRIT DMG',value=21,percent=True),Stat(label='Elemental Mastery',value=0),Stat(label='DEF',value=23)],crit_value=41.2) for slot in ['Flower of Life','Plume of Death','Sands of Eon','Goblet of Eonothem','Circlet of Logos']]).model_dump() for i,n in enumerate(names)]
for character in characters:
    character['icon']='https://enka.network/ui/UI_AvatarIcon_Ayaka.png'
    character['weapon']['icon']='https://enka.network/ui/UI_EquipIcon_Sword_Amenoma.png'
    for artifact in character['artifacts']:
        artifact['icon']='https://enka.network/ui/UI_RelicIcon_15001_4.png'

def envelope(data,source='enka',stale=False):
    return {'data':data,'meta':{'source':source,'fetched_at':datetime.now(timezone.utc).isoformat(),'stale':stale,'cached':stale,'refresh_after_seconds':0}}

@app.get('/')
@app.get('/showcase')
@app.get('/rankings')
@app.get('/explore')
@app.get('/notes')
@app.get('/settings')
async def page(request:Request):
    response=templates.TemplateResponse(request=request,name='dashboard.html',context={'csrf':'fixture-only','accent':'amber'})
    response.body=response.body.replace(b'<body>',b'<body><p>FIXTURE OFFLINE - data contoh untuk pengujian, bukan akun nyata.</p>')
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['content-length']=str(len(response.body))
    return response

@app.api_route('/api/v1/{path:path}',methods=['GET','POST','PATCH','DELETE'])
async def api(path:str,request:Request):
    if path=='image':
        src=request.query_params.get('src','')
        name='namecard' if 'NameCard' in src else 'weapon' if 'EquipIcon' in src else 'artifact' if 'RelicIcon' in src else 'character'
        return FileResponse(root/'tests'/'assets'/f'{name}.png')
    if path=='config':
        if request.method=='PATCH':
            body=await request.json()
            settings.public_account.uid=body.get('public_account',{}).get('uid',settings.public_account.uid)
            settings.ui.language=body.get('ui',{}).get('language',settings.ui.language)
            settings.ui.accent=body.get('ui',{}).get('accent',settings.ui.accent)
        return {'data':public_config(settings)}
    if path=='auth/hoyolab/test':return {'data':[{'uid':'899999999','nickname':'Fixture privat','server':'Asia'}]}
    if path=='explore':
        from exploration import normalize_exploration
        raw=[dict(id=i,name=name,parent_id=0,world_type=2,exploration_percentage=value,
                  area_exploration_list=[{'name':name+' fixture area','exploration_percentage':value}],
                  offerings=[{'name':'Offering fixture','level':10}])
             for i,name,value in [(1,'Mondstadt',800),(15,'Natlan',700),(17,'Nod-Krai',600)]]
        raw.extend([dict(id=21,name='Windrest Peak',parent_id=0,world_type=2,exploration_percentage=500),
                    dict(id=22,name='Temple of Space',parent_id=0,world_type=1,exploration_percentage=400)])
        raw[2]['area_exploration_list'].extend([{'name':'Lunar Island','exploration_percentage':300},{'name':'Moontide Isle','exploration_percentage':500}])
        return envelope({'uid':settings.hoyolab.game_uid,'nickname':'Fixture privat','server':'Asia',**normalize_exploration(raw)},'hoyolab')
    if path=='notes':
        return envelope({'uid':settings.hoyolab.game_uid,'nickname':'Fixture privat','server':'Asia','resin':{'current':0,'max':200,'full_at':None},'commissions':{'completed':None,'total':4,'reward_claimed':False,'commissions_completed':0,'encounter_claimed':0,'encounter_available':None},'realm_currency':{'current':None,'max':2400},'weekly_discounts_remaining':0,'transformer':None,'expeditions':[{'name':name,'status':'Ongoing','finishes_at':'2026-10-03T00:00:00Z','icon':'https://enka.network/ui/UI_AvatarIcon_Ayaka.png'} for name in names[:5]]},'hoyolab')
    if path=='status':return {'data':{'sources':{'enka':'ok','akasha':'ok','hoyolab':'disabled'}}}
    if path.startswith('showcase/'):
        uid=path.split('/')[1]
        await asyncio.sleep(.3 if uid.endswith('1') else .02)
        return envelope({'profile':{'uid':uid,'nickname':'Fixture '+uid,'signature':'Contoh offline untuk pengujian UI.','level':60,'world_level':9,'icon':None,'namecard':'https://enka.network/ui/UI_NameCardPic_Ayaka_P.png'},'characters':characters})
    if path.startswith('akasha-build/'):
        import copy
        c=copy.deepcopy(characters[int(path.split('/')[-1],16)-1])
        c['weapon']['name']='Akasha snapshot weapon fixture'
        c['source']='akasha'
        c['snapshot_updated_at']='2026-10-01'
        return envelope({'character':c},'akasha')
    if path.startswith('rankings/'):
        if path.endswith('2'):return JSONResponse({'error':{'message':'Fixture: Akasha gagal terhubung'}},503)
        return envelope([{'character_id':i+1,'character':n,'element':elements[i],'category':'Kategori fixture dengan asumsi weapon dan rotasi panjang','weapon':'Weapon asumsi fixture','variant':'Energy Recharge 140%','details':'Data contoh berlabel, bukan ranking akun nyata.','rank':None if i==1 else i,'population':10000,'top_percent':None if i==1 else i/100,'crit_value':None if i==1 else 0 if i==0 else 220,'level':90,'artifact_sets':['Set fixture (4pc)','Other fixture (1pc)'] if i%2==0 else ['Set A fixture (2pc)','Set B fixture (2pc)','Other fixture (1pc)'],'build_hash':f'{i+1:032x}','build_snapshot':characters[i],'icon':'https://enka.network/ui/UI_AvatarIcon_Ayaka.png'} for i,n in enumerate(names)],'akasha')
    return {'data':{}}

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8001)

