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

"""Script to ..."""

from logreduce.process import Classifier
import argparse
import json
import pprint
from pathlib import Path
from typing import List, Tuple, Dict
import os


# CLI Format$  logreduce-ocp-ci ci_level, ci_job_failure_dest [-train baseline_dir] 
def usage() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate OCP CI job failures for subsequant analysis")
    parser.add_argument("ci_level", choices=['infra', 'ocp'])
    parser.add_argument("ci_job_failure_dest")
    parser.add_argument("--train", nargs="?", default=0)
    parser.add_argument("--threshold", default=0.2)
    return parser.parse_args()


def get_event_files(ci_level, dir_path: str) -> List[Path]:
    return [Path(dir) / file
        for dir, _, files in os.walk(dir_path)
            for file in files
                if ci_level == "ocp"
                   if file.endswith(".json") ]


Event = Dict[str, str]


def get_events(event_file: Path) -> List[Event]:
    return [event
            for event in json.load(open(event_file))["items"]
                # Filter message that contains unfilter noise such as:
                # `ci-op-6ts4i744/e2e-openstack to origin-ci-ig-n-tjcs`
                if not event["message"].startswith("Successfully assigned ")]

def create_model(event_files: List[Path]) -> Classifier:
    clf = Classifier("hashing_nn")
    model = clf.get("events")
    for event_file in event_files:
        print("Loading %s" % event_file)
        events = get_events(event_file)
        data = set([model.process_line(event["message"]) for event in events])
        model.train(data)

    clf.save("/tmp/model.pkt")

    return clf


def get_anomalies(clf: Classifier, event_files: List[Path]) -> List[Tuple[float, Path, Event]]:
    result = []
    model = clf.get("events")
    for event_file in event_files:
        print("Testing %s" % event_file)
        events = get_events(event_file)
        data = [model.process_line(event["message"]) for event in events]
        distances = model.test(data)
        for (distance, event) in zip(distances, events):
            if distance[0] > 0.2:
                result.append((distance[0], event_file, event))
    return result


def main() -> None:
    args = usage()

    if args.train:
        event_files = get_event_files(args.ci_level, args.train)
        clf = create_model(event_files)
    else:
        clf = Classifier.load("/tmp/model.pkt")

    anomalies = get_anomalies(clf, get_event_files(args.ci_level, args.ci_job_failure_dest))
    for (distance, path, event) in anomalies:
        if distance > args.threshold:
            print(path.name, distance)
            pprint.pprint(event)


if __name__ == "__main__":
    main()
