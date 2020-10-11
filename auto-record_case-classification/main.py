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

# link database
db = firestore.Client()

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


@handler.add(FollowEvent)
def process_follow_event(event):
    welcome_message = TextSendMessage(text='您好～我是您的智慧助理：）')
    line_bot_api.reply_message(event.reply_token, welcome_message)

    users_profile = line_bot_api.get_profile(event.source.user_id)
    db.collection('UserID-user').document(event.source.user_id).set(json.loads(str(users_profile)))

@handler.add(JoinEvent)
def process_join_event(event):
    welcome_message = TextSendMessage(text='您好～我是您的智慧助理：）')
    line_bot_api.reply_message(event.reply_token, welcome_message)

    ## ===== This feature is available only for verified or premium accounts. ===== ##
    member_ids_list = json.loads(str(line_bot_api.get_group_member_ids(event.source.group_id)))['memberIds']
    for member_user_id in member_ids_list:
        group_users_profile = line_bot_api.get_group_member_profile(event.source.group_id, member_user_id)
        db.collection('UserID-group-'+ event.source.group_id).document(member_user_id).set(json.loads(str(group_users_profile)))

@handler.add(MemberJoinedEvent)
def process_member_join_event(event):
    users_id_list = event.joined.members
    for users_id_d in users_id_list:
        users_id_i = json.loads(str(users_id_d))['userId']
        users_profile = line_bot_api.get_group_member_profile(event.source.group_id, users_id_i)
        db.collection('UserID-group-'+ event.source.group_id).document(users_id_i).set(json.loads(str(users_profile)))

@handler.add(MemberLeftEvent)
def process_member_left_event(event):
    users_id_list = event.left.members
    for users_id_d in users_id_list:
        users_id_i = json.loads(str(users_id_d))['userId']
        db.collection('UserID-group-'+ event.source.group_id).document(users_id_i).update({'status':'left'})
        # db.collection('UserID-group-'+ event.source.group_id).document(users_id_i).delete()


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

    ## ===== process message content ===== ##
    message_event = {**json.loads(str(event)), **json.loads(str(event.source)), **json.loads(str(event.message))}

    ## ----- save media file ----- ##
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

    ## ----- Special: case classification ----- ##
    if event.message.text.find('【::案件通報開始::】') == 0:
        message_event['publisher'] = event.message.text.split('\n')[1]
        with open('/tmp/keep_case_name.txt', 'w') as f:
            f.write(event.message.text.split('\n')[2])
    else:
        message_event['publisher'] = None

    try:
        with open('/tmp/keep_case_name.txt', 'r') as f:
            message_event['case_name'] = f.read()
    except FileNotFoundError:
        message_event['case_name'] = None        


    ## ===== save message content, userid and profile to database ===== ##
    if event.source.type == 'user':
        foldername_m = 'Message-user-'+ event.source.user_id
        foldername_u = 'UserID-user'
        data_u = line_bot_api.get_profile(event.source.user_id)
    elif event.source.type == 'group':
        foldername_m = 'Message-group-'+ event.source.group_id
        foldername_u = 'UserID-group-'+ event.source.group_id
        data_u = line_bot_api.get_group_member_profile(event.source.group_id, event.source.user_id)  
    elif event.source.type == 'room':
        foldername_m = 'Message-room-'+ event.source.room_id
        foldername_u = 'UserID-room-'+ event.source.room_id
        data_u = line_bot_api.get_room_member_profile(event.source.room_id, event.source.user_id)

    ## ----- save message content to db and print ----- ##
    db.collection(foldername_m).document(event.message.id).set(message_event)
    print(message_event)
    
    ## ----- check users profile already save, or not ----- ##
    doc_ref = db.collection(foldername_u).document(event.source.user_id)
    if doc_ref.get().exists:
        pass
    else:
        doc_ref.set(json.loads(str(data_u)))

    ## ----- Special: add real users profile to db ----- ##
    if event.message.text.find('【::自我介紹::】') == 0:
        real_users_profile = event.message.text.split('\n')
        doc_ref.update({
            'add_timestamp': time.time(),
            'real_name': real_users_profile[1],
            'job_title': real_users_profile[2],
            'organization': real_users_profile[3],
            'email': real_users_profile[4]
        })