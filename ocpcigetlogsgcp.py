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
from ocpcilogreduce import ocpci_logreduce, ocpci_get_gjid, ocpci_get_jbnum, ocpci_get_lfilenm
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


def get_logfile(events_json_path, bucket_name):
    print(f"get_logfile({events_json_path}) Made it!")
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    events_json_blob = bucket.blob(events_json_path)
    gjid = ocpci_get_gjid(events_json_path)
    jbnum = ocpci_get_jbnum(events_json_path)
    lfnm = ocpci_get_lfilenm(events_json_path)
    local_log_dir = "/tmp/ocpci_lr"
    local_logfile = f"{local_log_dir}/{gjid}/{lfnm}{jbnum}.pkt"
    if not os.path.exists(local_log_dir):
        os.mkdir(local_log_dir)
    if not os.path.exists(f"{local_log_dir}/{gjid}"):
        os.mkdir(f"{local_log_dir}/{gjid}")
    

    Path(local_logfile).touch()

    events_json_blob.download_to_filename(local_logfile)

    return(local_logfile)

def filter_jobs(mdata):
    print("filter_jobs() Made it!")
    if "name" in mdata:
        mdata_name = mdata["name"]
    else:
        print("no 'name' in mdata")
        return(False)

    mdata_list = mdata_name.split("/")
    if len(mdata_list) != 7:
            return(False)
    print(f"mdata_name is {mdata_name}")
    

    bucket_name = "origin-ci-test"
    org_repo = mdata_list[2]
    pull_number = mdata_list[3]
    job_name = mdata_list[4]
    build_number = mdata_list[5]
    prlogs_pull_dir = "pr-logs/pull/"
    # prlogs_directory_dir = "pr_logs/directory"
    finished_json_path = prlogs_pull_dir + org_repo + "/" + pull_number + "/" + job_name + "/" + build_number + "/" + "finished.json"
    events_json_path =   prlogs_pull_dir + org_repo + "/" + pull_number + "/" + job_name + "/" + build_number + "/" + "artifacts/build-resources/events.json"

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    chk_bucket = storage_client.bucket(bucket_name)

    finished_json_blob = bucket.blob(finished_json_path)
    # print(f"finished_json_blob is {finished_json_blob}")
    finished_json = str(finished_json_blob.download_as_string())
    # print(f"finished_json is {finished_json[:20]}")



    if "\"result\":\"SUCCESS\"" in finished_json:
        # print("filter_jobs(): finished_json=SUCCESS filtered")
        # TBD: seed jobname LR model
    
        return(False)
    elif "\"result\":\"FAILURE\"" in finished_json:
        stats = storage.Blob(bucket=chk_bucket, name=events_json_path).exists(storage_client)
        if stats == False:
            print(f"no events.json file {events_json_path}")
            return(False)
        else:
            print(f"events.json file exists {events_json_path}")
            local_logfile = get_logfile(events_json_path, bucket_name)
            ocpci_logreduce(events_json_path, local_logfile)

        return(True)
        
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