from aws_cdk import (
    core, 
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy
    # aws_cloud9 as cloud9
)
from aws_cdk.aws_secretsmanager import (
    Secret,
    SecretStringGenerator
)

from bin.network_sg import NetworkSgConst
from bin.iam_roles import IamConst
from bin.manifest_reader import *
import json

class BaseEksInfraStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, eksname: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # CFN input params
        datalake_bucket = core.CfnParameter(self, "datalakebucket", type="String",
            description="An existing S3 bucket to be accessed by Jupyter Notebook and ETL job",
            default=""
        )
        login_name = core.CfnParameter(self, "jhubuser", type="String",
            description="Your username login to jupyter hub",
            default="sparkoneks"
        )
        # Auto-generate a Jupyter login in secrets manager
        _secret = Secret(self, 'jHubPwd', 
            generate_secret_string=SecretStringGenerator(
                exclude_punctuation=True,
                secret_string_template=json.dumps({'username': login_name.value_as_string}),
                generate_string_key="password")
        )
        eks_network = NetworkSgConst(self,'network-sg', eksname)
        iam_role = IamConst(self,'iam_roles', eksname)

# //**********************************************************************//
# //*************** Upload application code to S3 bucket ****************//
# //********************************************************************//
        _artifact_bucket=s3.Bucket(self, "codeBucket", 
            encryption=s3.BucketEncryption.KMS_MANAGED
        )  

        s3deploy.BucketDeployment(self, "DeployCode",
            sources=[s3deploy.Source.asset("deployment/app_code")],
            destination_bucket= _artifact_bucket,
            destination_key_prefix="app_code"
        )
        code_bucket = _artifact_bucket.bucket_name
        
# //**********************************************************************//
# //******************* EKS CLUSTER WITH NO NODE GROUP *******************//
# //*********************************************************************//
        self._my_cluster = eks.Cluster(self,'EksCluster',
                vpc= eks_network.vpc,
                cluster_name=eksname,
                output_cluster_name=True,
                version= eks.KubernetesVersion.V1_18,
                endpoint_access= eks.EndpointAccess.PUBLIC_AND_PRIVATE,
                default_capacity=0
        )

# //***********************************************************************//
# //********************* MANAGED NODE GROUP IN EKS *************************//
# //***************  compute resource to run Spark jobs *******************//
# //*********************************************************************//

        _managed_node = self._my_cluster.add_nodegroup_capacity('managed-nodegroup',
            nodegroup_name = 'etl-job',
            node_role = iam_role.managed_node_role,
            desired_size = 1,
            max_size = 5,
            min_size = 1,
            disk_size = 50,
            instance_type = ec2.InstanceType('r5.xlarge'),
            labels = {'app':'spark', 'lifecycle':'OnDemand'},
            subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE,one_per_az=True)
        )
        core.Tags.of(_managed_node).add('Name','ManagedNode'+eksname)            
# //****************************************************************************************//
# //*********************** Add Spot NodeGroup to EKS *************************************//
# //************* Run Spark driver on reliable on-demand, exectutor on spot **************//
# //************ CDK automatically installs the spot interrupt handler daemon ***********//
# //******************  to handle EC2 Spot Instance Termination Notices.****************//
# //***********************************************************************************//

        _spot_node = self._my_cluster.add_auto_scaling_group_capacity('spot',
            instance_type=ec2.InstanceType('r4.xlarge'),
            min_capacity=1,
            max_capacity=10,
            spot_price='1'
        )
        _spot_node.add_security_group(
            ec2.SecurityGroup.from_security_group_id(self, 'sharedNodeSG', 
                self._my_cluster.cluster_security_group_id
            )
        )
        # add auto scaler to the cluster 
        core.Tags.of(_spot_node).add('Name', 'Spot-'+eksname)
        core.Tags.of(_spot_node).add('k8s.io/cluster-autoscaler/enabled', 'true')
        core.Tags.of(_spot_node).add('k8s.io/cluster-autoscaler/'+eksname, 'owned')

# //************************************v*************************************************************//
# //***************************** SERVICE ACCOUNT, RBAC and IAM ROLES *******************************//
# //****** Associating IAM role to K8s Service Account to provide fine-grain security control ******//
# //***********************************************************************************************//
        # Cluster Auto-scaler
        _scaler_sa = self._my_cluster.add_service_account('AutoScalerSa', 
            name='cluster-autoscaler', 
            namespace='kube-system'
        )  
        _scaler_role = loadYamlLocal('../app_resources/autoscaler-iam-role.yaml')
        for statmt in _scaler_role:
            _scaler_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))

        # ALB Ingress
        _alb_sa = self._my_cluster.add_service_account('ALBServiceAcct', 
            name='alb-aws-load-balancer-controller',
            namespace='kube-system'
        )
        _alb_role = loadYamlLocal('../app_resources/alb-iam-role.yaml')
        for statmt in _alb_role:
            _alb_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))

        # External secret controller
        _secrets_sa = self._my_cluster.add_service_account('ExSecretController',
            name='external-secrets-controller',
            namespace="kube-system"
        )
        _secrets_sa.node.add_dependency(_secret)
        _secrets_role = loadYamlReplaceVarLocal('../app_resources/ex-secret-iam-role.yaml',
                        fields={"{{secretsmanager}}": _secret.secret_arn+"*"}
                    )
        for statmt in _secrets_role:
            _secrets_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))   
    
# //***********************************************************************************//
# //********************* Enable Cluster Autoscaler **********************************//
# //*********************************************************************************//
 
        _var_mapping = {
            "{{region_name}}": self.region, 
            "{{cluster_name}}": eksname, 
        }
        _scaler_chart = self._my_cluster.add_helm_chart('ClusterAutoScaler',
            chart='cluster-autoscaler-chart',
            repository='https://kubernetes.github.io/autoscaler',
            release='nodescaler',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/autoscaler-values.yaml',_var_mapping)
        )
        _scaler_chart.node.add_dependency(_scaler_sa) 

# //*************************************************************************************//
# //************************ CONTAINER INSIGHT (CLOUDWATCH LOG) ************************//
# //**********************************************************************************//
        _cw_log = eks.KubernetesManifest(self,'ContainerInsight',
            cluster=self._my_cluster, 
            manifest=loadYamlReplaceVarRemotely('https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml', 
                    fields=_var_mapping,
                    multi_resource=True
            )
        )

# //*********************************************************************//
# //*********************** ALB INGRESS CONTROLLER **********************//
# //*********************************************************************//
        _alb_chart = self._my_cluster.add_helm_chart('ALBChart',
            chart='aws-load-balancer-controller',
            repository='https://aws.github.io/eks-charts',
            release='alb',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/alb-values.yaml',
                fields={
                    "{{region_name}}": self.region, 
                    "{{cluster_name}}": eksname, 
                    "{{vpc_id}}": eks_network.vpc.vpc_id
                }
            )
        )
        _alb_chart.node.add_dependency(_alb_sa)

# //*********************************************************************//
# //********************* EXTERNAL SECRETS CONTROLLER *******************//
# //*********************************************************************//
        _secret_chart = self._my_cluster.add_helm_chart('SecretContrChart',
            chart='kubernetes-external-secrets',
            repository='https://external-secrets.github.io/kubernetes-external-secrets/',
            release='external-secrets',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/ex-secret-values.yaml',
                fields={
                    '{{region_name}}': self.region
                }
            )
        ) 
        _secret_chart.node.add_dependency(_secrets_sa)    

# //*********************************************************************//
# //******************** ADD EFS PERSISTENT STORAGE *********************//
# //*********** enable S3A staging commiter for faster S3 access ********//
# //*********************************************************************//
        # _csi_driver_chart = self._my_cluster.add_helm_chart('EFSDriver', 
        #     chart='aws-efs-csi-driver',
        #     release='efs',
        #     repository='https://github.com/kubernetes-sigs/aws-efs-csi-driver/releases/download/v0.3.0/helm-chart.tgz',
        #     create_namespace=False,
        #     namespace='kube-system',
        # )

        _k8s_efs = efs.FileSystem(self,'EFSFileSystem',
            vpc=eks_network.vpc,
            encrypted=True,
            file_system_name='efs-quickaccess',
            lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
            performance_mode=efs.PerformanceMode.MAX_IO,
            removal_policy=core.RemovalPolicy.DESTROY,
            # vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True)
        )
        # _efs_mount_target = efs.CfnMountTarget(self,'MountEFS',
        #     file_system_id=_k8s_efs.file_system_id,
        #     security_groups=[eks_efs_sg.security_group_id],
        #     subnet_id=eks_network.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnet_ids[0]
        # )
        # _pv= eks.KubernetesManifest(self,'pvClaim',
        #     cluster=self._my_cluster,
        #     manifest=loadYamlReplaceVarLocal('../app_resources/efs-spec.yaml', 
        #         fields= {
        #             "{{FileSystemId}} ": _k8s_efs.file_system_id
        #         },
        #         multi_resource=True)
        # )      
        # _pv.node.add_dependency(_k8s_efs)

# ****************************** CREATE APPLICATIONS ON EKS *************************************

# //******************************************************************************************//
# //********************* 0. SETUP PERMISSION & SECURITY CONTROL ****************************//
# //******* create k8s namespace, service account, and IAM role for service account ********//
# //***************************************************************************************//

        # create k8s namespace
        _etl_ns = self._my_cluster.add_manifest('SparkNamespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { 
                    "name": "spark",
                    "labels": {"name":"spark"}
                }
            }
        )
        _jupyter_ns = self._my_cluster.add_manifest('jhubNamespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { 
                    "name": "jupyter",
                    "labels": {"name":"spark"}
                }
            }
        )     
        
        # create k8s service account
        _etl_sa = self._my_cluster.add_service_account('ETLSa', 
            name='arcjob', 
            namespace='spark'
        )
        _etl_sa.node.add_dependency(_etl_ns)

        _etl_rb = eks.KubernetesManifest(self,'ETLRoleBinding',
            cluster=self._my_cluster,
            manifest=loadYamlReplaceVarLocal('../app_resources/etl-rbac.yaml', 
            fields= {
                "{{MY_SA}}": _etl_sa.service_account_name
            }, 
            multi_resource=True)
        )
        _etl_rb.node.add_dependency(_etl_sa)

        _jupyter_sa = self._my_cluster.add_service_account('jhubServiceAcct', 
            name=login_name.value_as_string,
            namespace='jupyter'
        )
        _jupyter_sa.node.add_dependency(_jupyter_ns)

        # Associate AWS IAM role to K8s Service Account
        _bucket_setting={
                "{{codeBucket}}": code_bucket,
                "{{datalakeBucket}}": datalake_bucket.value_as_string
        }
        _s3_access = loadYamlReplaceVarLocal('../app_resources/etl-iam-role.yaml',fields=_bucket_setting)
        for statmnt in _s3_access:
            _etl_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))
            _jupyter_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))
        
# //**************************************************************************************//
# //************************** 1. Setup ARGO WORKFLOW ***********************************//
# //******* K8s Native WF tool orchestrate containerized batch & streaming jobs ********//
# //***********************************************************************************//
        _argo_install = self._my_cluster.add_helm_chart('ARGOChart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo',
            create_namespace=True,
            values=loadYamlLocal('../app_resources/argo-values.yaml')
        )
        
        # Create a k8s cluster scope workflow template, required when manually submit Spark jobs
        _submit_tmpl = self._my_cluster.add_manifest('SubmitSparkWrktmpl',
            loadYamlLocal('../app_resources/spark-template.yaml')
        )
        _submit_tmpl.node.add_dependency(_argo_install)

# //*********************************************************************//
# //************************** 2. Setup Jupyter *************************//
# //*********************************************************************//
        # Installation
        _jhub_install= self._my_cluster.add_helm_chart('JHubChart',
            chart='jupyterhub',
            repository='https://jupyterhub.github.io/helm-chart',
            release='jhub',
            version='0.10.4',
            namespace='jupyter',
            create_namespace=False,
            values=loadYamlReplaceVarLocal('../app_resources/jupyter-values.yaml', 
                fields={"{{codeBucket}}": code_bucket})
        )
        _jhub_install.node.add_dependency(_jupyter_ns)

        # configure JupyterHub
        _name_parts= core.Fn.split('-',_secret.secret_name)
        _name_no_suffix=core.Fn.join('-',[core.Fn.select(0, _name_parts), core.Fn.select(1, _name_parts)])

        _config_hub = eks.KubernetesManifest(self,'JHubConfig',
            cluster=self._my_cluster,
            manifest=loadYamlReplaceVarLocal('../app_resources/jupyter-config.yaml', 
                fields= {
                    "{{MY_SA}}": _jupyter_sa.service_account_name,
                    "{{REGION}}": self.region, 
                    "{{SECRET_NAME}}": _name_no_suffix
                }, 
                multi_resource=True)
        )
        _config_hub.node.add_dependency(_secret_chart)
        _config_hub.node.add_dependency(_jhub_install)


# # //*************************************************************************************//
# # //****************** 3.Setup permission for native Spark jobs  ***********************//
# # //***********************************************************************************//
        _spark_sa = self._my_cluster.add_service_account('nativeSparkSa',
            name='nativejob',
            namespace='spark'
        )
        _spark_sa.node.add_dependency(_etl_ns)

        _spark_rb = self._my_cluster.add_manifest('sparkRoleBinding',
            loadYamlReplaceVarLocal('../app_resources/native-spark-rbac.yaml',
                fields= {
                    "{{MY_SA}}": _spark_sa.service_account_name
                })
        )
        _spark_rb.node.add_dependency(_spark_sa)

        _spark_iam = loadYamlReplaceVarLocal('../app_resources/native-spark-iam-role.yaml',fields=_bucket_setting)
        for statmnt in _spark_iam:
            _spark_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

# # # //*********************************************************************//
# # # //*************************** Deployment Output ***********************//
# # # //*********************************************************************//
        argo_url=eks.KubernetesObjectValue(self, 'argoALB',
            cluster=self._my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='argo-server',
            object_namespace='argo',
            timeout=core.Duration.minutes(10)
        )
        argo_url.node.add_dependency(_argo_install)
        core.CfnOutput(self,'ARGO_URL', value='http://'+ argo_url.value + ':2746')
        
        jhub_url=eks.KubernetesObjectValue(self, 'jhubALB',
            cluster=self._my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='jupyterhub',
            object_namespace='jupyter',
            timeout=core.Duration.minutes(10)
        )
        jhub_url.node.add_dependency(_config_hub)
        core.CfnOutput(self,'JUPYTER_URL', value='http://'+ jhub_url.value + ':8000')
        core.CfnOutput(self,'CODE_BUCKET', value=code_bucket)
