# SQL based data processing with declarative framework
This is a project developed with Python CDK for the solution SO0141 - SQL based ETL with a declarative framework.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the .env
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template to be deployed.

```
$ cdk synth CreateEKSCluster --require-approval never -c env=develop 

```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

Finally deploy the stacks.

```
$ cdk deploy CreateEKSCluster -c env=develop

```

After everything is created successfully, you can find few userful outputs from the CloudFormation/CDK deployment. Now it's time to visit the `Argo Dashboard WebUI`, and `submit Spark jobs`. 

Firstly, let's find the Argo dashboard URL, something looks like this:
```
CreateEKSCluster.ARGOURL = http://<random_string>-<account_id>.<region>.elb.amazonaws.com:2746
```

Alternatively, find the URL via CLI command in 2 steps:

1. Copy the `aws eks update-kubeconfig` command from the output, which configures kubectl so that you can connect to the newly created Amazon EKS cluster. 
```
$ aws eks update-kubeconfig --name <cluster_name> --region <region> --role-arn arn:aws:iam::<account_id>:role/<role_name>
```

2. Get the ARGO dashboard URL via kubectl tool:
```
$ ARGO_URL=$(kubectl -n argo get svc argo-server --template "{{ range (index .status.loadBalancer.ingress 0) }}{{ . }}{{ end }}")
$ echo ARGO DASHBOARD: http://${ARGO_URL}:2746
```

Now, it's time to submit our Spark jobs to ARGO. 

1. Take a look at the sample job developed in the [Jupyter Notebook](https://github.com/tripl-ai/arc-starter/tree/master/examples/kubernetes/nyctaxi.ipynb).  It uses a Spark Wrapper called [ARC framework](https://arc.tripl.ai/) to create a Spark application in a declarative way. The opinionated standard approach enables rapid app deployment, simplifies data pipeline build. Additionally, It makes self-service ETL & analytics possible to the business.

In this exmaple data pipeline, we will extract "New York City Taxi Data" from the [AWS Open Data Registry](https://registry.opendata.aws/), ie. a public s3 bucket `s3://nyc-tlc/trip\ data`, then transform the data type from CSV to parquet, followed by a SQL-based data validation step, to ensure the typing transformation is done properly. Finally, query the optimized data filtered by a flag column.

2. Go to the ARGO dashboard, Click on `SUBMIT NEW WORKFLOW` button on the top left of ARGO Dashoard.

![](/images/1-argoui.png)

3. Copy and paste the `Workflow` to AROG portal, click `SUBMIT`.

```
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: nyctaxi-job-
  namespace: spark
  # name: nyctaxi-job-spark
spec:
  serviceAccountName: arcjob
  entrypoint: nyctaxi-job
  templates:
  - name: nyctaxi-job
    dag:
      tasks:
        - name: step1-query
          templateRef:
            name: arc-spark-clustertemplate
            template: sparkClient
            clusterScope: true   
          arguments:
            parameters:
            - name: jobId
              value: nyctaxi 
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

4. You can examine the job log with great details, by clicking a dot on the ARGO WebUI.
![](/images/3-argo-log.png)

5. A second job example with a real-world problem is also provided in the source code. This time, we can try to use a command line to submit the job:
```
$ argo submit source/app_resources/scd2-job.yaml
```


It solves the incrermtnal data load problem with [Slow Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) in a `Delta Lake` open format. You will find how easy it is to tackle the infamous big data problem in a declarative manner.



## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
 * `cdk destroy`     delete the stack deployed earlier

