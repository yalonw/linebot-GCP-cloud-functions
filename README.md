###### Date: 2020.10

# LineBot + GCP ( Cloud Functions )
### 開發目標
- 利用 LineBot 自動儲存所有對話訊息（包含照片、影片、音檔、文件等），  
  以及儲存使用者資訊，並佈署至 Google Cloud Functions

### 開發環境
- 雲服務 Cloud Service : GCP ( Google Cloud Platform )
- 伺服器 Server : [Cloud Functions](https://cloud.google.com/functions)
- 資料庫 Database : [Firestore](https://cloud.google.com/firestore)
- 儲存空間 Storage : [Cloud Storage](https://cloud.google.com/storage)

### 程式碼
- Cloud Functions source code ： (╭☞ ･ω･)╭☞ [傳送門](./auto-record/main_new.py)
- gcloud script
  - step1 : [Install the Cloud SDK](https://cloud.google.com/sdk/docs/install) 
  - step2 : modify SECRET_KEY in [`.env.yaml`](./.env.yaml) and PROJECT_ID in [`set_up_gcp_service.sh`](./set_up_gcp_service.sh)
  - step3 : [`bash set_up_gcp_service.sh`](./set_up_gcp_service.sh)

### 參考資料
+ LINE Bot
  - [Messaging API reference](https://developers.line.biz/zh-hant/reference/messaging-api/)
  - [GitHub - Build LINE Bot examples](https://github.com/line/line-bot-sdk-python/blob/master/examples/flask-kitchensink/app.py)
+ Cloud Functions
  - [Quickstart triggered by an HTTP request](https://cloud.google.com/functions/docs/quickstart-python) 
  -> [GitHub](https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/storage/cloud-client/storage_upload_file.py)
  - [The only writeable part of the filesystem is the `/tmp` directory](https://cloud.google.com/functions/docs/concepts/exec#file_system)
+ Cloud Storage
  - [Quickstart using a server client library](https://googleapis.dev/python/storage/latest/index.html)
  - [Sharing data public](https://cloud.google.com/storage/docs/cloud-console?&_ga=2.140644026.-984261553.1588856613#_sharingdata) 
  -> [Making data public](https://cloud.google.com/storage/docs/access-control/making-data-public)
  - [Accessing public data - API Link](https://cloud.google.com/storage/docs/access-public-data#api-link)
+ Firestore
  - [Quickstart using a server client library](https://cloud.google.com/firestore/docs/quickstart-servers?hl=zh-tw)