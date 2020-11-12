# SQL based data processing with declarative framework
This is a project developed with Python CDK for the solution SO0141 - SQL based ETL with a declarative framework.

## Prerequisites 
Python is needed in this project. Specifically, you will need version 3.6 or later. You can find information about downloading and installing Python [here](https://www.python.org/downloads/). Additionally you will need to have the Python package installer (pip) installed. See installation instructions [here](https://pypi.org/project/pip/).

If you use Windows, be sure Python is on your PATH. 


## Deploy Infrastructure

Clone the project.

```
$ git clone https://github.com/melodyyangaws/sql-based-etl.git
$ cd sql-based-etl

```

Build docker image and push to ECR via a bash script. 
arc-jupyter doesn't need image build, just pull it from public and push to ECR. The {{account_number}} in `deployment/environment.cfg` and sample job files under `source/app_resources/` will be updated by your input.

```
$ bash deployment/pull_and_push_ecr.sh <region> <account_number> <ecr_repo_name> <build_or_not>
 
# For example:
$ bash deployment/pull_and_push_ecr.sh 'us-west-2' 1234567 'arc' 1
$ bash deployment/pull_and_push_ecr.sh 'us-west-2' 1234567 'arc-jupyter'
```

This project is set up like a standard Python project. The `cdk.json` file tells where the application entry point is.The initialization process also creates a virtualenv within this project, stored under the .env
directory.  To create the virtualenv it assumes that there is a `python3`(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

``` 
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r source/requirements.txt
```

Install kubectl & jq tools

```
$ sudo curl --silent --location -o /usr/local/bin/kubectl \
   https://amazon-eks.s3.us-west-2.amazonaws.com/1.17.11/2020-09-18/bin/linux/amd64/kubectl
$ sudo chmod +x /usr/local/bin/kubectl

$ sudo yum -y install jq
```

At this point you can now synthesize the CloudFormation template to be deployed.

```
$ cdk synth SparkOnEKS --require-approval never -c env=develop -o cdk.out

```

Finally deploy the stack. It takes two optional parameters `jhubuser` & `datalakebucket`.

```
# Scenario1: the recommended way is to deploy the default settings

$ cdk deploy SparkOnEKS --require-approval never -c env=develop

# Scenario2: give an arbitrary username as your Jupyter Hub login. 
# Otherwise, login with a default user.

$ cdk deploy SparkOnEKS --require-approval never -c env=develop --parameters jhubuser=<random_login_name>

# Scenario3: by default, the `datalakebucket` is set to the solution deployment S3 bucket, 
# if you want to use an existing bucket that contains real data, add the parameter to the command line
# an IAM role will be mapped to the existing S3 bucket for Jupyter Notebook and ETL job access. 
# NOTE: the bucket must be in the same region as your infrastructure deployment.

$ cdk deploy SparkOnEKS --require-approval never -c env=develop --parameters jhubuser=<random_login_name> --parameters datalakebucket=<existing_datalake_bucket>

```
## Troubleshooting

1. If you see the issue `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1123)`, most likely it means no default certificate authority for your Python installation on OSX. Refer to the [answer](https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate) and installing `Install Certificates.command` should fix your local environment.

2. If an error says `SparkOnEKS failed: Error: This stack uses assets, so the toolkit stack must be deployed to the environment (Run "cdk bootstrap aws://YOUR_ACCOUNT_NUMBER/REGION")` , it means it is the first time you deploy an AWS CDK app into an environment (account/region), you’ll need to install a “bootstrap stack”. This stack includes resources that are needed for the toolkit’s operation. For example, the stack includes an S3 bucket that is used to store templates and assets during the deployment process.

You can use the cdk bootstrap command to install the bootstrap stack into an environment:

```
cdk bootstrap aws://YOUR_ACCOUNT_NUMBER/REGION -c develop
```


## Manually fix EKS node group security groups
Due to the issue https://github.com/aws/aws-cdk/issues/10884 , we will have to manually amend the SG for now.
1. Go to EC2 console and locate the instance `Spot-spark-on-eks-dev`, find an inbound rule which has the source from `eks-cluster-sg-spark-on-eks-dev` and port is 443, then change the `Type` to `All Traffic`. If the rule entry doesn't exist, add a new rule for it.
2. Find the managed node EC2 instance, which has the empty `Name` field and the value of the tag `eks:nodegroup-name` is `etl-job`. Similiar to the previous step, change the inbound rule which has the source from `SparkOnEKS-EksClusterspotInstanceSecurityGroup` and port is 443, ie. modify the `Type` from `HTTPS` to `All Traffic`. 
3. restart any broken pods in Jupyter namespace, such as `hub` pod.

```
$ kubectl get pod -n jupyter
$ kubectl delete pod <hub-random-string>  -n jupyter
```

## Submit a Spark job on a web interface

After finished the deployment, we can start to `submit Spark job` on [Argo](https://argoproj.github.io/). Argo is an open source container-native workflow tool to orchestrate parallel jobs on Kubernetes. Argo Workflows is implemented as a Kubernetes CRD (Custom Resource Definition), which triggers time-based and event-based workflows specified by a configuration file.

Take a look at the [sample job](https://github.com/tripl-ai/arc-starter/tree/master/examples/kubernetes/nyctaxi.ipynb) developed in Jupyter Notebook.  It uses a Spark Wrapper called [ARC framework](https://arc.tripl.ai/) to create an ETL job in a codeless, declarative way. The opinionated standard approach enables rapid application deployment, simplifies data pipeline build. Additionally, it makes [self-service analytics](https://github.com/melodyyangaws/aws-service-catalog-reference-architectures/blob/customize_ecs/ecs/README.md) possible to the business.

In this exmaple, we will extract the `New York City Taxi Data` from the [AWS Open Data Registry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/), ie. a public s3 bucket `s3://nyc-tlc/trip data`, transform the data from CSV to parquet file format, followed by a SQL-based data validation step, to ensure the typing transformation is done correctly. Finally, query the optimized data filtered by a flag column.

1. Find your Argo dashboard URL from the deployment output, something like this:
![](/images/0-argo-uri.png)

2. Go to the ARGO dashboard, Click on the `SUBMIT NEW WORKFLOW` button.
![](/images/1-argoui.png)

3. Replace the existing manifest by the following job definition, click `SUBMIT`.

```
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: nyctaxi-job-
  namespace: spark
spec:
  serviceAccountName: arcjob
  entrypoint: nyctaxi
  templates:
  - name: nyctaxi
    dag:
      tasks:
        - name: step1-query
          templateRef:
            name: spark-template
            template: smallJob
            clusterScope: true   
          arguments:
            parameters:
            - name: jobId
              value: nyctaxi 
            - name: image
              value: ghcr.io/tripl-ai/arc:latest
            - name: configUri
              value: https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes/nyctaxi.ipynb
            - name: parameters
              value: "--ETL_CONF_DATA_URL=s3a://nyc-tlc/trip*data --ETL_CONF_JOB_URL=https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes"

```
![](/images/2-argo-submit.png)

4. Click a pod (dot) on the dashboard to examine the job status and application logs.
![](/images/3-argo-log.png)


## Submit a Spark job via command line

We have included a second job manifest file and a Jupyter notebook, as an example of a complex Spark job to solve a real-world data problem. Let's submit it via a commmand line this time. 
<details>
<summary>manifest file</summary>
The [manifest file](/source/app_resources/scd2-job.yaml) defines where the Jupyter notebook file (job configuration) and input data are. 
</details>
<details>
<summary>Jupyter notebook</summary>
The [Jupyter notebook](/deployment/app_code/job/scd2_job.ipynb) specifies what exactly need to do in a data pipeline.
</details>

In general, a parquet file is immutable in a Data Lake. This exmaple will demostrate how to address the challenge and process data incrermtnally. It uses `Delta Lake`, which is an open source storage layer on top of parquet file, to bring the ACID transactions to Apache Spark and modern big data workloads. In this solution, we will build up a table to meet the [Slowly Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) requirement, and prove that how easy it is when ETL with a SQL first approach implemented in a configuration-driven architecture.


1.Open the `scd2 workflow job` manifest file, replace the S3 bucket by a correct name at each task sections. Either the code bucket name from your deployment output, or an existing datalake bucket passed in as a deployment parameter.

```
$ vi source/app_resources/scd2-workflow-job.yaml
```
![](/images/4-cfn-output.png)

![](/images/3-scd-bucket.png)

2.Before running command lines, you need to connect to the Amazon EKS cluster firstly. Get the connection command from the deployment output, something like this:

```
aws eks update-kubeconfig --name <EKS_cluster_name> --region <region> --role-arn arn:aws:iam::<account_number>:role/<role_name>
```
![](/images/0-eks-config.png)

3.Submit Arc Spark job

```
$ kubectl apply -f source/app_resources/scd2-workflow-job.yaml

# Delete before submit the same job again
$ kubectl delete -f source/app_resources/scd2-workflow-job.yaml
$ kubectl apply -f source/app_resources/scd2-workflow-job.yaml
```

<details>
<summary> 
Alternatively, submit the job without the extra deletion step by [Argo CLI](https://www.eksworkshop.com/advanced/410_batch/install/). 
</summary> 
```
$ argo submit source/app_resources/scd2-workflow-job.yaml -n spark --watch

# terminate the job that is running
$ argo delete scd2-job-<random_string> -n spark

```
*** Make sure to comment out a line in the manifest file before your submission. ***
![](/images/2-comment-out.png)
![](/images/2-argo-scdjob.png)
</details>

4.Go to your Argo dashboard by running the folowing command. Or copy the URL directy from your deployment output.

```
$ ARGO_URL=$(kubectl -n argo get ingress argo-server --template "{{ range (index .status.loadBalancer.ingress 0) }}{{ . }}{{ end }}")
$ echo ARGO DASHBOARD: http://${ARGO_URL}:2746
```

5.Check the job status and applications logs on the dashboard.
![](/images/3-argo-log.png)


## Create / test Spark job in Jupyter notebook

Apart from orchestrating Spark jobs with a declarative approach, we introduce a codeless, configuration-driven design for increasing data process productivity, by leveraging an open-source [data framework ARC](https://arc.tripl.ai/) for a SQL-centric ETL solution. We take considerations of the needs and expected skills from our customers in data, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

1.Login to Jupyter Hub. The default username is `sparkoneks`, or use your own login passed in as a dpeloyment parameter. The default password is `supersecret!`

```
$JHUB_URL=$(kubectl -n jupyter get ingress -o json | jq -r '.items[] | [.status.loadBalancer.ingress[0].hostname] | @tsv')
$echo jupyter hub login: http://${JHUB_URL}:8000

```

2.Start the default development environment. Use a big Jupyter Hub instance to author your ETL job if you prefer.

![](/images/3-jhub-login.png)

3.Upload a sample Arc-jupyter notebook from `deployment/app-code/job/scd2_job.ipynb`
![](/images/3-jhub-upload.png =80x100)

![](/images/3-jhub-open-notebook.png)

4.Execute each block and observe the result.

NOTE: the variable `${ETL_CONF_DATALAKE_LOC}` is set to a code bucket created by the deployment, and the IAM role attached to the Jupyter Hub is restricted to the S3 bucket. If you would like to connect to an existing bucket that contains real data, re-run the deployment with your `datalakebucket` name as a parameter, or simply add the bucket ARN to the IAM role 'SparkOnEKS-EksClusterjhubServiceAcctRole'.

```
cdk deploy SparkOnEKS -c env=develop --require-approval never -c env=develop --parameters datalakebucket=<real_data_bucket>
```

## Submit a native Spark job with Spot instance

As an addition of the solution, to meet customer's preference of running native Spark jobs, we wil demostrate how easy to submit a job in EKS. In this case, the Jupyter notebook still can be used, as an interactive development enviroment for PySpark apps. 

In Spark, driver is a single point of failure in data processing. If driver dies, all other linked components will be discarded as well. To achieve the optimal performance and cost, we will run the driver on a reliable managed EC2 instance on EKS, and the rest of executors will be on spot instances.

1.[OPTIONAL] Run a dummy container to check source code files.

```
$ kubectl run --generator=run-pod/v1 jump-pod --rm -i --tty --serviceaccount=nativejob --namespace=spark --image <account_number>.dkr.ecr.<region>.amazonaws.com/arc:latest sh

# after login to the container, validate the files
# make sure the service account is `nativejob` and the lifecycle value is `Ec2Spot` in the executor template
sh-5.0# ls 
sh-5.0# cat executor-pod-template.yaml
sh-5.0# exit

```
2.Copy the S3 bucket name from the deployment output

![](/images/4-cfn-output.png)

3.Modify the job manifest file `native-spark-job.yaml` 
by changing the destination bucket.

![](/images/4-spark-output-s3.png)


4.Submit the native Spark job

```
$ kubectl apply -f source/app_resources/TEST-native-job.yaml

```
5.Go to SparkUI to check the job progress and performance

```
$ driver=$(kubectl get pod -n spark -l spark-role=driver -o json | jq -r '.items[] | [.metadata.name] | @tsv')
$ kubectl port-forward $driver 4040:4040 -n spark

# go to your web browser, type in `localhost:4040`

```
6. Examine the auto-scaling and multiAZs

```
# watch the number of EC2 instances. The job requests 5 exectuors with 5 new Spot instances. The auto-scaling will be triggered across multiple zones and different instance types.
$ kubectl get node --label-columns=lifecycle,topology.kubernetes.io/zone
$ kubectl get pod -n spark
```
![](/images/4-auto-scaling.png)

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
 * `cdk destroy`     delete the stack deployed earlier
 * `kubectl get pod -n spark`                         list all jobs running in the Spark namespace
 * `kubectl get svc -n argo`                          get argo dashboard URL
 * `kubectl get svc -n jupyter`                       get Jupyterhub's URL
 * `argo submit source/app_resources/spark-job.yaml`  submit a spark job from a manifest file
 * `argo list --all-namespaces`                       show jobs from all namespaces
 * `kubectl delete pod --all -n spark`                delete all jobs submitted in the Spark namespace
* `kubectl apply -f source/app_resources/spark-template.yaml` submit a reusable job template for Spark applications

