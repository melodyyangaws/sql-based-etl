# SQL-based ETL with Apache Spark on Amazon EKS
This is a project developed with Python [CDK](https://docs.aws.amazon.com/cdk/latest/guide/home.html) for the solution - SQL based ETL with a declarative framework powered by Apache Spark. 

We introduce a quality-aware design to increase data process productivity, by leveraging an open-source data framework [Arc](https://arc.tripl.ai/) for a user-centered declarative ETL solution. Additionally, we take considerations of the needs and expected skills from customers in data analytics, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

## Prerequisites 
Python is needed in this project. Specifically, you will need version 3.6 or later. You can find information about downloading and installing Python [here](https://www.python.org/downloads/). Additionally you will need to have the Python package installer (pip) installed. See installation instructions [here](https://pypi.org/project/pip/).

If you use Windows, be sure Python is on your PATH. 


## Deploy Infrastructure

### Clone the project

```
git clone https://github.com/awslabs/sql-based-etl-with-apache-spark-on-amazon-eks.git
cd sql-based-etl-with-apache-spark-on-amazon-eks

```

### Install kubernetes command tool on MAC
If you are running Linux / Windows, please see the official [argo doc](https://github.com/argoproj/argo/releases) & [kubectl doc](https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl-on-windows) to find the download links.

```
./deployment/setup_cmd_tool.sh
```
Additionally, you might need the [CDK toolkit](https://cdkworkshop.com/15-prerequisites/500-toolkit.html) to deploy the solution. Please igore the installation, if you intend to deploy the solution via AWS CloudFormation.


### Prepare deployment
The following bash script will help you to prepare the deployment in your AWS account. It creates two environment variables `$CDK_DEPLOY_ACCOUNT` and `$CDK_DEPLOY_REGION` based on your input.

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

Once the CDK deployment is completed, we can start to `submit a Spark job` on [Argo](https://argoproj.github.io/).

<details>
<summary>Argo definition</summary>
An open source container-native workflow tool to orchestrate parallel jobs on Kubernetes. Argo Workflows is implemented as a Kubernetes CRD (Custom Resource Definition). It triggers time-based or event-based workflows via configuration files.
</details>

Firstly, let's take a look at a [sample job](https://github.com/tripl-ai/arc-starter/tree/master/examples/kubernetes/nyctaxi.ipynb) developed in Jupyter Notebook.  It uses a thin Spark wrapper called [Arc](https://arc.tripl.ai/) to create an ETL job in a codeless, declarative way. The opinionated standard approach enables rapid application development, and simplifies data pipeline build. Additionally, it makes [self-service analytics](https://github.com/melodyyangaws/aws-service-catalog-reference-architectures/blob/customize_ecs/ecs/README.md) possible.

In this example, we will extract the `New York City Taxi Data` from [AWS Open Data Registry](https://registry.opendata.aws/nyc-tlc-trip-records-pds/), ie. a public S3 bucket `s3://nyc-tlc/trip data`, then transform the data from CSV to parquet file format, followed by a SQL-based validation step, to ensure the typing transformation is done correctly. Finally, query the optimized data filtered by a flag column.

1. Click the Argo dashboard URL from your deployment output, something like this:

![](/images/0-argo-uri.png)

OPTIONAL: type `argo server` in command line tool to run it locally, the URL is `http://localhost:2746`.

2. To be able to login, get a token by the following command, and paste it to the Argo website. Make sure you have connected to the EKS Cluster.

```
argo auth token
```
![](/images/1-argologin.png)

3. After login, click `SUBMIT NEW WORKFLOW`. 

![](/images/1-argoui.png)

4. Replace the existing manifest by the following, then `SUBMIT`. Or simply upload the sample file from `[source/example/nyctaxi-job-scheduler.yaml]`

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
            - name: environment
              value: test    
            - name: tags
              value: "project=sqlbasedetl, owner=myang, costcenter=66666"  
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

In general, parquet files are immutable in Data Lake. This example will demonstrate how to address the problem and process data incrementally. It uses `Delta Lake`, an open source storage layer on top of parquet file, to bring the ACID transactions to your modern data architecture. In the example, we will build up a table to support the [Slowly Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) format, to demonstrate how easy to do the ETL with a SQL first approach implemented in a configuration-driven way.


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

# Delete before submit the same job again
kubectl delete -f source/example/scd2-job-scheduler.yaml
kubectl apply -f source/example/scd2-job-scheduler.yaml
```

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


3. Go to the Argo dashboard via the URL link from deployment output 

![](/images/0-argo-uri.png)


4. Check the job status and applications logs
![](/images/3-argo-job-dependency.png)


5. As an output of the ETL pipeline, you will see a [Delta Lake](https://delta.io/) table is created in [Athena](https://console.aws.amazon.com/athena/) by leveraging Glue Catalog. Run the following query to check if the table is a SCD2 type.

```
SELECT * FROM default.contact_snapshot WHERE id=12
```

## Develop & test Spark job in Jupyter

Apart from orchestrating Spark jobs with a declarative approach, we introduce a configuration-driven design for increasing data process productivity, by leveraging an open-source [data framework Arc](https://arc.tripl.ai/) for a SQL-centric ETL solution. We take considerations of the needs and expected skills from our customers in data, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

1. Login to JupyterHub user interface:

![](/images/3-jupyter-url.png)

username -  `sparkoneks`, or use your own login name defined at the deployment earlier. 
password - see below command.

```
JHUB_PWD=$(kubectl -n jupyter get secret jupyter-external-secret -o jsonpath="{.data.password}" | base64 --decode)
echo -e "\njupyter login: $JHUB_PWD"
```

2. Start the default IDE (development environment). Use the bigger instance to author your ETL job if needed.

![](/images/3-jhub-login.png)


3. Upload a sample Arc-jupyter notebook from `source/example/scd2-job.ipynb`. Once uploaded, double click the file name to open the notebook.

![](/images/3-jhub-open-notebook.png)


4. Execute each block and observe the result.

NOTE: the variable `${ETL_CONF_DATALAKE_LOC}` is set to a code bucket or an existing DataLake S3 bucket specified at the deployment. An IAM role attached to the JupyterHub is controlling the data access to the S3 bucket. If you want to connect to a different bucket that wasn't specified at the deployment, you will get an access deny error. In this case, simply add the bucket ARN to the IAM role 'SparkOnEKS-EksClusterjhubServiceAcctRole'.


5. Now let's take a look at the output table in [Athena](https://console.aws.amazon.com/athena/), to check if the table is populated correctly.

```
SELECT * FROM default.deltalake_contact_jhub WHERE id=12
```

## Submit a native Spark job with Spot instance

As an addition of the solution, to meet customer's preference of running native Spark jobs, we will demonstrate how easy to submit a job with a fat jar file in EKS. In this case, the Jupyter notebook still can be used, as an interactive development environment for PySpark apps. 

In Spark, driver is a single point of failure in data processing. If driver dies, all other linked components will be discarded as well. To achieve the optimal performance and cost, we will run the driver on a reliable managed EC2 instance on EKS, and the rest of executors will be on spot instances.

1. [OPTIONAL] Run a dummy container to validate the spot template file. 
NOTE: update the placeholder with corret information.

```
kubectl run --generator=run-pod/v1 jump-pod --rm -i --tty --serviceaccount=nativejob --namespace=spark --image <your_account_number>.dkr.ecr.<your_region>.amazonaws.com/arc:latest sh

# after login to the container, validate a file
# ensure the service account is `nativejob` and the lifecycle value is `Ec2Spot` in the template
sh-5.0# ls 
sh-5.0# cat executor-pod-template.yaml
sh-5.0# exit

```

2. Modify the job manifest file [native-spark-job-scheduler.yaml](source/example/native-spark-job-scheduler.yaml) stored on your computer, ie. replace the placeholder {{codeBucket}}.

![](/images/4-cfn-output.png)
![](/images/4-spark-output-s3.png)


3. Submit a native Spark job. 

```
kubectl apply -f source/example/native-spark-job-scheduler.yaml
kubectl get pod -n spark

# when rerun, delete before apply again
kubectl delete -f source/example/native-spark-job-scheduler.yaml
kubectl apply -f source/example/native-spark-job-scheduler.yaml

```
4. Go to SparkUI to check your job progress and performance. Make sure the driver pod exists.

```
driver=$(kubectl get pod -n spark -l spark-role=driver -o jsonpath="{.items[*].metadata.name}" --field-selector=status.phase=Running)
echo "driver pod is $driver"
kubectl port-forward $driver 4040:4040 -n spark

# go to `localhost:4040` from your web browser

```
5. Examine the auto-scaling and multi-AZs support

```
# The sample job will run with 10 Spark executors for 15 mins. It requires one Spark executor per EC2 spot instance. Once the job is triggered, you will see the autoscaling kick-in within seconds. It will scale your EKS Cluster from 1 to 10 spot nodes. It is flexible to fit the Spark executors into a smaller number of spot instances if you want. 

# The auto-scaling is fired up across multiple AZs. It is configurable to schedule the job in a single AZ if required.

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
 * `argo submit source/example/nyctaxi-job-scheduler.yaml`  submit a spark job via Argo workflow tool
 * `argo list --all-namespaces`                       show all jobs scheduled via Argo
 * `kubectl delete pod --all -n spark`                delete all Spark jobs
 * `kubectl apply -f source/app_resources/spark-template.yaml` create a reusable Spark job template

## Clean up
Go to the root directory of the GitHub reporsitory, then run the clean up script.

```
cd sql-based-etl-with-apache-spark-on-amazon-eks
./deployment/delete_all.sh

```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE.txt) file.