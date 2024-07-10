import json
import pika
import logging
import requests

from typing import List
from sqlalchemy.sql import func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models.models import AwslProducer, Mblog, Pic
from .config import CHUNK_SIZE, WB_URL_PREFIX, settings, WB_COOKIE

engine = create_engine(settings.db_url, pool_size=100)
DBSession = sessionmaker(bind=engine)


_logger = logging.getLogger(__name__)

# MQ
channel = None


def check_pika_channel() -> None:
    global channel
    if not settings.pika_url or not settings.bot_queue:
        return
    if channel is not None and channel.is_open:
        return
    connection = pika.BlockingConnection(pika.URLParameters(settings.pika_url))
    channel = connection.channel()
    channel.queue_declare(queue=settings.bot_queue, durable=True)


class Tools:

    @staticmethod
    def wb_get(url) -> dict:
        try:
            res = requests.get(url=url, headers={
                "cookie": WB_COOKIE.format(settings.cookie_sub)
            })
            return res.json()
        except Exception as e:
            _logger.exception(e)
            return None

    @staticmethod
    def select_max_id(uid: str) -> int:
        session = DBSession()
        try:
            mblog = session.query(func.max(Mblog.id)).filter(
                Mblog.uid == uid).one()
        finally:
            session.close()
        return int(mblog[0]) if mblog and mblog[0] else 0

    @staticmethod
    def update_max_id(uid: str, max_id: int) -> None:
        session = DBSession()
        try:
            session.query(AwslProducer).filter(
                AwslProducer.uid == uid
            ).update({
                AwslProducer.max_id: str(max_id)
            })
            session.commit()
        finally:
            session.close()

    @staticmethod
    def update_mblog(awsl_producer: AwslProducer, wbdata: dict) -> str:
        if not wbdata:
            return ""
        origin_wbdata = wbdata.get("retweeted_status") or wbdata
        if not origin_wbdata.get("user"):
            return ""
        _logger.info("awsl update db mblog awsl_producer=%s id=%s mblogid=%s" %
                     (awsl_producer.name, wbdata["id"], wbdata["mblogid"]))
        session = DBSession()
        try:
            mblog = Mblog(
                id=wbdata["id"],
                uid=awsl_producer.uid,
                mblogid=wbdata["mblogid"],
                re_id=origin_wbdata["id"],
                re_mblogid=origin_wbdata["mblogid"],
                re_user_id=origin_wbdata["user"]["id"],
                re_user=json.dumps(origin_wbdata["user"])
            )
            session.add(mblog)
            session.commit()
        finally:
            session.close()

        return origin_wbdata["mblogid"]

    @staticmethod
    def update_pic(wbdata: dict, re_wbdata: dict) -> None:
        if not re_wbdata:
            return
        pic_infos = re_wbdata.get("pic_infos", {})
        session = DBSession()
        try:
            for sequence, pic_id in enumerate(re_wbdata.get("pic_ids", [])):
                session.add(Pic(
                    awsl_id=wbdata["id"],
                    sequence=sequence,
                    pic_id=pic_id,
                    pic_info=json.dumps(pic_infos[pic_id]),
                ))
            session.commit()
        finally:
            session.close()

    @staticmethod
    def find_all_awsl_producer() -> List[AwslProducer]:
        session = DBSession()
        try:
            awsl_producers = session.query(
                AwslProducer
            ).filter(
                AwslProducer.in_verification.isnot(True)
            ).filter(
                AwslProducer.deleted.isnot(True)
            ).all()
        finally:
            session.close()
        return awsl_producers

    @staticmethod
    def send2bot(awsl_producer: AwslProducer, re_mblogid: str, re_wbdata: dict) -> None:
        try:
            check_pika_channel()
            if not channel:
                return
            wb_url = WB_URL_PREFIX.format(
                re_wbdata["user"]["id"], re_wbdata["mblogid"])
            pic_infos = re_wbdata.get("pic_infos", {})
            pic_ids = re_wbdata.get("pic_ids", [])
            source_screen_name = re_wbdata.get(
                "user", {}
            ).get(
                "screen_name"
            ) or awsl_producer.name
            for i in range(0, len(pic_ids), CHUNK_SIZE):
                channel.basic_publish(
                    exchange='',
                    routing_key=settings.bot_queue,
                    body=json.dumps({
                        "wb_url": wb_url,
                        "awsl_producer": source_screen_name,
                        "pics": [
                            pic_infos[pic_id]["original"]["url"]
                            for pic_id in pic_ids[i:i+CHUNK_SIZE]
                        ]
                    }),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                _logger.info("send bot_queue %s", pic_ids[i:i+CHUNK_SIZE])
            _logger.info("send to bot_queue re_mblogid %s", re_mblogid)
        except Exception as e:
            _logger.exception(e)
