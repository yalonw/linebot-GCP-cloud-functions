#!/bin/bash
## ===== Set up gcp development environment Using the gcloud command-line tool ===== ##

## ===== Initializing the Cloud SDK ===== ##
gcloud init

## ===== Select or create a GCP project ===== ##
PROJECT_ID=${USER}linebot-autorecord
BILLING_ID="$(gcloud beta billing accounts list --format="value(ACCOUNT_ID)")"
REGION="asia-northeast1"

gcloud projects create ${PROJECT_ID} --set-as-default
gcloud beta billing projects link ${PROJECT_ID} --billing-account ${BILLING_ID}
# gcloud config set project ${PROJECT_ID}
# gcloud config configurations list

## ===== Create a Filestore ===== ##
gcloud app create --region=${REGION}
gcloud firestore databases create --region=${REGION}

## ===== Create a Cloud Storage ===== ##
gsutil mb -b on -l ${REGION} gs://${PROJECT_ID}-public-gcs/
gsutil iam ch allUsers:objectViewer gs://${PROJECT_ID}-public-gcs

## ===== Create a Cloud Functions ===== ##
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
cd auto-record
gcloud functions deploy ${PROJECT_ID} \
  --region=${REGION} \
  --trigger-http --allow-unauthenticated \
  --env-vars-file=.env.yaml \
  --runtime=python38 \
  --entry-point=callback