# ocp-ci-rca-tools

A collection of tools aimed at automating as much of the Red Hat OpenShift Platform CI errored jobs root cause analisys (RCA) process as possible.

The intent for these tools is to aggregate all of the CI test errored job log files, then extract and count all unique error messages across the lo files such that one can perform RCA.  The extraction and count service is based on the Python logreduce Project, which based on seeding its learning model with success logs, highlights useful text in failed logs.

References:

- <https://ci-operator-configresolver-ui-ci.apps.ci.l2s4.p1.openshiftapps.com/help>
- <https://github.com/openshift/ci-tools/blob/master/ARCHITECTURE.md>
- <https://github.com/openshift/ci-tools/blob/master/CONFIGURATION.md#base_images>
- <https://github.com/openshift/release/tree/master/ci-operator>
- <https://github.com/kubernetes/test-infra/blob/master/gubernator/README.md#job-artifact-gcs-layout>
- <https://github.com/openshift/release/blob/54a2db7d73cdeaff2b9bc94398508268f9f85df9/core-services/prow/02_config/_config.yaml#L492>
- <https://github.com/kubernetes/test-infra/blob/master/gubernator/README.md#job-artifact-gcs-layout>
