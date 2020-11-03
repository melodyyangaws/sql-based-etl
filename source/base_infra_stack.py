from aws_cdk import (
    core, 
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy
)

from lib.network_sg import NetworkSgConst
from lib.iam_roles import IamConst
from lib.manifest_reader import *


class BaseEksInfraStack(core.Stack):

    # @property
    # def appcode_bucket(self):
    #     return self._artifact_bucket.bucket_name 

    # @property    
    # def eks_cluster(self):
    #     return self._my_cluster

    def __init__(self, scope: core.Construct, id: str, eksname: str, admin_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        eks_vpc = NetworkSgConst(self,'network-sg', eksname).vpc
        iam_role = IamConst(self,'iam_roles', eksname, admin_name)

# //**********************************************************************//
# //******************* Upload app code to S3 bucket *********************//
# //*********************************************************************//
        self._artifact_bucket = s3.Bucket(self, "codeBucket",encryption=s3.BucketEncryption.KMS_MANAGED)

        s3deploy.BucketDeployment(self, "DeployCode",
            sources=[s3deploy.Source.asset("deployment/app_code")],
            destination_bucket=self._artifact_bucket,
        )

        bucket_name = self._artifact_bucket.bucket_name

# //**********************************************************************//
# //******************* EKS CLUSTER WITH NO NODE GROUP *******************//
# //*********************************************************************//

        self._my_cluster = eks.Cluster(self,'EksCluster',
                vpc= eks_vpc,
                # role= _iam_role.control_plane_role
                # security_group= NetworkSgConst.control_plane_sg,
                cluster_name=eksname,
                output_cluster_name=True,
                masters_role= iam_role.admin_role,
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
        core.Tags.of(_managed_node).add('Name', 'Managed-'+eksname)
# //****************************************************************************************//
# //*********************** Add Spot NodeGroup to EKS *************************************//
# //************* Run Spark driver on reliable on-demand, exectutor on spot **************//
# //************ CDK automatically installs the spot interrupt handler daemon ***********//
# //******************  to handle EC2 Spot Instance Termination Notices.****************//
# //***********************************************************************************//

        _spot_node = self._my_cluster.add_auto_scaling_group_capacity('spot',
            instance_type=ec2.InstanceType('r4.xlarge'),
            bootstrap_options={
                "kubelet_extra_args": "--node-labels app=spark",
            },
            min_capacity=1,
            max_capacity=10,
            spot_price='1'
        )
        # add to cluster auto scaler
        core.Tags.of(_spot_node).add('Name', 'Spot-'+eksname)
        core.Tags.of(_spot_node).add('k8s.io/cluster-autoscaler/enabled', 'true')
        core.Tags.of(_spot_node).add('k8s.io/cluster-autoscaler/'+eksname, 'owned')
# //**************************************************************************************//
# //********************* Add Farget Node to EKS ****************************************//
# // *************** Jupyter acts as an IDE for develop/test ETL job *******************//
# //******* Easy to maintain when it comes to the multi-tenancy, personaliation *******//
# //**********************************************************************************//

        # _fargate_node=self._my_cluster.add_fargate_profile('FargateProfile',
        #     selectors=[{"namespace":"jupyter"}],
        #     fargate_profile_name='jupyterhub',
        #     pod_execution_role=iam_role.fargate_role,
        #     subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True)
        # )
        # core.Tags.of(_fargate_node).add('k8s.io/cluster-autoscaler/enabled', 'true')
        # core.Tags.of(_fargate_node).add('k8s.io/cluster-autoscaler/'+eksname, 'owned')
# //************************************v*************************************************************//
# //***************************** SERVICE ACCOUNT, RBAC and IAM ROLES *******************************//
# //**** Associating AWS IAM role to K8s Service Account to provide fine-grain security control ****//
# //***********************************************************************************************//

       # Setup service account in a new namespace Spark
        _etl_ns = self._my_cluster.add_manifest('SparkNamespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { 
                    "name": "spark",
                    "labels": {"name":"spark"}
                }
            }
        )    
        _etl_sa = self._my_cluster.add_service_account('ETLSa', name='arcjob', namespace='spark')
        _etl_sa.node.add_dependency(_etl_ns)

        _setting = {"{{MY_SA}}": _etl_sa.service_account_name}
        _etl_k8s_rb = eks.KubernetesManifest(self,'ETLRoleBinding',
            cluster=self._my_cluster,
            manifest=loadYamlReplaceVarLocal('../app_resources/etl-rbac.yaml', fields= _setting, multi_resource=True)
        )
        _etl_k8s_rb.node.add_dependency(_etl_sa)

        # Associate AWS IAM role to K8s Service Account
        _etl_bucket={"{{codeBucket}}": bucket_name}
        _etl_s3_statements = loadYamlReplaceVarLocal('../app_resources/etl-iam-role.yaml', fields=_etl_bucket)
        for statmnt in _etl_s3_statements:
            _etl_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

        # Cluster Auto-scaler service account
        _scaler_sa = self._my_cluster.add_service_account('AutoScalerSa', 
            name='cluster-autoscaler', 
            namespace='kube-system'
        )  
        _scaler_role = loadYamlLocal('../app_resources/autoscaler-iam-role.yaml')
        for statmt in _scaler_role:
            _scaler_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))

        # ALB Ingress service account
        _alb_sa = self._my_cluster.add_service_account('ALBServiceAcct', 
            name='alb-ingress-controller',
            namespace='kube-system'
        )
        _alb_role = loadYamlLocal('../app_resources/alb-iam-role.yaml')
        for statmt in _alb_role:
            _alb_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))

# //*************************************************************************************//
# //********************* Enable Cluster Autoscaler ************************************//
# //********************* add nodes to node group when it is needed *******************//
# //**********************************************************************************//
 
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

        # Deploy the ALB Ingress Controller from Helm chart
        dataMap = {
            "{{region_name}}": self.region, 
            "{{cluster_name}}": eksname, 
            "{{vpc_id}}": eks_vpc.vpc_id
        }
        _alb_chart = self._my_cluster.add_helm_chart('ALBChart',
            chart='aws-alb-ingress-controller',
            repository='http://storage.googleapis.com/kubernetes-charts-incubator',
            release='alb',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/alb-values.yaml',dataMap)
        )
        _alb_chart.node.add_dependency(_alb_sa)

# # # Add EFS for S3A staging commiter for faster S3 access
#         _csi_driver = self._my_cluster.add_manifest('efs-driver', 
#             loadYamlRemotely('https://raw.githubusercontent.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.0')
#         )
#         _k8s_efs = efs.FileSystem(self,'create-efs',
#             vpc=eks_vpc,encrypted=True,
#             lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
#             performance_mode=efs.PerformanceMode.MAX_IO,
#             throughput_mode=efs.ThroughputMode.BURSTING,
#         )
#         _efs_mount_target = efs.CfnMountTarget(self,'mountEFS',
#             file_system_id=_k8s_efs.file_system_id,
#             security_groups=NetworkSgConst.efs_sg,
#             subnet_id=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC, one_per_az=True)

#         )
#         self._my_cluster.add_manifest('efs-storage',
#             manifest=loadYamlLocal('../app_resources/efs-storageclass.yaml')
#        )
#         _pv= self._my_cluster.add_manifest('pv-workdir-s3a',
#         manifest={
#             "apiVersion": "v1"
#             "kind": "PersistentVolume"
#             "metadata":{"name": "workdir-pv"}
#             "spec":{"capacity":{"storage": "5Gi"}}
#             "volumeMode":"Filesystem"
#             "accessModes":[{
#                 "ReadWriteMany"
#             }]
#             "persistentVolumeReclaimPolicy": "Retain"
#             "storageClassName":  "efs-sc"
#             "csi":{
#                 "driver": "efs.csi.aws.com",         
#                 "volumeHandle": _k8s_efs.file_system_id
#             }
#         }
#        _pv.node.add_dependency(_k8s_efs)

# //*************************************************************************************//
# //************************** Setup ARGO WORKFLOW *************************************//
# //******* K8s Native WF tool orchestrate containerized batch & streaming jobs ********//
# //***********************************************************************************//
        
        # Installation
        _argo_install = self._my_cluster.add_helm_chart('ARGOChart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo',
            create_namespace=True,
            values=loadYamlLocal('../app_resources/argo-values.yaml')
        )

        # Create a Spark workflow template, manually submit jobs based on the template later.
        _submit_tmpl = self._my_cluster.add_manifest('SubmitSparkWrktmpl',
            loadYamlLocal('../app_resources/spark-template.yaml')
        )
        _submit_tmpl.node.add_dependency(_argo_install)

# //*********************************************************************//
# //***************************** Setup Jupyter **************************//
# //*********************************************************************//

        _jhub_install= self._my_cluster.add_helm_chart('JHubChart',
            chart='jupyterhub',
            repository='https://jupyterhub.github.io/helm-chart',
            release='jhub',
            version='0.10.2',
            namespace='jupyter',
            create_namespace=True,
            values=loadYamlReplaceVarLocal('../app_resources/jupyter-config.yaml', fields=_etl_bucket)
        )
        _expose_hub = self._my_cluster.add_manifest('JHubIngress',
            loadYamlLocal('../app_resources/jupyter-ingress.yaml')
        )
        _expose_hub.node.add_dependency(_jhub_install)

        # Create a login user name determined by a CFN input param
        login_name = core.CfnParameter(self, "jhubuser", type="String",
            description="The username login to jupyter hub"
        )
        _hub_sa = self._my_cluster.add_service_account('jhubServiceAcct', 
            name=login_name.value_as_string,
            namespace='jupyter'
        )
        _hub_sa.node.add_dependency(_jhub_install)

        _setting = {"{{MY_SA}}": _hub_sa.service_account_name}
        _jhub_user_rb = self._my_cluster.add_manifest('hubRoleBinding',loadYamlReplaceVarLocal('../app_resources/jupyter-rbac.yaml',fields= _setting))
        _jhub_user_rb.node.add_dependency(_hub_sa)

        for statmnt in _etl_s3_statements:
            _hub_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

# # //*************************************************************************************//
# # //************ Create service account for native Spark jobs  **************************//
# # //***********************************************************************************//
        _spark_sa = self._my_cluster.add_service_account('nativeSparkSa',
            name='nativejob',
            namespace='spark'
        )
        _spark_sa.node.add_dependency(_etl_ns)

        _setting = {"{{MY_SA}}": _spark_sa.service_account_name}
        _spark_rb = self._my_cluster.add_manifest('sparkRoleBinding',
            loadYamlReplaceVarLocal('../app_resources/native-spark-rbac.yaml',fields= _setting)
        )
        _spark_rb.node.add_dependency(_spark_sa)

        _setting={"{{codeBucket}}": bucket_name}
        _spark_iam = loadYamlReplaceVarLocal('../app_resources/native-spark-iam-role.yaml',fields=_setting)
        for statmnt in _spark_iam:
            _spark_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

# # # # //*********************************************************************//
# # # # //**************** Cloud9 for eksctl in private subnet ****************//
# # # # //*********************************************************************//
# # # # 
# # #         # # create a cloud9 ec2 environment in a new VPC
# # #         # c9env = cloud9.Ec2Environment(self, 'Cloud9Env',
# # #         #     vpc=NetworkSgConst.vpc,
# # #         #     instance_type=ec2.InstanceType('t3.small'),
# # #         #     subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
# # #         # )

# # #         # # print the Cloud9 IDE URL in the output
# # #         # core.CfnOutput(self, 'URL', value=c9env.ide_url)


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
        core.CfnOutput(self,'_ARGO_URL', value='http://'+ argo_url.value + ':2746')
        
        jhub_url=eks.KubernetesObjectValue(self, 'jhubALB',
            cluster=self._my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='jupyterhub',
            object_namespace='jupyter',
            timeout=core.Duration.minutes(10)
        )
        jhub_url.node.add_dependency(_expose_hub)
        core.CfnOutput(self,'_JUPYTER_URL', value='http://'+ jhub_url.value + ':8000')