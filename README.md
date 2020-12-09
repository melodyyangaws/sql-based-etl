# SQL-based ETL with Apache Spark on Amazon EKS
This is a project developed with Python CDK for the solution - SQL based ETL with a declarative framework powered by Apache Spark. 

We introduce a quality-aware design to increase data process productivity, by leveraging an open-source data framework [Arc](https://arc.tripl.ai/) for a user-centered declarative ETL solution. Additionally, we take considerations of the needs and expected skills from customers in data analytics, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

## Prerequisites 
Python is needed in this project. Specifically, you will need version 3.6 or later. You can find information about downloading and installing Python [here](https://www.python.org/downloads/). Additionally you will need to have the Python package installer (pip) installed. See installation instructions [here](https://pypi.org/project/pip/).

If you use Windows, be sure Python is on your PATH. 


## Deploy Infrastructure

Clone the project.

```
git clone https://github.com/melodyyangaws/sql-based-etl.git
cd sql-based-etl

```

Build Arc docker image and push it to your container registry ECR. 
The following bash script will help you to prepare the deployment in your AWS environment. Replace the placeholders by your own information.

```
bash deployment/pull_and_push_ecr.sh <your_region> <your_account_number> 'arc' 1
```

Install kubernetes tools on MAC.
If you are running Linux / Windows, please see the [official docs](https://github.com/argoproj/argo/releases) for the download links.

```
bash deployment/setup_cmd_tool.sh
```

Manually create a virtualenv on MacOS and Linux.
This project is set up like a standard Python project. The `cdk.json` file tells where the application entry point is.

``` 
python3 -m venv .env
```
If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```
After the virtualenv is created, you can use the following step to activate your virtualenv.

```
source .env/bin/activate
```
Once the virtualenv is activated, you can install the required dependencies.

```
pip install -r source/requirements.txt
```
Finally deploy the stack. It takes two optional parameters `jhubuser` & `datalakebucket`.

```
# Scenario1: Deploy with default settings (recommended)

cdk deploy SparkOnEKS --require-approval never -c env=develop

# Scenario2: Create a username to login Jupyter hub. 
# Otherwise, login by a default name.

cdk deploy SparkOnEKS --require-approval never -c env=develop --parameters jhubuser=<random_login_name>

# Scenario3: by default, the `datalakebucket` is pointing to a S3 bucket created by the solution.
# if you prefer to use an existing bucket that contains real data, replace the placeholder by your bucket name. 
# NOTE: the bucket must be in the same region as the solution deployment region.

cdk deploy SparkOnEKS --require-approval never -c env=develop --parameters jhubuser=<random_login_name> --parameters datalakebucket=<existing_datalake_bucket>

```
## Troubleshooting

1. If you see the issue `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1123)`, most likely it means no default certificate authority for your Python installation on OSX. Refer to the [answer](https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate) and installing `Install Certificates.command` should fix your local environment. Otherwise, use Cloud9 to deploy the CDK instead.

2. If an error says `SparkOnEKS failed: Error: This stack uses assets, so the toolkit stack must be deployed to the environment (Run "cdk bootstrap aws://YOUR_ACCOUNT_NUMBER/REGION")` , it means it is the first time you deploy an AWS CDK app into an environment (account/region), you’ll need to install a “bootstrap stack”. This stack includes resources that are needed for the toolkit’s operation. For example, the stack includes an S3 bucket that is used to store templates and assets during the deployment process.

You can use the cdk bootstrap command to install the bootstrap stack into an environment:

```
cdk bootstrap aws://<YOUR_ACCOUNT_NUMBER>/<YOUR_REGION> -c develop
```

## Connect to EKS cluster

Before running any commands against the EKS cluster newly deployed, you need to connect to it firstly. Get the connection command from your deployment output, something like this:

```
aws eks update-kubeconfig --name <EKS_cluster_name> --region <region> --role-arn arn:aws:iam::<account_number>:role/<role_name>
```
![](/images/0-eks-config.png)


## Submit a Spark job on web interface

After finished the deployment, we can start to `submit Spark job` on [Argo](https://argoproj.github.io/). Argo is an open source container-native workflow tool to orchestrate parallel jobs on Kubernetes. Argo Workflows is implemented as a Kubernetes CRD (Custom Resource Definition), which triggers time-based and event-based workflows specified by a configuration file.

Take a look at the [sample job](https://github.com/tripl-ai/arc-starter/tree/master/examples/kubernetes/nyctaxi.ipynb) developed in Jupyter Notebook.  It uses a thin Spark wrapper called [Arc](https://arc.tripl.ai/) to create an ETL job in a codeless, declarative way. The opinionated standard approach enables rapid application deployment, simplifies data pipeline build. Additionally, it makes [self-service analytics](https://github.com/melodyyangaws/aws-service-catalog-reference-architectures/blob/customize_ecs/ecs/README.md) possible to the business.

In this example, we will extract the `New York City Taxi Data` from the [AWS Open Data Registry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/), ie. a public s3 bucket `s3://nyc-tlc/trip data`, transform the data from CSV to parquet file format, followed by a SQL-based data validation step, to ensure the typing transformation is done correctly. Finally, query the optimized data filtered by a flag column.

1. Find your Argo dashboard URL from the deployment output, something like this:
![](/images/0-argo-uri.png)

NOTE: if the URL is not available, run it locally by type in `argo server` in your commandline tool.

2. Go to the ARGO dashboard, click on the `SUBMIT NEW WORKFLOW` button. If you are running Argo locally, type in `http://localhost:2746` in your web browser.

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

We have included a second job manifest file and a Jupyter notebook, as an example of a complex Spark job to solve a real-world data problem. Let's submit it via a command line this time. 
<details>
<summary>manifest file</summary>
The [manifest file](/source/example/scd2-workflow-job.yaml) defines where the Jupyter notebook file (job configuration) and input data are. 
</details>
<details>
<summary>Jupyter notebook</summary>
The [Jupyter notebook](/source/example/scd2_job.ipynb) specifies what exactly need to do in a data pipeline.
</details>

In general, a parquet file is immutable in a Data Lake. This example will demonstrate how to address the problem and process data incrementally. It uses `Delta Lake`, which is an open source storage layer on top of parquet file, to bring the ACID transactions to your modern data architecture. In the example data pineline, we will build up a table to support the [Slowly Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) format, to demostrate how easy to do the ETL with a SQL first approach implemented in a configuration-driven architecture.


1.Open the [scd2 job manifest file](source/example/scd2-workflow-job.yaml) on your computer, replace the S3 bucket placeholders at each task sections. Either copy & paste the code bucket name from your deployment output, or use the existing s3 bucket name passed in as a parameter to your deployment previously.

```
vi source/example/scd2-workflow-job.yaml
```
![](/images/4-cfn-output.png)

![](/images/3-scd-bucket.png)


2.Submit Arc Spark job

```
# Make sure you are in the project root directory
cd sql-based-etl

# Start a data pipeline containing 3 spark jobs
kubectl apply -f source/example/scd2-workflow-job.yaml

# Delete before submit the same job again
kubectl delete -f source/example/scd2-workflow-job.yaml
kubectl apply -f source/example/scd2-workflow-job.yaml
```

<details>
<summary> 
Alternatively, submit the job with Argo CLI. 
</summary> 

```
argo submit source/example/scd2-workflow-job.yaml -n spark --watch

# terminate the job that is running
argo delete scd2-job-<random_string> -n spark

```
*** Make sure to comment out a line in the manifest file before your submission. ***
![](/images/2-comment-out.png)
![](/images/2-argo-scdjob.png)
</details>

4.Go to your Argo dashboard by running the following command. Or copy the URL directly from your deployment output.

```
ARGO_URL=$(kubectl -n argo get ingress argo-server --template "{{ range (index .status.loadBalancer.ingress 0) }}{{ . }}{{ end }}")
echo ARGO DASHBOARD: http://${ARGO_URL}:2746
```

5.Check the job status and applications logs on the dashboard.
![](/images/3-argo-log.png)


## Developo & test Spark job in Jupyter notebook

Apart from orchestrating Spark jobs with a declarative approach, we introduce a configuration-driven design for increasing data process productivity, by leveraging an open-source [data framework Arc](https://arc.tripl.ai/) for a SQL-centric ETL solution. We take considerations of the needs and expected skills from our customers in data, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

1.Login to Jupyter Hub. 
The default username is `sparkoneks`, or use your own login name defined at the deployment earlier:

```
JHUB_PWD=$(kubectl -n jupyter get secret jupyter-external-secret -o jsonpath="{.data.password}" | base64 --decode)
JHUB_URL=$(kubectl -n jupyter get ingress -o jsonpath="{.items[].status.loadBalancer.ingress[0].hostname}")
echo -e "\njupyter login: $JHUB_PWD \njupyter hub URL: http://${JHUB_URL}:8000"

#if the jupyter hub URL returned http://:8000, we can run the user interface locally
POD_NAME=$(kubectl get po -n jupyter -l component=proxy -o jsonpath="{range .items[*]}{@.metadata.name}{end}")
kubectl port-forward $POD_NAME 8000:8000 -n jupyter 

# type http://127.0.0.1:8000 in your web browser
```

2.Start the default development environment. Use a biggre instance to author your ETL job if you prefer.

![](/images/3-jhub-login.png)

3.Upload a sample Arc-jupyter notebook from `source/example/scd2_job.ipynb`

![](/images/3-jhub-open-notebook.png)

4.Execute each block and observe the result.

NOTE: the variable `${ETL_CONF_DATALAKE_LOC}` is set to a code bucket or your existing bucket configured by the deployment, ie. an IAM role attached to the Jupyter Hub is designed to access this bucket only. If you would like to connect to another bucket that wansn't configured by the deployment process, you will get an error with access deny. In this case, simply add the bucket ARN to the IAM role 'SparkOnEKS-EksClusterjhubServiceAcctRole'.


## Submit a native Spark job with Spot instance

As an addition of the solution, to meet customer's preference of running native Spark jobs, we will demonstrate how easy to submit a job with a fat jar file in EKS. In this case, the Jupyter notebook still can be used, as an interactive development environment for PySpark apps. 

In Spark, driver is a single point of failure in data processing. If driver dies, all other linked components will be discarded as well. To achieve the optimal performance and cost, we will run the driver on a reliable managed EC2 instance on EKS, and the rest of executors will be on spot instances.

1.[OPTIONAL] Run a dummy container to validate template files.

```
kubectl run --generator=run-pod/v1 jump-pod --rm -i --tty --serviceaccount=nativejob --namespace=spark --image <your_account_number>.dkr.ecr.<your_region>.amazonaws.com/arc:latest sh

# after login to the container, validate a file
# ensure the service account is `nativejob` and the lifecycle value is `Ec2Spot` in the template
sh-5.0# ls 
sh-5.0# cat executor-pod-template.yaml
sh-5.0# exit

```
2.Copy the S3 bucket name from the deployment output

![](/images/4-cfn-output.png)

3.Modify the job manifest file [native-spark-job.yaml](source/example/native-spark-job.yaml) 
by replacing the bucket name placeholders.

![](/images/4-spark-output-s3.png)


4.Submit the native Spark job

```
kubectl apply -f source/example/native-spark-job.yaml

```
5.Go to SparkUI to check your job progress and performance

```
driver=$(kubectl get pod -n spark -l spark-role=driver -o jsonpath="{.items[*].metadata.name}")
kubectl port-forward $driver 4040:4040 -n spark

# type in `localhost:4040` to go to your web browser

```
6. Examine the auto-scaling and multiAZs

```
# the job requests 5 executors with 5 new Spot instances. 
# the auto-scaling will be triggered across multiple AZs.

kubectl get node --label-columns=lifecycle,topology.kubernetes.io/zone
kubectl get pod -n spark
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
 * `kubectl get ingress -n argo`                      get argo dashboard URL
 * `kubectl get ingress -n jupyter`                   get Jupyterhub's URL
 * `argo submit source/example/spark-arc-job.yaml`    submit a spark job from a manifest file
 * `argo list --all-namespaces`                       show jobs from all namespaces
 * `kubectl delete pod --all -n spark`                delete all jobs submitted in the Spark namespace
 * `kubectl apply -f source/app_resources/spark-template.yaml` submit a reusable job template for Spark applications

## Clean up
* Delete a s3 bucket with the prefix of `sparkoneks-codebucket`, because AWS CloudFormation cannot delete a non-empty Amazon S3 bucket automatically. 
* Delete cloud resources by the following CDK CLI

```
cdk destroy SparkOnEKS -c env=develop --require-approval never
``` 
If any error ocurrs, go to Cloudformation console in your AWS account, manually delete templates on the console.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.