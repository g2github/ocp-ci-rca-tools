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

import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import os
import os.path
from os import path
import wget


# When a ci failure occurs this script can download the artifacts 
# for later offline analysis

# CLI Format$  get-ocp-ci-artifacts ci_job_failure_dest ocp-ci-artifacts 
def usage() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download OCP CI failed job artifacts to local transfer directory")
    parser.add_argument('ci_job_failure_dest')
    parser.add_argument('ocp_ci_artifacts')
    return parser.parse_args()


def main() -> None:
    args = usage()

    # construct local OCP CI storage directory to mimic GCS hierarchy under CLI-specified local dir
    if not os.path.exists(args.ci_job_failure_dest):
        os.mkdir(args.ci_job_failure_dest)

    # build out mimic of GCS OCP CI storage directory structure, to enable subsequent location of artifacts to CI job
    # example GCS OCP CI job archive base directory
    # https://storage.googleapis.com/origin-ci-test/pr-logs/pull/openshift_cluster-network-operator/758/pull-ci-openshift-cluster-network-operator-release-4.5-e2e-aws-sdn-multi/1295819731873304576/
    if args.ocp_ci_artifacts.startswith("https://storage.googleapis.com/origin-ci-test/pr-logs/pull"):
        ocp_ci_artifacts_metad = args.ocp_ci_artifacts[len("https://storage.googleapis.com/origin-ci-test/pr-logs/pull"):]
        ocp_ci_metad = ocp_ci_artifacts_metad.split("/", 10)
        build_dir = args.ci_job_failure_dest
        for dir_lvl in ocp_ci_metad[1::]:
            build_dir = build_dir + "/" + dir_lvl
            if not os.path.exists(build_dir):
                os.mkdir(build_dir)
    
    # Currently using the following OCP CI Job arttifact logs;
    #  build-log.txt to mine for failures associated with the OCP cluster failures related to its hosting cloudSP
    #  events.json to mine for failures associated with the OCP cluster itself
    infra_ci_log = args.ocp_ci_artifacts + "build-log.txt"
    ocp_ci_log = args.ocp_ci_artifacts + "artifacts/build-resources/events.json"

    # Download log files to local store
    wget.download(infra_ci_log, out=build_dir)
    print("\n") 
    wget.download(ocp_ci_log, out=build_dir)

    print("\ndone")
    
if __name__ == "__main__":
    main()
