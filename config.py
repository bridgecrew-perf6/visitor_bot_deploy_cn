# -*- coding: utf-8 -*-

import time
import schedule
import os
import json
import threading

from whoosh import index
from whoosh.index import create_in
from whoosh.fields import *
from whoosh.qparser import QueryParser, OrGroup
from whoosh import qparser

from common import *

BOT_SRC_DIR = "bot_resources"
# 默认返回大小
default_size = 10

bot_intents_dict = {}
bot_priorities = {}
bot_recents = {}
bot_frequency = {}

bot_searcher = {}
bot_qp_or = {}
bot_qp_and = {}

for bot_na in os.listdir(BOT_SRC_DIR):
    INTENT_FILE = os.path.join(BOT_SRC_DIR, bot_na, "intents.txt")
    intents_dict = {}
    for intent in read_file(INTENT_FILE):
        intent_pro = pre_process(intent)
        intents_dict[intent_pro] = intent

        intent_pinyin = get_pinyin(intent_pro)
        intents_dict[intent_pinyin] = intent

    bot_intents_dict[bot_na] = intents_dict

    # 加载whoosh索引文件
    index_dir = os.path.join(BOT_SRC_DIR, bot_na, "index")
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)

        schema = Schema(content=TEXT(stored=True))
        ix = create_in(index_dir, schema)
        writer = ix.writer()
        for line in intents_dict.keys():
            writer.add_document(content=line)
        writer.commit()
    else:
        ix = index.open_dir(index_dir)
    searcher = ix.searcher()
    bot_searcher[bot_na] = searcher

    qp_or = QueryParser("content", ix.schema, group=OrGroup)
    qp_or.add_plugin(qparser.FuzzyTermPlugin())
    bot_qp_or[bot_na] = qp_or

    qp_and = QueryParser("content", ix.schema)
    qp_and.add_plugin(qparser.FuzzyTermPlugin())
    bot_qp_and[bot_na] = qp_and
    print(bot_na, "whoosh index finished building...")

    # 加载priority文件，越top优先级越高
    PRIORITY_FILE = os.path.join(BOT_SRC_DIR, bot_na, "priority.txt")
    priorities = read_file(PRIORITY_FILE)
    bot_priorities[bot_na] = priorities
    print(bot_na, "priority file finished loading...")

    # 读取recent文件，越top优先级越高
    RECENT_FILE = os.path.join(BOT_SRC_DIR, bot_na, "recent.txt")
    if not os.path.exists(RECENT_FILE):
        recents = []
    else:
        recents = read_file(RECENT_FILE)
    bot_recents[bot_na] = recents
    print(bot_na, "recent file finished loading...")

    # 读取frequency文件
    FREQUENCY_FILE = os.path.join(BOT_SRC_DIR, bot_na, "frequency.json")
    if not os.path.exists(FREQUENCY_FILE):
        frequency = {}
    else:
        with open(FREQUENCY_FILE, encoding="utf-8") as f:
            frequency = json.load(f)
    bot_frequency[bot_na] = frequency
    print(bot_na, "frequency file finished loading...")


# 每天写入资源文件
def run_resources():
    for _bot_name_ in os.listdir(BOT_SRC_DIR):
        print(_bot_name_, 'starting writing resource files...')
        write_lines(os.path.join(BOT_SRC_DIR, _bot_name_, "recent.txt"), bot_recents[_bot_name_])
        open_file(os.path.join(BOT_SRC_DIR, _bot_name_, "frequency.json"), mode='w').write(
            json.dumps(bot_frequency[_bot_name_], ensure_ascii=False))


# 每30天reset排序因子
def run_resort():
    for bot_n in os.listdir(BOT_SRC_DIR):
        bot_recents[bot_n] = []
        bot_frequency[bot_n] = {}

        recent_file_path = os.path.join(BOT_SRC_DIR, bot_n, "recent.txt")
        freq_file_path = os.path.join(BOT_SRC_DIR, bot_n, "frequency.json")
        if os.path.exists(recent_file_path):
            os.remove(recent_file_path)
        if os.path.exists(freq_file_path):
            os.remove(freq_file_path)


schedule.every().day.do(run_resources)
schedule.every(30).days.do(run_resort)


# 多线程调度
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


threading.Thread(target=run_schedule).start()
