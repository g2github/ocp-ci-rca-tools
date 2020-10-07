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
from pathlib import Path
from typing import List, Tuple, Dict
import wget
import os
import os.path
from os import path


# When a ci job error occurs, this script can download the artifacts for later offline analysis

# CLI Format$  get-ocp-ci-artifacts  ocp_ci_artifacts_src ocp_ci_artifacts_dest [--train ci_success_logs_dest]
def usage() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download OCP CI failed job artifacts to local transfer directory")
    parser.add_argument('ocp_ci_artifacts_src')
    parser.add_argument('ocp_ci_artifacts_dest')
    return parser.parse_args()


def main() -> None:
    args = usage()

    # construct local OCP CI storage directory to mimic GCS hierarchy under CLI-specified local dir
    if not os.path.exists(args.ocp_ci_artifacts_dest):
        os.mkdir(args.ocp_ci_artifacts_dest)

    # strip out remote server file system 
    known_unknowable = "/origin-ci-test/pr-logs/pull"
    index = args.ocp_ci_artifacts_src.find(known_unknowable)
    index += len(known_unknowable)
    ocp_ci_artifacts_base_dir = args.ocp_ci_artifacts_src[index:]
    local_logs_store = ocp_ci_artifacts_base_dir.split("/", 10)
    local_log_filename = args.ocp_ci_artifacts_dest

    n = 0
    for dir_lvl in local_logs_store[1::]:
        n+=1
        if n==1:
            local_log_filename = local_log_filename + "/" + dir_lvl
        else:
            local_log_filename = local_log_filename + "-" + dir_lvl
    
    # Currently using the following OCP CI Job artifact logs;
    #  build-log.txt to mine for erroreds associated with the OCP cluster erroreds related to its hosting cloudSP
    #  events.json to mine for erroreds associated with the OCP cluster itself

    remote_infra_filename = args.ocp_ci_artifacts_src + "build-log.txt"
    local_infra_filename = local_log_filename + "-build-log.txt"

    remote_ocp_filename = args.ocp_ci_artifacts_src + "artifacts/build-resources/events.json"
    local_ocp_filename = local_log_filename + "-artifacts-build-resources-events.json"

    # Download log files to local store
    wget.download(remote_infra_filename, out=local_infra_filename)
    print("\n") 
    wget.download(remote_ocp_filename, out=local_ocp_filename)

if __name__ == "__main__":
    main()
