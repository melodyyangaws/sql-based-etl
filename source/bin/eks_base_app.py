from aws_cdk import core
from aws_cdk.aws_eks import ICluster, KubernetesManifest
from bin.manifest_reader import *

class EksBaseAppConst(core.Construct):
    def __init__(self,scope: core.Construct, id: str, eks_cluster: ICluster, region: str, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

# //***********************************************************************************//
# //********************* Install Cluster Autoscaler **********************************//
# //*********************************************************************************//
 
        _var_mapping = {
            "{{region_name}}": region, 
            "{{cluster_name}}": eks_cluster.cluster_name, 
        }
        _scaler_chart = eks_cluster.add_helm_chart('ClusterAutoScaler',
            chart='cluster-autoscaler-chart',
            repository='https://kubernetes.github.io/autoscaler',
            release='nodescaler',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/autoscaler-values.yaml',_var_mapping)
        )
        # _scaler_chart.node.add_dependency(eks_sa.scaler_sa) 

# //*************************************************************************************//
# //************************ CONTAINER INSIGHT (CLOUDWATCH LOG) ************************//
# //**********************************************************************************//
        _cw_log = KubernetesManifest(self,'ContainerInsight',
            cluster=eks_cluster, 
            manifest=loadYamlReplaceVarRemotely('https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml', 
                    fields=_var_mapping,
                    multi_resource=True
            )
        )

# //*********************************************************************//
# //*********************** ALB INGRESS CONTROLLER **********************//
# //*********************************************************************//
        _alb_chart = eks_cluster.add_helm_chart('ALBChart',
            chart='aws-load-balancer-controller',
            repository='https://aws.github.io/eks-charts',
            release='alb',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/alb-values.yaml',
                fields={
                    "{{region_name}}": region, 
                    "{{cluster_name}}": eks_cluster.cluster_name, 
                    "{{vpc_id}}": eks_cluster.vpc.vpc_id
                }
            )
        )
        # _alb_chart.node.add_dependency(eks_sa.alb_sa)

# //*********************************************************************//
# //********************* EXTERNAL SECRETS CONTROLLER *******************//
# //*********************************************************************//
        _secret_chart = eks_cluster.add_helm_chart('SecretContrChart',
            chart='kubernetes-external-secrets',
            repository='https://external-secrets.github.io/kubernetes-external-secrets/',
            release='external-secrets',
            create_namespace=False,
            namespace='kube-system',
            values=loadYamlReplaceVarLocal('../app_resources/ex-secret-values.yaml',
                fields={
                    '{{region_name}}': region
                }
            )
        ) 
        # _secret_chart.node.add_dependency(eks_sa.secrets_sa)    