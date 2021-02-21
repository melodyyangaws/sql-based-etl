# SQL-based ETL with Spark on EKS
This is a project for a solution - SQL based ETL with a declarative framework powered by Apache Spark. 

We introduce a quality-aware design to increase data processing productivity, by leveraging an open-source [Arc data framework](https://arc.tripl.ai/) for a user-centered declarative ETL solution. Additionally, we take considerations of the needs and expected skills from customers in data analytics, and accelerate their interaction with ETL practice in order to foster simplicity, while maximizing efficiency.

## Architecture Overview
![](/images/architecture.png)


## Deploy Infrastructure
1. Open AWS CloudShell in `us-east-1`: [link to AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1)
2. Paste the command to CloudShell, in order to install kubernetes tools
 ```bash
 curl https://raw.githubusercontent.com/melodyyangaws/sql-based-etl/blog/deployment/setup_cmd_tool.sh | bash
 ```
3. Provisionning via CloudFormation template, which takes approx. 30 minutes. 

Deploy with default settings or fill in parameters to customize the solution. If ETL your own data, input the parameter `datalakebucket` by your S3 bucket.

`NOTE: your S3 bucket must be in the same region as the deployment region.`

  |   Region  |   Launch Template |
  |  ---------------------------   |   -----------------------  |
  |  ---------------------------   |   -----------------------  |
  **N.Virginia** (us-east-1) | [![Deploy to AWS](/images/00-deploy-to-aws.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=SparkOnEks&templateURL=https://aws-solution-test-us-east-1.s3.amazonaws.com/global-s3-assets/SparkOnEKS.template)  


## Post Deployment

### Build & test ETL job in Arc Jupyter
1. Login to the Arc Jupyter found at [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false)

* username -  `sparkoneks`, or your own login name specified at the deployment earlier. 
* password - run the command in [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1)
```bash
JHUB_PWD=$(kubectl -n jupyter get secret jupyter-external-secret -o jsonpath="{.data.password}" | base64 --decode)
echo -e "\nJupyter password: $JHUB_PWD"
```
NOTE: Your Jupyter session will end, if it is inactive for 30 minutes. You may lose your work, if it hasn't been saved back to the Git repository. Alternatively, you can download the work to your compute, which can be disabled in Production, in order to further enhance your data security.
<!-- 

We introduce a configuration-driven design to increase the data process productivity, by leveraging an open-source [data framework Arc](https://arc.tripl.ai/) for a SQL-centric ETL solution. Furthermore, we enforce the best practice in Data DevOps. Ensure every single ETL artefact are source & version controlled. Git should be the single source of truth for your ETL development and deployment. 
 -->
2. Locate the sample ETL job `sql-based-etl/source/example/scd2-job.ipynb`. It demonstrates how to process data incrementally using SQL scripts and the `Delta Lake` technique. 

To demonstrate the DevOps best practice, your Jupyter instance clones the latest source artifact from a Git repository each time when you login. In real practice, you must check-in all the changes to your source repository, in order to save and trigger the ETL pipeline.

![](/images/3-git-commit-notebook.png)

3. Execute each block and observe the result.
4. Now let's take a look at the output table in [Athena](https://console.aws.amazon.com/athena/), to check if the table is populated correctly.
```bash
SELECT * FROM default.deltalake_contact_jhub WHERE id=12
```

### Submit & Orchestrate Arc ETL job
1. Connect to the new EKS cluster. Get the connection command from your [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false), something like this:

  ```bash
  aws eks update-kubeconfig --name <eks_name> --region <region> --role-arn <role_arn>

  # check the connection
  kubectl get svc
  ```

2. Login to Argo

Go to the Argo website found in the Cloudformation output, run `argo auth token` in [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1) to get a login token. Paste it to the Argo website.

![](/images/1-argologin.png)


3. Submit an Arc ETL job on Argo.

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

4. Submit an Arc job via Argo CLI. Check logs on your Argo website.

  Replace the bucket placeholder by yours found on the [CloudFormation Output](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringStatus=active&filteringText=&viewNested=true&hideStacks=false). Run the command on [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1)
  ```bash
  argo submit https://raw.githubusercontent.com/melodyyangaws/sql-based-etl/blog/source/example/scd2-job-scheduler.yaml -n spark --watch  -p codeBucket=<your_codeBucket_name>
  ```
  ![](/images/3-argo-job-dependency.png)

5. The job outputs a [Delta Lake](https://delta.io/) table. Run the query in [Athena] console (https://console.aws.amazon.com/athena/), in order to check if it is a SCD2 type. 

```
SELECT * FROM default.contact_snapshot WHERE id=12
```

### Submit a native Spark job

Without any changes, we will reuse the Arc docker image, submit a native Spark application defined in a declarative apporach. It saves lots of efforts on DevOps operation, as the way of deploying Spark application follows the same declarative approach in Kubernetes, which is consistent with other business applications deployment.

The example demonstrates:
* Saving cost with Amazon EC2 Spot instance type
* Dynamically scale a Spark application - [Dynamic Resource Allocation](https://spark.apache.org/docs/3.0.0-preview/job-scheduling.html#dynamic-resource-allocation)
* Self-recovery after losing a Spark driver
* Monitor the job on a Spark WebUI


1. Submit a native Spark job to EKS on [AWS CloudShell](https://console.aws.amazon.com/cloudshell/home?region=us-east-1). The job definition utlizes k8s's CRD [Spark Operator](https://operatorhub.io/operator/spark-gcp).
```bash
kubectl create -f https://raw.githubusercontent.com/melodyyangaws/sql-based-etl/blog/source/example/native-spark-job-scheduler.yaml
kubectl get pod -n spark
```
2. Modify the job manifest file [native-spark-job-scheduler.yaml](source/example/native-spark-job-scheduler.yaml) stored on your computer, ie. replace the placeholder {{codeBucket}}.

![](/images/4-cfn-output.png)
![](/images/4-spark-output-s3.png)


2. Submit the job. 


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