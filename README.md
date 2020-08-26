# ocp-ci-rca-tools

A collection of tools aimed at automating as much of the Red Hat OpenShift Platform CI errored jobs root cause analisys (RCA) process as possible.

The intent for these tools is to aggregate all of the CI test errored job log files, then extract and count all unique error messages across the lo files such that one can perform RCA.  The extraction and count service is based on the Python logreduce Project, which based on seeding its learning model with success logs, highlights useful text in failed logs.

Inputs to the tooling are;

get-ocp-ci-artifacts  ocp_ci_artifacts ci_errored_logs_dest [--train ci_success_logs_dest]

- ci_errored_logs_dest - destination directory for selected OCP ci artifacts on local server
  - ocp_ci_artifacts - Root directory where OCP ci robot stores ci job artifacts
  - [--train ci_success_logs_dest] - Gather successful ci job logs for initial/periodic logreduce model training {1} {4} {5}
  
logreduce-ocp-ci ci_level, ci_errored_logs_dest [--train ci_success_logs_dest, --threshold val]

- ci_level {2}
  - infra for OCP on cloud infrastructure
    - ocp for OCP software
  - ci_errored_logs_dest - destination directory for selected OCP ci artifacts on local server
    - this destination directory is constructed from the job archive source format, by rebuilding that directory below the keystring "/origin-ci-test/pr-logs/pull" {3}

  - --train ci_success_logs_dest

{1} Need to understand how to automate location of success artifacts, as currently only seeing artifacts from errored job.

{2} Need to better understand the context/intent of the various archive log files.

{3} OpenShift CI Build Artifacts and Results are stored using Google Cloud Storage within the origin-ci-test Bucket. This bucket allows non-authenticated read access.

{4} How often does the model require retraining?

{5} Can ${ARTIFACT_DIR} be used to "know" the GCS origin-ci-test Bucket root?

References:

- <https://ci-operator-configresolver-ui-ci.apps.ci.l2s4.p1.openshiftapps.com/help>
- <https://github.com/openshift/release/tree/master/ci-operator>
