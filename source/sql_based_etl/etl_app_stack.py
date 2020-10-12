from aws_cdk import (
    core,
    aws_eks as eks,
    aws_ec2 as ec2,
)
from aws_cdk.aws_iam import (
    PolicyStatement as policy,
    ManagedPolicy,
    ServicePrincipal,
    Role
)
from lib.manifest_reader import loadYamlLocal, loadYamlRemotely

class CreateAppStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, eksname: str, admin_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        _my_cluster = eks.Cluster.from_cluster_attributes(self, 'GetEKSCluster',
            cluster_name= eksname,
            kubectl_role_arn='arn:aws:iam::' + self.account + ':role/'+ admin_name
        )

# # //*************************************************************************************//
# # //************************** Setup ARGO WORKFLOW *************************************//
# # //******* K8s Native WF tool supports containerized batch & streaming jobs ***********//
# # //***********************************************************************************//
        
#         # Installation
#         _install =_my_cluster.add_helm_chart('argo-chart',
#             chart='argo',
#             repository='https://argoproj.github.io/argo-helm',
#             release='argo',
#             namespace='argo',
#             values=loadYamlLocal('../app_resources/argo-values.yaml')
#         )
#         _expose_ui = eks.KubernetesPatch(self,'port-forwarding',
#             cluster= _my_cluster,
#             resource_name='service/argo-server',
#             apply_patch=loadYamlLocal('../app_resources/argo-server-svc.yaml'),
#             # can't revert back to ClusterIP, a known k8s issue https://github.com/kubernetes/kubernetes/issues/33766
#             restore_patch={"spec": {"type": "ClusterIP"}},
#             resource_namespace='argo'
#         )
#         _expose_ui.node.add_dependency(_install)

#         # Submit Spark workflow template
#         _submit_tmpl = _my_cluster.add_manifest('spark-wrktmpl',
#             loadYamlLocal('../app_resources/spark-template.yaml')
#         )

        # Deploy Metrics Server for Horizontal Pod Autoscaler
        # kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.3.6/components.yaml


        # _submit_job=_my_cluster.add_manifest('spark_template',loadYamlLocal('../app_resources/spark-template.yaml'))
        # submit spark ETL job to ARGO: kubectl apply -f app_resources/nyctaxi.yaml -n argo --serviceaccount etl 
        
# //***************** Submit Native Spark job ******************//
# TO DO
    # submit native spark job to k8s: kubectl apply -f app_resources/kinnar.yaml -n spark --sercviceaccount etl
 ##########

# //*********************************************************************//
# //***************************** Setup Jupyter **************************//
# //*********************************************************************//
        _jhub_install=_my_cluster.add_helm_chart('jhub',
            chart='jupyterhub',
            repository='https://jupyterhub.github.io/helm-chart',
            release='jhub',
            namespace='jupyter',
            create_namespace=True,
            values=loadYamlLocal('../app_resources/jupyter-values.yaml')
        )

        _expose_hub = _my_cluster.add_manifest('enalble-jhub-ui',
            loadYamlLocal('../app_resources/jupyter-ingress.yaml')
        )
    
        # _expose_hub = eks.KubernetesPatch(self,'enalble-jhub-ui',
        #     cluster=_my_cluster,
        #     resource_name='service/hub',
        #     apply_patch={"spec": {"type": "LoadBalancer"}},
        #     # can't revert back to ClusterIP, a known k8s issue https://github.com/kubernetes/kubernetes/issues/33766
        #     restore_patch={"spec": {"type": "LoadBalancer"}},
        #     resource_namespace='jupyter'
        # )
        # _expose_hub.node.add_dependency(_jhub_install)
        # _my_cluster.add_service_account('jupyterhub',name='notebook',namespace='jupyter')


        # Add Self-managed Node Group to EKS
        #
        # self.workerNodegroupAsg = asg.AutoScalingGroup(
        #     scope=self, 
        #     id='EksWorkerNodeGroup', 
        #     vpc=cluster_vpc,
        #     instance_type=ec2.InstanceType('r5.large'),
        #     desired_capacity= desired_node_count,
        #     machine_image=eks.EksOptimizedImage(
        #         kubernetes_version=cluster_version,
        #         node_type=eks.NodeType.STANDARD
        #     ),
        #     min_capacity=0,
        #     max_capacity=3,
        #     role=worker_role,
        #     update_type=asg.UpdateType.ROLLING_UPDATE
        # )

        # self.workerNodegroupAsg.connections.allow_from(
        #     other=cluster_sg,
        #     port_range=ec2.Port.tcp_range(start_port=1025, end_port=65535),
        # )

        # self.workerNodegroupAsg.connections.allow_from(
        #     other=cluster_sg,
        #     port_range=ec2.Port.tcp(443)
        # )
        # self.workerNodegroupAsg.connections.allow_internally(port_range=ec2.Port.all_traffic())

        # argo_url = _my_cluster.get_service_load_balancer_address(service_name='argo-server',namespace='argo')
        # core.CfnOutput(self,'_ARGO_URL', value='http://'+ str(argo_url) + ':2746')
