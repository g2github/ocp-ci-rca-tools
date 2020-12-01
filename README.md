# OCP CI Root Cause Analysis Tool

Tooling aimed at automating as much of the Red Hat OpenShift Platform CI (OCP CI) Root Cause Analisys (RCA) process as possible.

The specific goal is to reduce the time it takes to understand an OCP CI job failure by compressing the information of a failed job output to the bits that commuicate the anomalies. This first POC version treats each relavent OCP CI logfile individually, baselined and analyzed with resultant output saved for subsequent analysis.  

## Usage
To use the code, first request GCS authentication credentials from your organizations GCS administrator (delivered as a JSON formated file), then enter the following commands:

> cmd-line$ export GOOGLE_APPLICATION_CREDENTIALS="path to your GCS credentials file"  
> cmd-line$ gcloud auth activate-service-account --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"   

Next, enter the following command:  
> cmd-line$ ocpcigetlogsgcp <ocipci-gcs-project_id>, <ocpci-topic_id>, <ocpci-subscription_id>

where:
> <ocipci-gcs-project_id> is "openshift-gce-devel"  
> <ocpci-topic_id> is "origin-ci-test",  
> <ocpci-subscription_id> is "ocpci-logs". 

Current data output format is:

'local-ocpci-lr-server':/tmp/ocpci_lr/anomolies/anomolies-<gjid>.json
where:
> <gjid> is the Global Job ID that is the concatentation of the OCP CI GCS Bucket org_repo and job_name.

## References:

- <https://opensource.com/article/18/9/quiet-log-noise-python-and-machine-learning>
- <https://ci-operator-configresolver-ui-ci.apps.ci.l2s4.p1.openshiftapps.com/help>
- <https://github.com/openshift/ci-tools/blob/master/ARCHITECTURE.md>
- <https://github.com/openshift/ci-tools/blob/master/CONFIGURATION.md#base_images>
- <https://github.com/openshift/release/tree/master/ci-operator>
- <https://github.com/kubernetes/test-infra/blob/master/gubernator/README.md#job-artifact-gcs-layout>
- <https://github.com/openshift/release/blob/54a2db7d73cdeaff2b9bc94398508268f9f85df9/core-services/prow/02_config/_config.yaml#L492>
- <https://github.com/kubernetes/test-infra/blob/master/gubernator/README.md#job-artifact-gcs-layout>
