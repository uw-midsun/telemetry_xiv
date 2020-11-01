# This script recieves CAN data,sends it to FRED with MQTT,
# and stores the data locally
# This should be run by the RPI for the telemetry system
# Make sure that DynamoDB is set up and link the key in a .env file

# If you are running this script with virtual CAN
# ensure that it is set up first
# You can run the below commands
# sudo modprobe vcan
# sudo ip link add dev vcan0 type vcan
# sudo ip link set up vcan0

import asyncio
import aioboto3
import boto3
import cantools
import can
import csv
from datetime import datetime
from dotenv import load_dotenv
import json
import os
import paho.mqtt.client as mqtt
import websockets

load_dotenv()

can_bus = can.interface.Bus('vcan0', bustype='socketcan')
db = cantools.database.load_file('system_can.dbc')

broker = "mqtt.sensetecnic.com"
port = 1883
client = mqtt.Client(client_id=os.getenv("MQTT_CLIENT_ID"))
client.username_pw_set(username=os.getenv("MQTT_USERNAME"),
                       password=os.getenv("MQTT_PASSWORD"))

dynamodb = boto3.resource('dynamodb')
dynamo_db_table = dynamodb.Table('can_messages')

# Write new line and header
with open('can_messages.csv', 'a', newline='') as csvfile:
    fieldnames = ['datetime', 'name', 'sender', 'data']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writerow({'datetime': '', 'name': '', 'sender': '', 'data': ''})
    writer.writeheader()


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected")
    else:
        print("Bad connection returned code=", rc)


def connect():
    client.on_connect = on_connect
    client.connect(broker, port, 60)
    client.loop_start()


async def decode_and_send(websocket, path):
    while True:
        message = can_bus.recv()
        decoded = db.decode_message(message.arbitration_id, message.data)

        time = str(datetime.fromtimestamp(message.timestamp))
        name = db.get_message_by_frame_id(message.arbitration_id).name
        sender = db.get_message_by_frame_id(message.arbitration_id).senders[0]
        can_decoded_data = {'datetime': time, 'name': name,
                            'sender': sender, 'data': decoded}

        # Send data out to a CSV, FRED, and DynamoDB
        write_to_csv(can_decoded_data)
        client.publish("accounts/midnight_sun/CAN",
                    payload=json.dumps(can_decoded_data),qos=2)
        await websocket.send(str(can_decoded_data))
        async with aioboto3.resource('dynamodb', region_name='us-east-1') as resource:
            dynamo_db_table = await resource.Table('can_messages')
            await dynamo_db_table.put_item(Item=can_decoded_data)


def write_to_csv(can_decoded_data):
    with open('can_messages.csv', 'a', newline='') as csvfile:
        fieldnames = ['datetime', 'name', 'sender', 'data']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(can_decoded_data)


def main():
    connect()
    start_server = websockets.serve(decode_and_send, "localhost", 8765)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
