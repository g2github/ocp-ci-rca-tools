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

import logreduce
from logreduce.process import Classifier
import argparse
import json
import pprint
from pathlib import Path
from typing import List, Tuple, Dict
import os

ocp_Event = Dict[str, str]
infra_Event = Dict[str, str]


# CLI Format$  ocpci-logreduce(object.error_job(URL), object.success_job(url))  
def usage() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate and filter OCP CI job errors for subsequant analysis")
    parser.add_argument("error_job_url")
    parser.add_argument("success_job_url")

    return parser.parse_args()

def get_ocp_event_files(dir_path: str) -> List[Path]:
    return [Path(dir) / file
        for dir, _, files in os.walk(dir_path)
            for file in files
                if file.endswith(".json") ]

def get_infra_event_files(dir_path: str) -> List[Path]:
    return [Path(dir) / file
        for dir, _, files in os.walk(dir_path)
            for file in files
                if file.endswith(".txt") ]

def get_ocp_events(event_file: Path) -> List[ocp_Event]:
    return [event
            for event in json.load(open(event_file))["items"]
                # Filter message that contains unfilter noise such as:
                # `ci-op-6ts4i744/e2e-openstack to origin-ci-ig-n-tjcs`
                if not event["message"].startswith("Successfully assigned ")]

def get_infra_events(event_file: Path) -> List[infra_Event]:
    return [event
            for event in json.load(open(event_file))["items"]
                # Filter message that contains unfilter noise such as:
                # `ci-op-6ts4i744/e2e-openstack to origin-ci-ig-n-tjcs`
                if not event["message"].startswith("Successfully assigned ")]

def create_ocp_model(event_files: List[Path]) -> Classifier:
    clf = Classifier("hashing_nn")
    model = clf.get("events")
    for event_file in event_files:
        print("Loading %s" % event_file)
        events = get_ocp_events(event_file)
        data = set([model.process_line(event["message"]) for event in events])
        model.train(data)

    clf.save("/tmp/ocp-model.pkt")
    
    return clf

def create_infra_model(event_files: List[Path]) -> Classifier:
    clf = Classifier("hashing_nn")
    model = clf.get("events")
    for event_file in event_files:
        print("Loading %s" % event_file)
        events = get_infra_events(event_file)
        data = set([model.process_line(event["message"]) for event in events])
        model.train(data)

    clf.save("/tmp/infra-model.pkt")

    return clf

def get_ocp_anomalies(clf: Classifier, event_files: List[Path]) -> List[Tuple[float, Path, ocp_Event]]:
    result = []
    model = clf.get("events")
    for event_file in event_files:
        print("Testing %s" % event_file)
        events = get_ocp_events(event_file)
        data = [model.process_line(event["message"]) for event in events]
        distances = model.test(data)
        for (distance, event) in zip(distances, events):
            if distance[0] > 0.2:
                result.append((distance[0], event_file, event))
    return result

def get_infra_anomalies(clf: Classifier, event_files: List[Path]) -> List[Tuple[float, Path, infra_Event]]:
    result = []
    model = clf.get("events")
    for event_file in event_files:
        print("Testing %s" % event_file)
        events = get_infra_events(event_file)
        data = [model.process_line(event["message"]) for event in events]
        distances = model.test(data)
        for (distance, event) in zip(distances, events):
            if distance[0] > 0.2:
                result.append((distance[0], event_file, event))
    return result


def main() -> None:
    args = usage()

    if args.success_job_url:
        ocp_event_files = get_ocp_event_files(args.success_job_url)
        ocp_clf = create_ocp_model(ocp_event_files)
        infra_event_files = get_infra_event_files(args.success_job_url)
        infra_clf = create_infra_model(infra_event_files)
    else:
        if os.path.exists("/tmp/ocp_model.pkt"):
            ocp_clf = Classifier.load("/tmp/ocp_model.pkt")
            ocp_anomalies = get_ocp_anomalies(ocp_clf, get_ocp_event_files(args.error_job_url))

        
            infra_clf = Classifier.load("/tmp/infra_model.pkt")

    infra_anomalies = get_infra_anomalies(infra_clf, get_infra_event_files(args.error_job_url))

    ocp_file = open('LR.out', 'a')

    for (distance, path, event) in ocp_anomalies:
        if distance > args.threshold:
            #print(path.name, distance)
            #pprint.pprint(event)
            if event.get('count') != 1: 
                match = "[count] " + str(event.get('count')) + "\n" 
                ocp_file.write(match)
                match = "[logfile] " + path.name + "\n"
                ocp_file.write(match)
                match = "[logReduce proximity] " + str(distance) + "\n"
                ocp_file.write(match)
                match = "[reason] " + event.get("reason") + "\n"
                ocp_file.write(match)
                match = "[message] " + event.get("message") + "\n"
                ocp_file.write(match)
                match = "[type] " + event.get("type") + "\n"
                ocp_file.write(match)

                ocp_file.write("\n")
    
    ocp_file = ocp_file.close()

   


if __name__ == "__main__":
    main()
