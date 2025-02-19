import schedule
import time
import logging
import config
import json
import os
import argparse
import sys

from datetime import date
from notifier import sendNotification
from crawler.yogyaonline import hotDeals as yogyaPromo, getCategories as yogyaCategories
from crawler.klikindomaret import promosiMingguIni as indoPromo, getDataCategories as indoCategories
from crawler.alfagift import catalog as alfaCatalog
from config import DATA_DIR

import uvicorn

from fastapi import FastAPI
from routes import root, belanja

app = FastAPI(redoc_url=None, docs_url=None)

app.include_router(root.router)
app.include_router(belanja.router)
#app.include_router(yogyaonline.router)

logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

def dataScrap(target: str, itemsType: str):
    TODAY_STRING = date.today().strftime("%Y-%m-%d")
    if itemsType == "":
        itemsType = "all"
    cData = {}
    if target == 'yogyaonline':
        if itemsType == "all":
            cData = [
                {'data': yogyaCategories(), 'date': TODAY_STRING, 'type': 'catalog' },
                {'data': yogyaPromo(), 'date': TODAY_STRING, 'type': 'promo'}
            ]
        elif itemsType == 'promo':
            cData = {'data': yogyaPromo(), 'date': TODAY_STRING }
        elif itemsType == 'catalog':
            cData = {'data': yogyaCategories(), 'date': TODAY_STRING }
    
    if target == 'klikindomaret':
        if itemsType == "all":
            cData = [
                {'data': indoPromo(), 'date': TODAY_STRING, 'type': 'promo' },
                {'data': indoCategories(), 'date': TODAY_STRING, 'type': 'catalog' }
            ]
        elif itemsType == "promo":
            cData = {'data': indoPromo(), 'date': TODAY_STRING }
        elif itemsType == "catalog":
            cData = {'data': indoCategories(), 'date': TODAY_STRING }

    if target == 'alfagift':
        if itemsType == "catalog":
            cData = {'data': alfaCatalog(), 'date': TODAY_STRING }

    if not itemsType == "all":

        file_object = open(f'{DATA_DIR}/{target}/{itemsType}/{TODAY_STRING}.json', 'w+')
        file_object.write(json.dumps(cData))

        # Backup for notifier, remove this after notifier is fixed
        if target == "yogyaonline":
            file_object = open(f'{DATA_DIR}/{TODAY_STRING}.json', 'w+')
            file_object.write(json.dumps(cData))

        logging.info(f"== scrapping {target} success, saved to {DATA_DIR}/{target}/{itemsType}/{TODAY_STRING}.json")
        
    else:
        for itemData in cData:
            file_object = open(f'{DATA_DIR}/{target}/{itemData["type"]}/{TODAY_STRING}.json', 'w+')
            file_object.write(json.dumps(itemData))

            logging.info(f"== scrapping {target} success, saved to {DATA_DIR}/{target}/{itemData['type']}/{TODAY_STRING}.json")
        if target == "yogyaonline":
            # Backup for notifier, remove this after notifier is fixed
            file_object = open(f'{DATA_DIR}/{TODAY_STRING}.json', 'w+')
            file_object.write(json.dumps(cData))

    return True

def jobScrapper(target: str = 'all', itemsType: str = 'all'):
    logging.info(f"=== worker target to {target} with scraping mode {itemsType} is running")

    if target == 'all':
        for itemTarget in ['yogyaonline', 'alfagift', 'klikindomaret']:
            job = dataScrap(itemTarget)
            if not job:
                logging.error("Fail Scrapping")
    else:
        job = dataScrap(target, itemsType)
        if not job:
            logging.error("Fail Scrapping")

if __name__ == "__main__":
    REQUIREMENT_DIR = [
        f"{DATA_DIR}",
        f"{DATA_DIR}/alfagift",
        f"{DATA_DIR}/alfagift/catalog",
        f"{DATA_DIR}/alfagift/promo",
        f"{DATA_DIR}/klikindomaret",
        f"{DATA_DIR}/klikindomaret/promo",
        f"{DATA_DIR}/klikindomaret/catalog",
        f"{DATA_DIR}/yogyaonline",
        f"{DATA_DIR}/yogyaonline/promo",
        f"{DATA_DIR}/yogyaonline/catalog"
    ]

    for dirr in REQUIREMENT_DIR:
        if not os.path.isdir(dirr):
            os.mkdir(dirr)

    parser = argparse.ArgumentParser(description='Process the BiBiT Job')
    parser.add_argument('command', 
        metavar ='command', 
        type=str, 
        choices=['notif', 'scrap', 'do.notif', 'do.scrap', 'web.api'],
        help='a command to run the bibit Job, the choices is `notif`, `scrap`, `do.notif` and `do.scrap` ')
    
    parser.add_argument('--target', 
        metavar ='all, yogyaonline, klikindomaret, alfagift', 
        type=str, 
        default='all',
        choices=['all', 'yogyaonline', 'klikindomaret', 'alfagift'],
        help='choices the target to be scrapped')

    parser.add_argument('--scrap', 
        metavar ='all, promo, catalog', 
        type=str,
        default='catalog',
        choices=['all', 'promo', 'catalog'],
        help='choices the items type you want to get')

    args = parser.parse_args()
    
    logging.info(f"=== The scrapper for {args.target} in page {args.scrap} will be running for")

    if args.command == 'notif':
        for PRIME_TIME in config.PRIME_TIME:
            logging.info(f"=== notification worker at {PRIME_TIME} is queued")
            schedule.every().day.at(PRIME_TIME).do(sendNotification)

    if args.command == 'scrap':
        for SCRAPPING_TIME in config.SCRAPPING_TIME:
            logging.info(f"=== scrapper worker at {SCRAPPING_TIME} is queued")
            schedule.every().day.at(SCRAPPING_TIME).do(jobScrapper, target=args.target, itemsType=args.scrap)

    if args.command == 'do.notif':
        sendNotification()
        sys.exit(1)

    if args.command == 'do.scrap':
        jobScrapper(args.target, args.scrap)
        sys.exit(1)

    if args.command == 'web.api':
        uvicorn.run('main:app', host='0.0.0.0', port=8000, log_level="info", reload=True)
        sys.exit()

    while True:
        schedule.run_pending()
        time.sleep(2)
