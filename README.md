# ocp-ci-rca-tools
A collection of tools aimed at automating as much of the Red Hat OpenShift Platform CI errored jobs root cause analisys (RCA) process as possible.

The intent for these tools is to extract and aggregate all of the CI test errored job log files, such that one can perform RCA.  Inputs to the tooling are;

get-ocp-ci-artifacts ci_job_failure_dest ocp_ci_artifacts [--train ci_job_success_dest]
  - ci_job_failure_dest - destination directory for selected OCP ci artifacts on local server
  - ocp_ci_artifacts - Root directory where OCP ci robot stores ci job artifacts
  - [--train ci_job_success_dest] - Gather successful ci job logs for initial/periodic logreduce model training {1} {4}
  
logreduce-ocp-ci ci_level, ci_job_failure_dest [--train baseline_dir, --threshold val]
  - ci_level {2}
    - infra for OCP on cloud infrastructure 
    - ocp for OCP software
  - ci_job_failure_dest - destination directory for selected OCP ci artifacts on local server
    - this destination directory is constructed from the job archive source format, by rebuilding that directory below the keystring "/origin-ci-test/pr-logs/pull" {3}
    
  - --train baseline_dir 

{1} Need to understand how to automate location of success artifacts, as currently only seeing artifacts from errored job.

{2} Need to better understand the context/intent of the various archive log files.

{3} Make sure keystring "/origin-ci-test/pr-logs/pull" does not change.

{4} How often does the model require retraining?
