# SQL based data processing with declarative framework
This is a project developed with the Python CDK for AWS solution SO0141 - SQL based ETL with a declarative framework.

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

At this point you can now synthesize the CloudFormation template for this code with environment ini.

```
$ cdk synth CreateEKSCluster -c env=develop

```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

Finally deploy the stacks.

```
$ cdk deploy CreateEKSCluster -c env=develop

```

After everything is created successfully, you can go to Argo WebUI and submit Spark jobs. 
1. Firstly, configures kubectl so that you can connect to an Amazon EKS cluster
```
$ aws eks update-kubeconfig --name spark-on-eks-dev --region us-west-2 --role-arn arn:aws:iam::720560070661:role/EKSAdmin
```

2. Now we can start to submit Spark ETL jobs. Let's go to the ARGO dashboard:
```
$ ARGO_URL=$(kubectl -n argo get svc argo-server --template "{{ range (index .status.loadBalancer.ingress 0) }}{{ . }}{{ end }}")
$ echo ARGO DASHBOARD: http://${ARGO_URL}:2746
```
3. Take a look at the sample job developed in the [Jupyter Notebook](https://github.com/tripl-ai/arc-starter/tree/master/examples/kubernetes/nyctaxi.ipynb), and we are going to run it with a declarative approach by laverage the Spark-on-EKS technique.

In this exmaple data pipeline, we will extract "New York City Taxi Data" from the [AWS Open Data Registry](https://registry.opendata.aws/), ie. a public s3 bucket `s3://nyc-tlc/trip\ data`, then transform the data type from CSV to parquet, followed by a SQL-based data validation step, to ensure the typing transformation is done properly. Finally, query the optimized data filtered by a flag column.

4. After understand what the data processing does, let's submit the job on Spark. Click on `SUBMIT NEW WORKFLOW` button on the top left of ARGO Dashoard.

5. Copy and paste the `Workflow` to AROG portal, click `SUBMIT`.

```
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: nyctaxi-job-
  namespace: spark
spec:
  serviceAccountName: etl
  entrypoint: nyctaxi-job
  templates:
  - name: nyctaxi-job
    dag:
      tasks:
        - name: step1-query
          templateRef:
            name: arc-spark-clustertemplate
            template: sparkLocal
            clusterScope: true   
          arguments:
            parameters:
            - name: jobId
              value: nyctaxi 
            # to fully control the job executon, each stage of the job associates to an environment, eg.test & prod. For example: you can skip some test stages when env mismatches. 
            - name: environment
              value: test    
            # The sample Jupyter Notebook URL, could be a file in S3 bucket.  
            - name: configUri
              value: https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes/nyctaxi.ipynb
            # Params needed in your data processing
            - name: parameters
              value: "--ETL_CONF_DATA_URL=s3a://nyc-tlc/trip*data --ETL_CONF_JOB_URL=https://raw.githubusercontent.com/tripl-ai/arc-starter/master/examples/kubernetes"

```

6. You can examine the job log with great details, by clicking a dot on the ARGO WebUI.
7. Another sophisticated example is also provided in the source code. Simple go back to the ARGO workflows page-> `SUBMIT NEW WORKFLOW` -> `UPLOAD FILE` -> find the code reposity in your local directory -> [the sample file](/app_resources/scd2-job.yaml) is stored in "source/app_resources/scd2-job.yaml"  

8. It solves the incrermtnal data load problem with [Slow Changing Dimension Type 2](https://www.datawarehouse4u.info/SCD-Slowly-Changing-Dimensions.html) in a `Delta Lake` open format. You will find how easy it is to tackle the infamous big data problem in a declarative manner.



## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

