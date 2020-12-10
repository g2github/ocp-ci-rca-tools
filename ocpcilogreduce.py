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
import sys
import re
from logreduce.tokenizer import Tokenizer


logfile_as_list = Dict[str, str]

OCPCI_LOCAL_DIR_BASE = "/tmp/ocpci_lr"
OCPCI_LR_LOCAL_MODELS_DIR = OCPCI_LOCAL_DIR_BASE + "/models"
OCPCI_LR_MODEL_FILENAME_TAG = "/model-"
OCPCI_LR_LOCAL_ANOMOLIES_DIR = OCPCI_LOCAL_DIR_BASE + "/anomalies"
OCPCI_LR_ANOMALIES_FILE_TAG = "/anomalies-"

def get_anomalies(clf: Classifier, logfile: Path, gjid) -> List[Tuple[float, Path, logfile_as_list]]:
    result = []
    model = clf.get(gjid)
    print("Testing %s" % logfile)
    lf_as_list = import_logfile(logfile)
    data = [model.process_line(lf_item["message"]) for lf_item in lf_as_list]
    distances = model.test(data)
    for (distance, lf_item) in zip(distances, lf_as_list):
        if distance[0] > 0.2:
            result.append((distance[0], logfile, lf_item))
    return result

def import_logfile(logfile: Path) -> List[logfile_as_list]:
    return [lf_as_list
            for lf_as_list in json.load(open(logfile))["items"]
                # Filter message that contains unfilter noise such as:
                # `ci-op-6ts4i744/e2e-openstack to origin-ci-ig-n-tjcs`
                if not lf_as_list["message"].startswith("Successfully assigned ")]

def ocpci_get_gjid(cld_logfile_path):
    # Pull classifier out of the job_artifacts_url
    # Classifier is the org_repo/job_name
    parts = cld_logfile_path.split("/")
    
    org_repo = parts[2]
    job_name = parts[4]
    gjid = org_repo + "--" + job_name

    return(gjid)

def ocpci_get_jbnum(logfile_path):
    # Pull classifier out of the job_artifacts_url
    # Classifier is the org_repo/job_name
    parts = logfile_path.split("/")
    
    build_num = parts[5]

    return(build_num)

def ocpci_get_lfilenm(logfile_path):
    # Pull classifier out of the job_artifacts_url
    # Classifier is the org_repo/job_name
    parts = logfile_path.split("/")
    
    lfilenm = parts[8]

    return(lfilenm)

def ocpci_create_model(logfile: Path, gjid) -> Classifier:
    # Hardwired for events.json --> TBD: generalize
    clf = Classifier("hashing_nn") # choice of classifier algorithm
    model = clf.get(gjid) # arg --> 'logfile name' i.e. events.json class vs instance
    clf.gjid = gjid 
    # model.gjid = gjid

    print("ocpci_create_model(): Loading %s" % logfile)
    lf_as_list = import_logfile(logfile)
    if not len(lf_as_list):
        print(f"{logfile} List from import_logfile(no [items]) is empty")
        return(False)

    data = set([model.process_line(lf_item["message"]) for lf_item in lf_as_list])
    model.train(data)


    clf.save(OCPCI_LR_LOCAL_MODELS_DIR + OCPCI_LR_MODEL_FILENAME_TAG + f"{gjid}.pkt") 
    
    return clf

def ocpci_train_model(logfile: Path, gjid) -> Classifier:
    model_path = OCPCI_LR_LOCAL_MODELS_DIR + OCPCI_LR_MODEL_FILENAME_TAG + f"{gjid}.pkt"
    if os.path.exists(model_path):
        clf = Classifier.load(model_path)
        model = clf.get(gjid)

        print("ocpci_train_model(): Loading %s" % logfile)
        lf_as_list = import_logfile(logfile)
        data = set([model.process_line(lf_item["message"]) for lf_item in lf_as_list])
        model.train (data)
        clf.save(model_path)

        return(True)
    else:
        return(False)

def ocpci_model_exists(gjid):
    # print(f"ocpci_model_exists({gjid}) Made it!")
    model_path = OCPCI_LR_LOCAL_MODELS_DIR + OCPCI_LR_MODEL_FILENAME_TAG + f"{gjid}.pkt"

    if os.path.exists(model_path):
        print(f"ocpci_model_exists({gjid}) at {model_path}")
        model = Classifier.load(model_path)

        return(model)
    else:
        print(f"ocpci_model_exists({gjid}) NOT at {model_path}")
        return(False)

def ocpci_logreduce(gjid, lcl_logfile_path):
    model = ocpci_model_exists(gjid)
    anomalies = get_anomalies(model, lcl_logfile_path, gjid)
    gjid_anomalies_path = OCPCI_LR_LOCAL_ANOMOLIES_DIR + OCPCI_LR_ANOMALIES_FILE_TAG + f"{gjid}.json"
    if not os.path.exists(OCPCI_LR_LOCAL_ANOMOLIES_DIR):
        os.mkdir(OCPCI_LR_LOCAL_ANOMOLIES_DIR)
        
    # store results for eventual presentation
    with open(gjid_anomalies_path, 'a+') as f:
        json.dump(anomalies, f) 

    return