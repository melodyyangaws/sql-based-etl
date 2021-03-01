# SQL-based ETL with Spark on EKS
This is a project for a solution - SQL based ETL with a declarative framework powered by Apache Spark. 

We introduce a quality-aware design to increase data processing productivity, by leveraging an open-source [Arc data framework](https://arc.tripl.ai/) for a user-centered declarative ETL solution. Additionally, we take considerations of the needs and expected skills from customers in data analytics, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

## Overview
![](/images/architecture.png)

#### Table of Contents
* [Deploy Infrastructure](#Deploy-Infrastructure)
* [Post Deployment](#Post-Deployment)
  * [Install kubernetes tool](#Install-kubernetes-tool)
  * [Test ETL job in Jupyter](#Test-an-ETL-job-in-Jupyter)
  * [Submit & Orchestrate Arc ETL job](#submit--orchestrate-arc-etl-job)
    * [Submit a job on Argo UI](#Submit-a-job-on-Argo-UI)
    * [Submit a job via Argo CLI](#Submit-a-job-via-Argo-CLI)
  * [Submit a native Spark job](#Submit-a-native-Spark-job)
    * [Submit a job via kubectl](#Submit-a-job-via-kubectl)
    * [Self-recovery test](#Self-recovery-test)
    * [Cost savings with spot instance](#Check-Spot-instance-usage-and-cost-savings)
    * [Auto Scaling across Multi-AZ, and Spark's DynamicAllocation support](#Explore-EKS-features-Auto-Scaling-across-Multi-AZ-and-Spark's-Dynamic-Allocation-support)
* [Useful commands](#Useful-commands)  
* [Clean Up](#clean-up)
* [Security](#Security)
* [License](#License)


## Deploy Infrastructure
Provisionning via CloudFormation template, which takes approx. 30 minutes. 

  |   Region  |   Launch Template |
  |  ---------------------------   |   -----------------------  |
  |  ---------------------------   |   -----------------------  |
  **N.Virginia-blog** (us-east-1) | [![Deploy to AWS](/images/00-deploy-to-aws.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=SparkOnEKS&templateURL=https://aws-solution-test-us-east-1.s3.amazonaws.com/global-s3-assets/SparkOnEKS.template) | 
  | **Oregon-solution** (us-west-2) | [![Deploy to AWS](/images/00-deploy-to-aws.png)](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=SparkOnEKS&templateURL=https://aws-solution-test-us-west-2.s3.amazonaws.com/global-s3-assets/SparkOnEKS.template) |

Option1: Deploy with default.
Option2: Jupyter login with a customized username.
Option3: If ETL your own data, input the parameter `datalakebucket` with your S3 bucket. `NOTE: the S3 bucket must be in the same region as the deployment region.`

You can customize the solution and generate the CFN in your region: 
```bash
export DIST_OUTPUT_BUCKET=my-bucket-name # bucket where customized code will reside
export SOLUTION_NAME=sql-based-etl
export VERSION=v1.0.0 # version number for the customized code
export AWS_REGION=your-region

./deployment/build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION $DIST_OUTPUT_BUCKET

aws s3 cp ./deployment/global-s3-assets/ s3://$DIST_OUTPUT_BUCKET/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control
aws s3 cp ./deployment/regional-s3-assets/ s3://$DIST_OUTPUT_BUCKET/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control
```

[*^ back to top*](#Table-of-Contents)
## Post Deployment
Run a EKS connection command that can be found on [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1). It looks like this:
```bash
aws eks update-kubeconfig --name <eks_name> --region <region> --role-arn <role_arn>

# check the connection
kubectl get svc
```
### Install kubernetes tool
Install command tools via AWS CloudShell in your deployment region `us-east-1` or `us-west-2`: [link to AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1). Each CloudShell session will timeout after idle for 20 minutes, the below installation command must run again in a new session.
 ```bash
 curl https://raw.githubusercontent.com/melodyyangaws/sql-based-etl/blog/deployment/setup_cmd_tool.sh | bash
 ```
### Test an ETL job in Jupyter
* Login to the Jupyter found at [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false)

  * username -  `sparkoneks`, or your own login name specified at the deployment earlier. 
  * password - run the command in [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1)
  ```bash
  JHUB_PWD=$(kubectl -n jupyter get secret jupyter-external-secret -o jsonpath="{.data.password}" | base64 --decode)
  echo -e "\nJupyter password: $JHUB_PWD"
  ```
  NOTE: The Jupyter session will end if it is inactive for 30 minutes. You may lose your work, if it hasn't been saved back to the Git repository. Alternatively, you can download it to your computer, which can be disabled in order to further enhance your data security.

* Open the scd2 ETL job notebook `sql-based-etl/source/example/scd2-job.ipynb`. 

In thius example, we will create a table to support the [Slowly Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) format. You will have a hands-on experience to do the SQL-based ETL to implement the incremental data load in Data Lake.

To demonstrate the DevOps best practice, your Jupyter instance clones the latest source artifact from the current Git repository each time when you login. In real practice, you must check-in all the changes to your source repository, in order to save and run the ETL pipeline.
* Execute each block and observe the result. Change the data processing logic in SQL if you want.
* The sample notebook outputs a `Delta Lake` table. Run a query in [Athena](https://console.aws.amazon.com/athena/) console to check if it is a SCD2 type. 
    ```bash
    SELECT * FROM default.deltalake_contact_jhub WHERE id=12
    ```
[*^ back to top*](#Table-of-Contents)

### Submit & Orchestrate Arc ETL job
* Run a EKS connection command from [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false) in [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1), something like this:

    ```bash
    aws eks update-kubeconfig --name <eks_name> --region <region> --role-arn <role_arn>

    # check the connection
    kubectl get svc
    ```

* Go to Argo website found in the Cloudformation output, run `argo auth token` in [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1) to get a login token. Paste it to the Argo website.

#### Submit a job on Argo UI

  Click `SUBMIT NEW WORKFLOW` button, replace the content by the followings, then `SUBMIT`. Click a pod (dot) to check application logs.

  ```yaml
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
                value: "--ETL_CONF_DATA_URL=s3a://nyc-tlc/trip*data \
                --ETL_CONF_JOB_URL=https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes"
  ```

#### Submit a job via Argo CLI 
Let's submit the same scd2 job that was tested in Jupyter notebook earlier, then check job logs on Argo UI.

* Replace the bucket placeholder by yours found on the [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false). Run the command on [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1).
```bash
argo submit https://raw.githubusercontent.com/melodyyangaws/sql-based-etl/blog/source/example/scd2-job-scheduler.yaml -n spark --watch  -p codeBucket=<your_codeBucket_name>
```
![](/images/3-argo-job-dependency.png)

* Query the table in [Athena](https://console.aws.amazon.com/athena/) to check if it has the same outcome as the table populated by Jupyter. 

```
SELECT * FROM default.contact_snapshot WHERE id=12
```
[*^ back to top*](#Table-of-Contents)

### Submit a native Spark job

Reuse the Arc docker image to run a native Spark application, defined by k8s's CRD [Spark Operator](https://operatorhub.io/operator/spark-gcp). It saves efforts on DevOps operation, as the way of deploying Spark application follows the same declarative approach in k8s. It is consistent with other business applications deployment.
  The example demonstrates:
  * Save cost with Amazon EC2 Spot instance type
  * Dynamically scale a Spark application - via [Dynamic Resource Allocation](https://spark.apache.org/docs/3.0.0-preview/job-scheduling.html#dynamic-resource-allocation)
  * Self-recover after losing a Spark driver
  * Monitor a job on Spark WebUI

#### Submit a job via kubectl 
* Execute the command on [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1).
```bash
kubectl create configmap special-config --from-literal=codeBucket=<your_codeBucket_nmae>
kubectl apply -f https://raw.githubusercontent.com/melodyyangaws/sql-based-etl/blog/source/example/native-spark-job-scheduler.yaml
```
* Watch progress in k8s.
```bash
kubectl get pod -n spark
```
* Watch job progress and performance on SparkUI.
```bash
kubectl port-forward word-count-driver 4040:4040 -n spark
# go to `localhost:4040` from your web browser
```
[*^ back to top*](#Table-of-Contents)
#### Self-recovery test
In Spark, driver is a single point of failure in data processing. If driver dies, all other linked components will be discarded too. Outside of k8s, it requires extra effort to set up a job rerun, in order to manage the situation, however It is much simpler in EKS. 

* The native Spark job takes approx. 10 minutes to finish. Let's test its fault tolerance by kill the driver first: 
```bash
kubectl delete -n spark pod word-count-driver --force

# has the driver come back immediately?
kubectl get po -n spark
```
* Now kill one of executors: 
```bash
# replace the example pod name by yours
kubectl delete -n spark pod <example:amazon-reviews-word-count-51ac6d777f7cf184-exec-1> --force

# has it come back with a different number suffix? 
kubectl get po -n spark
```
[*^ back to top*](#Table-of-Contents)
#### Check Spot instance usage and cost savings
Check your [Spot Request](https://console.aws.amazon.com/ec2sp/v2/) console -> Saving Summary, to find out how much running cost have you just saved.

#### Explore EKS features: Auto Scaling across Multi-AZ, and Spark's Dynamic Allocation support

This job will end up with 20 Spark executors/pods on 10 spot EC2 instances for about 10 minutes. Based on the resource allocation defined by the job manifest file, it runs two executors per EC2 spot instance. As soon as the job is kicked in, you will see the autoscaling is triggered within seconds. It scales the EKS cluster from 1 spot compute node to 5, then from 5 to 10 triggered by Spark's DynamicAllocation.

The auto-scaling is configured to be balanced within two AZs. Depending on your business requirement, you can fit an ETL job into a single AZ if needed.

```bash
kubectl get node --label-columns=lifecycle,topology.kubernetes.io/zone
kubectl get pod -n spark
```
![](/images/4-auto-scaling.png)

[*^ back to top*](#Table-of-Contents)
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

[*^ back to top*](#Table-of-Contents)
## Clean up
Go to the repo's root directory, and run the clean up script.

```bash
cd sql-based-etl
./deployment/delete_all.sh
```
[*^ back to top*](#Table-of-Contents)
## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE.txt) file.