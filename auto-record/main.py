import os
import json
import logging
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError, InvalidSignatureError
from linebot.models import FollowEvent, MessageEvent, JoinEvent, MemberJoinedEvent, MemberLeftEvent
from linebot.models import (TextMessage, ImageMessage, VideoMessage, AudioMessage, FileMessage, 
                            StickerMessage, PostbackEvent, TextSendMessage)
import time
from google.cloud import storage
from google.cloud import firestore

# logging module
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.setLevel(logging.ERROR)
logger.setLevel(logging.DEBUG)

# setting linebot secret key
server_url = os.getenv("SERVER_URL")
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("SECRET_KEY"))

def callback(request):
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        print(f'\n Got exception from LINE Messaging API: {e.message}\n')
        for m in e.error.details:
            print(f'{m.property}: {m.message}')
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


def add_data_from_json(foldername, filename, data):
    db = firestore.Client()
    db.collection(foldername).document(filename).set(json.loads(str(data)))

def add_data_from_dict(foldername, filename, data):
    db = firestore.Client()
    db.collection(foldername).document(filename).set(data)

def delete_single_doc(foldername, filename):
    db = firestore.Client()
    db.collection(foldername).document(filename).delete()

@handler.add(FollowEvent)
def process_follow_event(event):
    welcome_message = TextSendMessage(text='您好～我是您的智慧助理：）')
    line_bot_api.reply_message(event.reply_token, welcome_message)  
    
    users_profile = line_bot_api.get_profile(event.source.user_id)
    add_data_from_json('UserID-user', event.source.user_id, users_profile)

@handler.add(JoinEvent)
def process_join_event(event):
    welcome_message = TextSendMessage(text='您好～我是您的智慧助理：）')
    line_bot_api.reply_message(event.reply_token, welcome_message) 
    
    ## ===== This feature is available only for verified or premium accounts. ===== ##
    member_ids_list = json.loads(str(line_bot_api.get_group_member_ids(event.source.group_id)))['memberIds']
    for member_user_id in member_ids_list:
        group_users_profile = line_bot_api.get_group_member_profile(event.source.group_id, member_user_id)
        add_data_from_json('UserID-group-'+ event.source.group_id, member_user_id, group_users_profile)

@handler.add(MemberJoinedEvent)
def process_member_join_event(event):
    users_id_list = event.joined.members
    for users_id_d in users_id_list:
        users_id_i = json.loads(str(users_id_d))['userId']
        users_profile = line_bot_api.get_group_member_profile(event.source.group_id, users_id_i)
        add_data_from_json('UserID-group-'+ event.source.group_id, users_id_i, users_profile)    

@handler.add(MemberLeftEvent)
def process_member_left_event(event):
    users_id_list = event.left.members
    for users_id_d in users_id_list:
        users_id_i = json.loads(str(users_id_d))['userId']
        delete_single_doc('UserID-group-'+ event.source.group_id, users_id_i)


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    stor = storage.Client()
    bucket = stor.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f'File {source_file_name} uploaded to {destination_blob_name}.')

@handler.add(MessageEvent)
def process_message(event, destination):
    reply_message = TextSendMessage(text='收到訊息~')
    line_bot_api.reply_message(event.reply_token, reply_message)

    ## ===== process message content. ===== ##
    message_event = json.loads(str(event))
    message_event.update(json.loads(str(event.source)))
    message_event.update(json.loads(str(event.message)))

    def save_file(ext):
        bucket_name = 'linebot-autorecord-public-gcs'        
        tempfile_path = '/tmp/tempfile' + ext
        file_name = str(event.timestamp) + '-' + str(event.message.id) + '-' + event.message.type + ext
        file_path = os.path.join(time.strftime("%Y-%m-%d"), file_name)

        message_content = line_bot_api.get_message_content(event.message.id)
        with open(tempfile_path, 'wb') as f:
            for chunk in message_content.iter_content():
                f.write(chunk)

        upload_blob(bucket_name, tempfile_path, file_path)
        os.unlink(tempfile_path)
        return 'https://storage.googleapis.com/' + bucket_name + '/' + file_path

    if event.message.type == 'image':        
        message_event['fileURL'] = save_file('.png')
    elif event.message.type == 'video':
        message_event['fileURL'] = save_file('.mp4')
    elif event.message.type == 'audio':
        message_event['fileURL'] = save_file('.m4a')
    elif event.message.type == 'file':
        message_event['fileURL'] = save_file(event.message.file_name)            
                
    ## ===== save message content and user_id to database. ===== ##
    if event.source.type == 'user':
        foldername = 'Message-user-'+ event.source.user_id
    ## -----  save user_id who messaged in the group. ----- ##
    elif event.source.type == 'group':
        foldername = 'Message-group-'+ event.source.group_id        
        group_users_profile = line_bot_api.get_group_member_profile(event.source.group_id, event.source.user_id)
        add_data_from_json('UserID-group-'+ event.source.group_id, event.source.user_id, group_users_profile)    
    ## -----  save user_id who messaged in the room. ----- ##    
    elif event.source.type == 'room':
        foldername = 'Message-room-'+ event.source.room_id
        room_users_profile = line_bot_api.get_room_member_profile(event.source.room_id, event.source.user_id)
        add_data_from_json('UserID-room-'+ event.source.room_id, event.source.user_id, room_users_profile)      

    add_data_from_dict(foldername, event.message.id, message_event)
    print(message_event)