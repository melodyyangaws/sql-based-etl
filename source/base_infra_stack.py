from aws_cdk import (
    core, 
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_iam as iam
)

from lib.network_sg import NetworkSgConst
from lib.iam_roles import IamConst
from lib.manifest_reader import *


class BaseEksInfraStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, eksname: str, admin_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        eks_vpc = NetworkSgConst(self,'network-sg', eksname).vpc
        iam_role = IamConst(self,'iam_roles', eksname, admin_name)

# //**********************************************************************//
# //******************* EKS CLUSTER WITH NO NODE GROUP *******************//
# //*********************************************************************//

        _my_cluster = eks.Cluster(self,'EksCluster',
                vpc= eks_vpc,
                # role= _iam_role.control_plane_role
                # security_group= _network_sg.control_plane_sg,
                cluster_name=eksname,
                output_cluster_name=True,
                masters_role= iam_role.admin_role,
                version= eks.KubernetesVersion.V1_17,
                endpoint_access= eks.EndpointAccess.PUBLIC_AND_PRIVATE,
                default_capacity=0
        )

# //***********************************************************************//
# //********************* MANAGED NODE GROUP IN EKS *************************//
# //***************  compute resource to run Spark jobs *******************//
# //*********************************************************************//

        _my_cluster.add_nodegroup_capacity('managed-nodegroup',
            nodegroup_name = 'etl-job',
            node_role = iam_role.managed_node_role,
            desired_size = 1,
            max_size = 5,
            min_size = 1,
            disk_size = 50,
            instance_type = ec2.InstanceType('m5.xlarge'),
            labels = {'app':'spark'},
            subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE,one_per_az=True)
        )

# //************************************v************************************************************//
# //***************************** SERVICE ACCOUNT, RBAC and IAM ROLES ******************************//
# //**** Associating AWS IAM role to K8s Service Account to provide fine-grain security control ****//
# //************************************************************************************************//

       # Setup service account in a new namespace Spark
        _ns = _my_cluster.add_manifest('spark-namespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { "name": "spark" }
            })
        _sa = _my_cluster.add_service_account('etl-sa', name='arcjob', namespace='spark')
        _sa.node.add_dependency(_ns)

        k8s_rolebinding = eks.KubernetesManifest(self,'etl-rolebinding',
            cluster=_my_cluster,
            manifest=loadYamlLocal('../app_resources/eks-rbac.yaml', multi_resource=True)
        )
        k8s_rolebinding.node.add_dependency(_sa)

        # Associate AWS IAM role to K8s Service Account
        _statements = loadYamlLocal('../app_resources/s3-iam-role.yaml')
        for statmnt in _statements:
            _sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

        # Cluster Auto-scaler service account
        _scaler_sa = _my_cluster.add_service_account('autoscalerr-sa', 
            name='cluster-autoscaler', 
            namespace='kube-system'
        )  
        _scaler_role = loadYamlLocal('../app_resources/autoscaler-iam-role.yaml')
        for statmt in _scaler_role:
            _scaler_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))

        # ALB Ingress service account
        _alb_sa = _my_cluster.add_service_account('alb', 
            name='alb-ingress-controller',
            namespace='kube-system'
        )
        _alb_rbac = eks.KubernetesManifest(self,'k8s-rbac',
            cluster=_my_cluster, 
            manifest=loadYamlRemotely('https://raw.githubusercontent.com/kubernetes-sigs/aws-alb-ingress-controller/v1.1.8/docs/examples/rbac-role.yaml',True)
        )
        _alb_role = loadYamlLocal('../app_resources/alb-iam-role.yaml')
        for statmt in _alb_role:
            _alb_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmt))

# //*************************************************************************************//
# //********************* Enable Cluster Autoscaler ************************************//
# //********************* add nodes to node group when it is needed *******************//
# //**********************************************************************************//
 
        dataDict = {
            "{{region_name}}": self.region, 
            "{{cluster_name}}": _my_cluster.cluster_name, 
        }
        _my_cluster.add_helm_chart('cluster-autoscaler',
            chart='cluster-autoscaler-chart',
            repository='https://kubernetes.github.io/autoscaler',
            release='nodescaler',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/autoscaler-values.yaml',dataDict)
        )

# //*************************************************************************************//
# //************************ CONTAINER INSIGHT (CLOUDWATCH LOG) ************************//
# //**********************************************************************************//

        _cw_log = eks.KubernetesManifest(self,'container-insight',
            cluster=_my_cluster, 
            manifest=loadYamlReplaceVarRemotely('https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml', 
                    fields=dataDict,
                    multi_resource=True
            )
        )

# //*********************************************************************//
# //*********************** ALB INGRESS CONTROLLER **********************//
# //*********************************************************************//

        # Deploy the ALB Ingress Controller from Helm chart
        dataMap = {
            "{{region_name}}": self.region, 
            "{{cluster_name}}": _my_cluster.cluster_name, 
            "{{vpc_id}}": eks_vpc.vpc_id
        }
        _my_cluster.add_helm_chart('aws-alb-ingress-controller',
            chart='aws-alb-ingress-controller',
            repository='http://storage.googleapis.com/kubernetes-charts-incubator',
            release='alb',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/alb-values.yaml',dataMap)
        )

# # Add EFS for S3A staging commiter for faster S3 access
#         _csi_driver = _my_cluster.add_manifest('efs-driver', 
#             loadYamlRemotely('https://raw.githubusercontent.com/kubernetes-sigs/aws-efs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.0')
#         )
#         _k8s_efs = efs.FileSystem(self,'create-efs',
#             vpc=eks_vpc,encrypted=True,
#             lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
#             performance_mode=efs.PerformanceMode.MAX_IO,
#             throughput_mode=efs.ThroughputMode.BURSTING,
#         )
        #   _my_cluster.add_manifest('efs-storage',
        #     manifest=loadYamlLocal('../app_resources/efs-storageclass.yaml')
#        )
#         _pv= _my_cluster.add_manifest('pv-workdir-s3a',
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

# # //*************************************************************************************//
# # //************************** Setup ARGO WORKFLOW *************************************//
# # //******* K8s Native WF tool supports containerized batch & streaming jobs ***********//
# # //***********************************************************************************//
        
        # Installation
        _install =_my_cluster.add_helm_chart('argo-chart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo',
            create_namespace=True,
            values=loadYamlLocal('../app_resources/argo-values.yaml')
        )
        _expose_ui = eks.KubernetesPatch(self,'port-forwarding',
            cluster= _my_cluster,
            resource_name='service/argo-server',
            apply_patch=loadYamlLocal('../app_resources/argo-server-svc.yaml'),
            # can't revert back to ClusterIP, a known k8s issue https://github.com/kubernetes/kubernetes/issues/33766
            restore_patch={},
            resource_namespace='argo'
        )
        _expose_ui.node.add_dependency(_install)

        # Submit Spark workflow template
        _submit_tmpl = _my_cluster.add_manifest('spark-wrktmpl',
            loadYamlLocal('../app_resources/spark-template.yaml')
        )
        _submit_tmpl.node.add_dependency(_install)


# //*************************************************************************************//
# //********************* Add Farget Node to EKS ***************************************//
# // *************** Jupyter acts as an IDE for develop/test ETL job ********************//
# //******* Easy to maintain when it comes to the multi-tenancy, personaliation *******//
# //**********************************************************************************//

        _my_cluster.add_fargate_profile('jhub',
            selectors=[{"namespace": "jupyter"}, {"app":"jupyter"}],
            fargate_profile_name='jupyterhub',
            pod_execution_role=iam_role.fargate_role,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True),
        )

# //*********************************************************************//
# //***************************** Setup Jupyter **************************//
# //*********************************************************************//
        _jhub_install=_my_cluster.add_helm_chart('jhub',
            chart='jupyterhub',
            repository='https://jupyterhub.github.io/helm-chart',
            release='jhub',
            version='0.9.0',
            namespace='jupyter',
            create_namespace=True,
            values=loadYamlLocal('../app_resources/jupyter-values.yaml'),
            wait=False
        )

        # _expose_ui = eks.KubernetesPatch(self,'expose-jhub-ui',
        #     cluster= _my_cluster,
        #     resource_name='service/hub',
        #     apply_patch=loadYamlLocal('../app_resources/jupyter-ingress.yaml'),
        #     # can't revert back to ClusterIP, a known k8s issue https://github.com/kubernetes/kubernetes/issues/33766
        #     restore_patch={},
        #     resource_namespace='jupyter'
        # )

        # _expose_ui.node.add_dependency(_jhub_install)



# # # //*********************************************************************//
# # # //****************** Cloud9 for Private EKS cluster ********************//
# # # //*********************************************************************//
# # # 
# #         # # create a cloud9 ec2 environment in a new VPC
# #         # c9env = cloud9.Ec2Environment(self, 'Cloud9Env',
# #         #     vpc=self._network_sg_construct.vpc,
# #         #     instance_type=ec2.InstanceType('t3.small'),
# #         #     subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
# #         # )

# #         # # print the Cloud9 IDE URL in the output
# #         # core.CfnOutput(self, 'URL', value=c9env.ide_url)

        argo_url = _my_cluster.get_service_load_balancer_address(service_name='argo-server',namespace='argo')
        core.CfnOutput(self,'_ARGO_URL', value='http://'+ str(argo_url) + ':2746')

        # jupyter_url = _my_cluster.get_service_load_balancer_address(service_name='hub',namespace='jupyter')
        # core.CfnOutput(self,'_JUPYTER_URL', value='http://'+ str(jupyter_url) + ':80')