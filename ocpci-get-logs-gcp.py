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
from google.cloud import pubsub_v1
from google.cloud import storage
import logging
import os



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

def receive_messages(project_id, subscription_id, timeout=None):
    """Receives messages from a pull subscription."""

    subscriber = pubsub_v1.SubscriberClient()
    # The `subscription_path` method creates a fully qualified identifier
    # in the form `projects/{project_id}/subscriptions/{subscription_id}`
    subscription_path = subscriber.subscription_path(project_id, subscription_id)# pylint: disable=no-member

    def callback(message):
        print(f"Received {message}.")
        message.ack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}..\n")

    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered first.
            streaming_pull_future.result(timeout=timeout)
        except TimeoutError:
            streaming_pull_future.cancel()

def receive_messages_with_flow_control(project_id, subscription_id, timeout=None):
    """Receives messages from a pull subscription with flow control."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)# pylint: disable=no-member
    
    client = storage.Client()
    bucket = client.get_bucket('origin-ci-test')

    def callback(message):
        mdata = str(message.data)
        mfind = mdata.find("finished.json")
        if mfind == -1:
            message.ack()
        else:
            print(f"Received {mdata}.")
            index = mdata.find("id")
            if index == -1:
                print("Huh?\n")
            else:
                index += len("\"id\": \"origin-ci-test")
                #index += len("\"id\":\"")
                mfind += len("finished.json")
                theurl = mdata[index: mfind]
                print(theurl)
                blob = bucket.get_blob(theurl)
                print(f"{blob}...\n")
                print(blob.download_as_string())




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
    #receive_messages(args.project_id, args.subscription_id)
    receive_messages_with_flow_control(args.project_id, args.subscription_id)