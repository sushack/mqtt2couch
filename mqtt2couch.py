#!/usr/bin/env python

import json
import logging
import logging.config
import sys

from cloudant.client import Client, Database
import pika
import yaml

if len(sys.argv) != 2:
    sys.exit("usage: %s config.yaml" % sys.argv[0])

stream = open(sys.argv[1], 'r')
config = yaml.load(stream)

amqp_config = config["amqp"]
cloudant_config = config["cloudant"]
logging_config = config["logging"]

logging.config.dictConfig(logging_config)
log = logging.getLogger('collector')

connection = pika.BlockingConnection(pika.ConnectionParameters(host=amqp_config["host"]))
channel = connection.channel()

channel.exchange_declare(exchange='amq.topic', type='topic', durable=True)

result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange='amq.topic', queue=queue_name, routing_key=amqp_config["routing_key"])

client = Client(cloudant_config["url"], username=cloudant_config["user"], password=cloudant_config["password"])
database = Database(cloudant_config["db"], client)

def callback(ch, method, properties, body):
    log.debug("%r: %r", method.routing_key, body)
    data = json.loads(body)
    database.create_document(**data)

channel.basic_consume(callback, queue=queue_name, no_ack=True)
channel.start_consuming()
