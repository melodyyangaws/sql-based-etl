# SQL-based ETL with Apache Spark on Amazon EKS
This is a project developed with Python [CDK](https://docs.aws.amazon.com/cdk/latest/guide/home.html) for the solution - SQL based ETL with a declarative framework powered by Apache Spark. 

We introduce a quality-aware design to increase data process productivity, by leveraging an open-source data framework [Arc](https://arc.tripl.ai/) for a user-centered declarative ETL solution. Additionally, we take considerations of the needs and expected skills from customers in data analytics, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

## Architecture Overview
![Architecture](images/architecture.png)

## Prerequisites 
1. Python 3.6 or later. You can find information about downloading and installing Python [here](https://www.python.org/downloads/).
2. AWS CLI version 1 
  Windows: [MSI installer](https://docs.aws.amazon.com/cli/latest/userguide/install-windows.html#install-msi-on-windows)
  Linux, macOS or Unix: [Bundled installer](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html#install-macosos-bundled)
3. The AWS CDK uses Node.js (>= 10.3.0). To install Node.js visit the[website](https://nodejs.org/).
  Verify that you have a compatible version:

  ```
  node --version
  ```

## Deploy Infrastructure

### Clone the project

```
git clone https://github.com/melodyyangaws/sql-based-etl
cd sql-based-etl

```

### Install kubernetes command tool on MAC
If you are running Linux / Windows, please see the official [argo doc](https://github.com/argoproj/argo/releases) & [kubectl doc](https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl-on-windows) to find the download links.

```
./deployment/setup_cmd_tool.sh
```
Additionally, you might need the [CDK toolkit](https://cdkworkshop.com/15-prerequisites/500-toolkit.html) to deploy the solution. Please igore the installation, if you intend to deploy via AWS CloudFormation.


### Prepare deployment
The following bash script will help you to prepare the deployment in your AWS account. It creates two environment variables `$CDK_DEPLOY_ACCOUNT` and `$CDK_DEPLOY_REGION` based on your input. Assume your AWS CLI can communicate with services in the `CDK_DEPLOY_ACCOUNT` as a default profile, if not, run the following configuration to setup your AWS account access.

```
aws configure
```
The ECR repository name `arc` is fixed, however, it can be changed. Don't forget to correct your ECR endpoints in [example ETL jobs](/source/example) if you want to use a different ECR repo name.

```
./deployment/pull_and_push_ecr.sh <your_region> <your_account_number> 'arc'

# use `skip_ecr` flag, when rerun the script without a docker push 
./deployment/pull_and_push_ecr.sh <your_region> <your_account_number> 'arc' 'skip_ecr'
```

### Create a virtualenv
This project is set up like a standard Python project. The `cdk.json` file tells where the application entry point is.

``` 
python3 -m venv .env
```
If you are in a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```
After the virtualenv is created, you can use the followings to activate your virtualenv and install the required dependencies.

```
source .env/bin/activate
pip install -e source
```
### Deploy the whole stack 
<span style="color: red;">Make sure you are in the source directory</span>

With two optional parameters `jhubuser` & `datalakebucket`, the deployment will take up to 30 minutes to complete. See the `troubleshooting` section if you have a problem during the deployment.

### Scenario1: deploy with default settings (recommended)

```
cd source
cdk deploy
```
### Scenario2: choose your own login name for Jupyter
To follow the best practice in security, a service account in EKS will be created dynamically, based on your deployment parameter. An IAM role with the least privilege will be assigned to the new service account. 

```
cd source
cdk deploy --parameters jhubuser=<random_login_name>
```
### Scenario3: use your own S3 bucket
By default, the deployment creates a new S3 bucket containing sample data and ETL job config. 
If you want to use your own data to build an ETL, replace the `<existing_datalake_bucket>` to your S3 bucket. `NOTE: your bucket must be in the same region as the deployment region.`

```
cd source
cdk deploy --parameters jhubuser=<random_login_name> --parameters datalakebucket=<existing_datalake_bucket>
```
## Troubleshooting

1. If you see the issue `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1123)`, most likely it means no default certificate authority for your Python installation on OSX. Refer to the [answer](https://stackoverflow.com/questions/52805115/0nd installing `Install Certificates.command` should fix your local environment. Otherwise, use [Cloud9](https://aws.amazon.com/cloud9/details/) to deploy the CDK instead.

2. If an error says `SparkOnEKS failed: Error: This stack uses assets, so the toolkit stack must be deployed to the environment (Run "cdk bootstrap aws://YOUR_ACCOUNT_NUMBER/REGION")` , it means it is the first time you deploy an AWS CDK app into an environment (account/region), you’ll need to install a “bootstrap stack”. This stack includes resources that are needed for the toolkit’s operation. For example, the stack includes an S3 bucket that is used to store templates and assets during the deployment process.

Run the bootstrap command:

```
cdk bootstrap aws://<YOUR_ACCOUNT_NUMBER>/<YOUR_REGION>
```

3. If an error appears during the CDK deployment: `Failed to create resource. IAM role’s policy must include the "ec2:DescribeVpcs" action`, it means you have reach the quota limits of Amazon VPC resources per Region in your AWS account. Please deploy to a different region or a different account.


## Connect to EKS cluster

Before running any commands against a new EKS cluster, you need to connect to it first. Get the connection command from your deployment output, something like this:

```
aws eks update-kubeconfig --name <EKS_cluster_name> --region <region> --role-arn arn:aws:iam::<account_number>:role/<role_name>
```
![](/images/0-eks-config.png)


## Submit a Spark job on web interface

Once the CDK deployment is finished, let's start to `submit a Spark job` on [Argo](https://argoproj.github.io/) console. For the best practice in security, your authentication token will be refreshed about 10mins. Simply regenerate your token and login again. 

<details>
<summary>Argo definition</summary>
An open source container-native workflow tool to orchestrate parallel jobs on Kubernetes. Argo Workflows is implemented as a Kubernetes CRD (Custom Resource Definition). It triggers time-based or event-based workflows via configuration files.
</details>

Firstly, let's take a look at a [sample job](https://github.com/tripl-ai/arc-starter/tree/master/examples/kubernetes/nyctaxi.ipynb) developed in Jupyter Notebook.  It uses a thin Spark wrapper called [Arc](https://arc.tripl.ai/) to create an ETL job in a codeless, declarative way. The opinionated standard approach enables the shift in data ownership to analysts who understand business problem better, simplifies data pipeline build and enforces the best practice in Data DevOps or GitOps. Additionally, we can apply a product-thinking to the declarative ETL as a [self-service service](https://github.com/melodyyangaws/aws-service-catalog-reference-architectures/blob/customize_ecs/ecs/README.md), which is highly scalable, predictable and reusable.

In this example, we extract the `New York City Taxi Data` from [AWS Open Data Registry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/), ie. a public S3 bucket `s3://nyc-tlc/trip data`, then transform the data from CSV to parquet file format, followed by a SQL based validation step to ensure the typing transformation is done correctly. Finally, query the optimized data filtered by a flag column.

1. Click the Argo dashboard URL from your deployment output, something like this:

![](/images/0-argo-uri.png)

OPTIONAL: type `argo server` in command line tool to run it locally to avoid the token timeout, the URL is `http://localhost:2746`.

2. To be able to login, get a token by the following command, and paste it to your website. Make sure you have connected to the EKS Cluster via a command previously.

```
argo auth token
```
![](/images/1-argologin.png)

3. After login, click `SUBMIT NEW WORKFLOW`. 

![](/images/1-argoui.png)

4. Replace the manifest by the following, then `SUBMIT`. Or simply upload the sample file from `[source/example/nyctaxi-job-scheduler.yaml]`

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
            template: sparkLocal
            clusterScope: true   
          arguments:
            parameters:
            - name: jobId
              value: nyctaxi  
            - name: tags
              value: "project=sqlbasedetl, owner=myowner, costcenter=66666"  
            - name: configUri
              value: https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes/nyctaxi.ipynb
            - name: parameters
              value: "--ETL_CONF_DATA_URL=s3a://nyc-tlc/trip*data --ETL_CONF_JOB_URL=https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes"

```
![](/images/2-argo-submit.png)

4. Click a pod (dot) on the dashboard to examine the job status and application logs. The ETL job/Jupyter notebook can be found at ![/source/example/nyctaxi-job.ipynb](/source/example/nyctaxi-job.ipynb)

![](/images/3-argo-log.png)


## Submit a Spark job via command line

We have included a second job manifest file and a Jupyter notebook, as an example of a complex Spark job to solve a real-world data problem. Let's submit it via a command line this time. 
<details>
<summary>manifest file</summary>
The [manifest file](/source/example/scd2-job-scheduler.yaml) defines where the Jupyter notebook file (job configuration) and input data are. 
</details>
<details>
<summary>Jupyter notebook</summary>
The [Jupyter notebook](/source/example/scd2-job.ipynb) specifies what exactly need to do in a data pipeline.
</details>

In general, parquet files are immutable in Data Lake. This example will demonstrate how to address the problem and process data incrementally. It uses `Delta Lake`, an open source storage layer on top of parquet file, to bring the ACID transactions to your modern data architecture. In the example, we will build up a table to support the [Slowly Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) format. You will have a hands-on experience to do the SQL-based ETL to achieve the incremental data load in Data Lake.


1. Open the [scd2 job scheduler file](source/example/scd2-job-scheduler.yaml) on your computer, replace the S3 bucket placeholder {{codeBucket}}. Either copy & paste the code bucket name from your deployment output, or use the existing s3 bucket name passed in as a parameter to your deployment previously.

```
vi source/example/scd2-job-scheduler.yaml
```
![](/images/4-cfn-output.png)
![](/images/3-scd-bucket.png)


2. Submit Arc Spark job

```
# Make sure you are in the project root directory
cd sql-based-etl-with-apache-spark-on-amazon-eks

# Start a data pipeline containing 3 spark jobs
kubectl apply -f source/example/scd2-job-scheduler.yaml

# run the CLI to watch the progress, or go to Argo site.
kubectl get pod -n spark
``

<details>
<summary> 
Alternatively, submit the job with Argo CLI. 
</summary> 

```
argo submit source/example/scd2-job-scheduler.yaml -n spark --watch
```
*** Ensure to comment out a line in the manifest file before your submission. ***
![](/images/2-comment-out.png)
![](/images/2-argo-scdjob.png)
</details>


3. Go to the Argo dashboard via an URL link of your deployment output 

![](/images/0-argo-uri.png)


4. Watch the job status and applications logs
![](/images/3-argo-job-dependency.png)


5. As a data pipeline output, you will see a [Delta Lake](https://delta.io/) table is created in [Athena](https://console.aws.amazon.com/athena/). Run the query in Athena console, to check if the table is a SCD2 type.

```
SELECT * FROM default.contact_snapshot WHERE id=12
```

## Build & test Spark job in Jupyter

Apart from orchestrating Spark jobs in a declarative approach, we introduce a configuration-driven design to increase the data process productivity, by leveraging an open-source [data framework Arc](https://arc.tripl.ai/) for a SQL-centric ETL solution. We take considerations of the needs and expected skills from our customers, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency. Furthermore, we enforce the best practice in Data DevOps. Ensure every single ETL artefact are source & version controlled. Git should be the single source of truth for your ETL development and deployment. 

NOTE: To follow the security best practice, we timeout your Jupyter session every 15 minutes. You may lose your work, if it hasn't been saved back to your GIT repository. To reconfigure the Jupyter, such as timeout or add your own source repository URL, check out the file `[source/app_resources/jupyter-values.yaml]`

1. Login to JupyterHub web soncole:

![](/images/3-jupyter-url.png)

* username -  `sparkoneks`, or use your own login name defined at the deployment earlier. 
* password - see below command.

```
JHUB_PWD=$(kubectl -n jupyter get secret jupyter-external-secret -o jsonpath="{.data.password}" | base64 --decode)
echo -e "\njupyter login: $JHUB_PWD"
```

2. Start the default IDE (development environment). Use the bigger instance to author your ETL job if needed.

![](/images/3-jhub-login.png)


3. Locate a sample Arc-jupyter notebook at `source/example/scd2-job.ipynb`. Double click the file name to open the notebook. 

To demonstrate the DevOps best practice, we clone the latest source files from the Git repository to your Jupyter instance each time when you login. In this example, you have granted permission to be able to download notebooks to your local computer before the 15mins timeout. 

![](/images/3-jhub-open-notebook.png)

In the real practice, you must check-in all the changes to your source repository, in order to save and trigger your ETL pipeline.

![](/images/3-git-commit-notebook.png)


4. Execute each block and observe the result.

NOTE: the variable `${ETL_CONF_DATALAKE_LOC}` is set to a code bucket or an existing DataLake S3 bucket specified at the deployment. An IAM role attached to the JupyterHub is controlling the data access to the S3 bucket. If you want to connect to a different bucket that wasn't specified at the deployment, you will get an access deny error. For the testing purpose, simply add the bucket ARN to the IAM role 'SparkOnEKS-EksClusterjhubServiceAcctRole'.


5. Now let's take a look at the output table in [Athena](https://console.aws.amazon.com/athena/), to check if the table is populated correctly.

```
SELECT * FROM default.deltalake_contact_jhub WHERE id=12
```

## Submit a native Spark job with a Kubernetes operator

In an addition, to meet customer's need to run a native Spark job, we will reuse the same Arc docker image. Without any changes, let's directly submit a native Spark application defined in a declarative manner. In other words, we will use the popular Kubernetes operator for Apache Spark, [Spark Operator](https://operatorhub.io/operator/spark-gcp) for short, to specify and run a job, which is as easy as running other workloads in Kubernetes. We will save lots of efforts on the DevOps operation, as the way of deploying Spark application follows the same declarative approach in Kubernetes, which is consistent with other business applications deployment.

The example demonstrates:
* Saving cost with Amazon EC2 Spot instance type
* Dynamically scale a Spark application - [Dynamic Resource Allocation](https://spark.apache.org/docs/3.0.0-preview/job-scheduling.html#dynamic-resource-allocation)
* Self-recovery after losing a Spark driver
* Monitor the job on a Spark WebUI


1. Modify the job manifest file [native-spark-job-scheduler.yaml](source/example/native-spark-job-scheduler.yaml) stored on your computer, ie. replace the placeholder {{codeBucket}}.

![](/images/4-cfn-output.png)
![](/images/4-spark-output-s3.png)


2. Submit the job. 

```
kubectl apply -f source/example/native-spark-job-scheduler.yaml
kubectl get pod -n spark
```

3. Go to SparkUI to check your job progress and performance. Make sure the driver pod exists.

```
kubectl port-forward word-count-driver 4040:4040 -n spark

# go to `localhost:4040` from your web browser
```

4. [OPTIONAL] The job takes 10 minutes to finish. Let's test if the Spark job is fault tolerant.

Spark application has a build-in self-recovery mechanism. The nature of Kubernetes has made it much easier, by leveraging its HA feature with multi-AZ support.

In Spark, driver is a single point of failure in data processing. If driver dies, all other linked components will be discarded as well.Outside of k8s, it requires extra effort to set up a rerun job to cope with the situation. It is simpler in EKS in our example. 

Let's manually kill the driver first: 

```
kubectl delete -n spark pod word-count-driver --force

# has your driver come back immediately?
kubectl get po -n spark
```

Now kill one of executors: 

```
# replace to your pod name with the amazon-reviews-word-count prefix
kubectl delete -n spark pod amazon-reviews-word-count-51ac6d777f7cf184-exec-1 --force

# has it come back with a different number suffix? 
kubectl get po -n spark
```

5. [OPTIONAL] Check Spot instance usage and cost savings

As mentioned before, if Spark's driver dies, the entire application will fail. To achieve the optimal cost performance, we have placed the driver on a reliable On-Demand managed EC2 instance in EKS, and the rest of executors is on spot instances. 

The example job starts with triggering 5 spot instances, running 10 executors(k8s pods). After a few minutes, it intelligently scales up to 10 spot, that is 20 executors in total. Once the job is completed, the Spark cluster will be automatically scaled down from 10 to 1 spot. Check your [Spot Request](https://console.aws.amazon.com/ec2sp/v2/) console -> Saving Summary, to find out how much running cost have you just saved.

![](/images/4-spot-console.png)

6. [OPTIONAL] Explore EKS feature of Auto Scaling with Multi-AZ support, and Spark's Dynamic Allocation.

This job will end up with 20 Spark executors/pods on 10 spot EC2 instances for about 10 minutes. Based on the resource allocation defined by the job manifest file, it runs two executors per EC2 spot instance. As soon as the job is kicked in, you will see the autoscaling is triggered within seconds. It scales the EKS cluster from 1 spot compute node to 5, then from 5 to 10 fired up by Spark's DynamicAllocation.

The auto-scaling is configured to be balanced within two AZs. Depending on your business requirement, you can fit a job into a single AZ if needed.

```
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
 * `kubectl get pod -n spark`                         list running Spark jobs
 * `argo submit source/example/nyctaxi-job-scheduler.yaml`  submit a spark job via Argo
 * `argo list --all-namespaces`                       show all jobs scheduled via Argo
 * `kubectl delete pod --all -n spark`                delete all Spark jobs
 * `kubectl apply -f source/app_resources/spark-template.yaml` create a reusable Spark job template

## Clean up
Go to the repo's root directory, and run the clean up script.

```
cd sql-based-etl-with-apache-spark-on-amazon-eks
./deployment/delete_all.sh

```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE.txt) file.