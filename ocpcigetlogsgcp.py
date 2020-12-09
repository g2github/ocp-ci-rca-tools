#!/usr/bin/env python3
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1, storage
from ocpcilogreduce import ocpci_logreduce, ocpci_get_gjid, ocpci_get_jbnum, ocpci_get_lfilenm, OCPCI_LOCAL_DIR_BASE, ocpci_model_exists, ocpci_train_model, ocpci_create_model
import logging
import os
import time
import json
from pathlib import Path



def usage() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hook into OCP CI GCS artifacts bucket for logfile access")

    parser.add_argument("project_id", help="Your Google Cloud project ID")
    parser.add_argument("topic_id", help="Your Google Cloud topic ID")
    parser.add_argument("subscription_id", help="Your Google Cloud subscription ID")

    return parser.parse_args()

def list_subscriptions_in_topic(project_id, topic_id):
    """Lists all subscriptions for a given topic."""

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)# pylint: disable=no-member

    response = publisher.list_topic_subscriptions(request={"topic": topic_path})# pylint: disable=no-member
    for subscription in response:
        print(subscription)

def list_subscriptions_in_project(project_id):
    """Lists all subscriptions in the current project."""
    subscriber = pubsub_v1.SubscriberClient()
    project_path = f"projects/{project_id}"

    # Wrap the subscriber in a 'with' block to automatically call close() to
    # close the underlying gRPC channel when done.
    with subscriber:
        for subscription in subscriber.list_subscriptions(request={"project": project_path}):# pylint: disable=no-member
            print(subscription.name)

def list_blobs(bucket_name):
    """Lists all the blobs in the bucket."""
    # bucket_name = "your-bucket-name"

    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name)

    for blob in blobs:
        print(blob.name)

def get_logfile(cld_logfile_path, bucket_name):
    # print(f"get_logfile({events_json_path}) Made it!")
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    chk_bucket = storage_client.bucket(bucket_name)


    cld_logfile_blob = bucket.blob(cld_logfile_path)
    gjid = ocpci_get_gjid(cld_logfile_path)
    jbnum = ocpci_get_jbnum(cld_logfile_path)
    lfnm = ocpci_get_lfilenm(cld_logfile_path)
    local_logfile = OCPCI_LOCAL_DIR_BASE + f"/{gjid}/{jbnum}-{lfnm}"
    print(f"get_logfile({cld_logfile_path}) local_logfile = {local_logfile}")

    stats = storage.Blob(bucket=chk_bucket, name=cld_logfile_path).exists(storage_client)
    if stats == False:
        print(f"get_logfile(): no GCS logfile {cld_logfile_path}")
        return(False)


    if not os.path.exists(OCPCI_LOCAL_DIR_BASE):
        os.mkdir(OCPCI_LOCAL_DIR_BASE)
    if not os.path.exists(OCPCI_LOCAL_DIR_BASE + f"/{gjid}"):
        os.mkdir(OCPCI_LOCAL_DIR_BASE + f"/{gjid}")
    

    Path(local_logfile).touch()

    cld_logfile_blob.download_to_filename(local_logfile)

    return(local_logfile)

def filter_jobs(mdata):
    bucket_name = "origin-ci-test"
    # Using the "name" field of the GCS pubsub data field, filter out any non-finished.json GCS object event messages
    if "name" in mdata:
        mdata_name = str(mdata["name"])
    else:
        print(f"filter_jobs(): Bad [missing?] GCS pubsub message.data.name! [{mdata}]")

        return(False)

    mdata_list = mdata_name.split("/")
    if len(mdata_list) != 7:
            return(False)
    print(f"filter_jobs(): mdata_name is {mdata_name}")

    # Construct "url pointers" to finished.json and events.json GCS objects"
    gcs_finished_json = mdata_name
    gcs_events_json = mdata_name.replace("finished.json", "artifacts/build-resources/events.json")

    storage_client = storage.Client()
 
    bucket = storage_client.get_bucket(bucket_name)
    chk_bucket = storage_client.bucket(bucket_name)

    finished_json_blob = bucket.blob(gcs_finished_json)
    finished_json = str(finished_json_blob.download_as_string())

    gjid = ocpci_get_gjid(gcs_events_json)
    model = ocpci_model_exists(gjid)
    gcs_events_json_exists = storage.Blob(bucket=chk_bucket, name=gcs_events_json).exists(storage_client)
    local_logfile = get_logfile(gcs_events_json, bucket_name)

    if "\"result\":\"SUCCESS\"" in finished_json:
        if model is not False:
            if gcs_events_json_exists:
                ocpci_train_model(local_logfile, gjid)
                return(True)
            else:
                print(f"filter_jobs({gjid}): Missing job artifacts! [{gcs_events_json}]")
                return(False)
        else:
            if gcs_events_json_exists:
                ocpci_create_model(local_logfile, gjid)
                return(True)
            else:
                print(f"filter_jobs({gjid}): Missing job artifacts! [{gcs_events_json}]")
                return(False)
    elif "\"result\":\"FAILURE\"" in finished_json:
        if model is not False:
            if gcs_events_json_exists:
                ocpci_logreduce(gjid, local_logfile)
                return(True)
            else:
                print(f"filter_jobs({gjid}): Missing job artifacts! [{gcs_events_json}]")
                return(False)
        else:
            print(f"filter_jobs({gjid}): no model to logreduce! [{gcs_events_json}]")
            return(False)
    else:
        print(f"filter_jobs({gjid}): Bad [malformed?] GCS finished.json! [{gcs_finished_json}]")
        return(False)
        
def receive_messages_with_flow_control(project_id, subscription_id, timeout=None):
    """Receives messages from a pull subscription with flow control."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)# pylint: disable=no-member
    
    def callback(message):
        mdata = str(message.data)
        if "finished.json" in mdata:
            mdata = mdata[2:-3].replace('\\n', '')
            mdata = json.loads(mdata)

            if "finished.json" in mdata['name'] and \
                "/logs/" not in mdata['id'] and \
                    "/batch/" not in mdata['name']:
                print("message accept") # with" + str(mdata)
                filter_jobs(mdata)
            # else:
                # print("not finished.json")

        message.ack()

    # Limit the subscriber to only have ten outstanding messages at a time.
    flow_control = pubsub_v1.types.FlowControl(max_messages=10)

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback, flow_control=flow_control
    )
    print(f"Listening for messages on {subscription_path}..\n")

    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            streaming_pull_future.result(timeout=timeout)
        except TimeoutError:
            streaming_pull_future.cancel()

if __name__ == "__main__":
    args = usage()
    list_subscriptions_in_project(args.project_id)
    receive_messages_with_flow_control(args.project_id, args.subscription_id)