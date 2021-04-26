######################################################################################################################
# Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                      #
#                                                                                                                   #
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
# with the License. A copy of the License is located at                                                             #
#                                                                                                                   #
#     http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                   #
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
# OR CONDITIONS OF ANY KIND, express o#implied. See the License for the specific language governing permissions     #
# and limitations under the License.  																				#                                                                              #
######################################################################################################################

from aws_cdk import (
    core, 
    aws_eks as eks,
    aws_secretsmanager as secmger,
    aws_kms as kms,
    aws_ecr_assets as ecr_asset,
    aws_ecr as ecr
)
from lib.cdk_infra.network_sg import NetworkSgConst
from lib.cdk_infra.iam_roles import IamConst
from lib.cdk_infra.eks_cluster import EksConst
from lib.cdk_infra.eks_service_account import EksSAConst
from lib.cdk_infra.eks_base_app import EksBaseAppConst
from lib.cdk_infra.s3_app_code import S3AppCodeConst
from lib.cdk_infra.spark_permission import SparkOnEksSAConst
from lib.ecr_build.ecr_build_pipeline import DockerPipelineConstruct
from lib.cloud_front_stack import NestedStack
from lib.util.manifest_reader import *
from lib.util import override_rule as scan
import json, os

class SparkOnEksStack(core.Stack):

    @property
    def code_bucket(self):
        return self.app_s3.code_bucket

    @property
    def argo_url(self):
        return self._argo_alb.value

    @property
    def jhub_url(self):
        return self._jhub_alb.value

    def __init__(self, scope: core.Construct, id: str, eksname: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.template_options.description = "(SO0141) SQL based ETL with Apache Spark on Amazon EKS. This solution provides a SQL based ETL option with a open-source declarative framework powered by Apache Spark."
        source_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]+'/source'

        # Cloudformation input params
        datalake_bucket = core.CfnParameter(self, "datalakebucket", type="String",
            description="Your existing S3 bucket to be accessed by Jupyter Notebook and ETL job. Default: blank",
            default=""
        )
        login_name = core.CfnParameter(self, "jhubuser", type="String",
            description="Your username login to jupyter hub",
            default="sparkoneks"
        )
        # Auto-generate a user login in secrets manager
        key = kms.Key(self, 'secretsKMSKey',removal_policy=core.RemovalPolicy.DESTROY,enable_key_rotation=True)
        jhub_secret = secmger.Secret(self, 'jHubPwd', 
            generate_secret_string=secmger.SecretStringGenerator(
                exclude_punctuation=True,
                secret_string_template=json.dumps({'username': login_name.value_as_string}),
                generate_string_key="password"),
            removal_policy=core.RemovalPolicy.DESTROY,
            encryption_key=key
        )

        #1. A new bucket to store app code and access logs
        self.app_s3 = S3AppCodeConst(self,'appcode')

        #2. build and push docker image to ECR 
        ecr_image = DockerPipelineConstruct(self,'image', self.app_s3.artifact_ibucket)
        # ecr_image.node.add_dependency(self.app_s3)
        core.CfnOutput(self,'IMAGE_URI', value=ecr_image.image_uri)

        # 3. Setup EKS base infrastructure
        network_sg = NetworkSgConst(self,'network-sg', eksname, self.app_s3.code_bucket)
        iam = IamConst(self,'iam_roles', eksname)
        eks_cluster = EksConst(self,'eks_cluster', eksname, network_sg.vpc, iam.managed_node_role, iam.admin_role)
        EksSAConst(self, 'eks_sa', eks_cluster.my_cluster, jhub_secret)
        EksBaseAppConst(self, 'eks_base_app', eks_cluster.my_cluster, core.Aws.REGION)

        # 4. Setup Spark application access control
        app_security = SparkOnEksSAConst(self,'spark_service_account', 
            eks_cluster.my_cluster, 
            login_name.value_as_string,
            self.app_s3.code_bucket,
            datalake_bucket.value_as_string
        )
        
        # 5. Install ETL orchestrator - Argo in EKS
        # can be replaced by other workflow tool, ie. Airflow
        argo_install = eks_cluster.my_cluster.add_helm_chart('ARGOChart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo',
            create_namespace=True,
            values=load_yaml_local(source_dir+'/app_resources/argo-values.yaml')
        )
        # Create argo workflow template for Spark apps with different T-shirt size
        submit_tmpl = eks_cluster.my_cluster.add_manifest('SubmitSparkWrktmpl',
            load_yaml_local(source_dir+'/app_resources/spark-template.yaml')
        )
        submit_tmpl.node.add_dependency(argo_install)

        # 6. Install Arc Jupyter notebook in EKS
        jhub_install= eks_cluster.my_cluster.add_helm_chart('JHubChart',
            chart='jupyterhub',
            repository='https://jupyterhub.github.io/helm-chart',
            release='jhub',
            version='0.11.1',
            namespace='jupyter',
            create_namespace=False,
            values=load_yaml_replace_var_local(source_dir+'/app_resources/jupyter-values.yaml', 
                fields={
                    "{{codeBucket}}": self.app_s3.code_bucket,
                    "{{region}}": self.region 
                })
        )
        # get Arc Jupyter login from secrets manager
        name_parts= core.Fn.split('-',jhub_secret.secret_name)
        name_no_suffix=core.Fn.join('-',[core.Fn.select(0, name_parts), core.Fn.select(1, name_parts)])

        config_hub = eks.KubernetesManifest(self,'JHubConfig',
            cluster=eks_cluster.my_cluster,
            manifest=load_yaml_replace_var_local(source_dir+'/app_resources/jupyter-config.yaml', 
                fields= {
                    "{{MY_SA}}": app_security.jupyter_sa,
                    "{{REGION}}": self.region, 
                    "{{SECRET_NAME}}": name_no_suffix
                }, 
                multi_resource=True)
        )
        config_hub.node.add_dependency(jhub_install)
   
        # 7. (OPTIONAL) retrieve ALB DNS Name to enable Cloudfront in the following nested stack.
        # Recommend to remove this section and the rest of CloudFront component. 
        # Setup your own certificate then add to ALB, to enable the HTTPS.
        self._argo_alb = eks.KubernetesObjectValue(self, 'argoALB',
            cluster=eks_cluster.my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='argo-server',
            object_namespace='argo'
        )
        self._argo_alb.node.add_dependency(argo_install)

        self._jhub_alb=eks.KubernetesObjectValue(self, 'jhubALB',
            cluster=eks_cluster.my_cluster,
            json_path='.status.loadBalancer.ingress[0].hostname',
            object_type='ingress',
            object_name='jupyterhub',
            object_namespace='jupyter'
        )
        self._jhub_alb.node.add_dependency(config_hub)

        # 8. Override cfn Nag scan rules for AWS Solution CICD deployment, not related to customer's environment.
        k8s_ctl_node=self.node.find_child('@aws-cdk--aws-eks.KubectlProvider')
        cluster_resrc_node=self.node.find_child('@aws-cdk--aws-eks.ClusterResourceProvider')
        scan.suppress_cfnnag_rule('W12', 'by default the role has * resource', self.node.find_child('eks_cluster').node.find_child('EKS').node.find_child('Resource').node.find_child('CreationRole').node.find_child('DefaultPolicy').node.default_child)
        scan.suppress_cfnnag_rule('W11', 'by default the role has * resource', self.node.find_child('Custom::AWSCDKOpenIdConnectProviderCustomResourceProvider').node.find_child('Role'))
        self.node.find_child('eks_cluster').node.find_child('EKS').node.find_child('ControlPlaneSecurityGroup').node.default_child.add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W40",
                    "reason": "Egress IP Protocol of -1 is default and generally considered OK"
                },
                {
                    "id": "W5",
                    "reason": "Security Groups with cidr open considered OK"
                }
            ]
        })
        k8s_ctl_node.node.find_child('Handler').node.default_child.add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of KubectlProvider hander has permission to write logs to CloudWatch"
                },
                {
                    "id": "W92",
                    "reason": "the function is created by CDK internally, set the ReservedConcurrentExecutions setting is out of reach"
                }
            ]
        })
        k8s_ctl_node.node.find_child('Provider').node.find_child('framework-onEvent').node.default_child.add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of KubectlProvider onEvent has permission to write logs to CloudWatch"
                },
                {
                    "id": "W92",
                    "reason": "the function is created by CDK internally, set the ReservedConcurrentExecutions setting is out of reach"
                }
            ]
        })
        self.node.find_child('Custom::S3AutoDeleteObjectsCustomResourceProvider').node.find_child('Handler').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of S3AutoDelete has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "S3AutoDelete function does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "S3AutoDelete function is created by CDK internally, set the ReservedConcurrentExecutions setting is out of reach"
                }
            ]
        })
        self.node.find_child('Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C').node.find_child('Resource').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of BucketDeployment has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "BucketDeployment function does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "BucketDeployment function is created by CDK internally, set the ReservedConcurrentExecutions setting is out of reach"
                }
            ]
       })
        self.node.find_child('Custom::AWSCDKOpenIdConnectProviderCustomResourceProvider').node.find_child('Handler').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of OpenIdConnectProvider has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "OpenIdConnectProvider function does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "OpenIdConnectProvider function is created by CDK internally, set the ReservedConcurrentExecutions setting is out of reach"
                }
            ]
        })
        self.node.find_child('AWSCDKCfnUtilsProviderCustomResourceProvider').node.find_child('Handler').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of CDKCfnUtilsProvider has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "CDKCfnUtilsProvider function does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "CDKCfnUtilsProvider function is created by CDK internally, set the ReservedConcurrentExecutions setting is out of reach"
                }
            ]
        })
        cluster_resrc_node.node.find_child('OnEventHandler').node.find_child('Resource').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of OnEventHandler has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "the internal function OnEventHandler does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "To set the ReservedConcurrentExecutions is out of reach with the internal function created by CDK"
                }
            ]
        })
        cluster_resrc_node.node.find_child('IsCompleteHandler').node.find_child('Resource').add_metadata('cfn_nag',{         
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of IsCompleteHandler has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "the internal function IsCompleteHandler does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "Setting up ReservedConcurrentExecutions is out of reach with the internal function created by CDK"
                }
            ]
        })
        cluster_resrc_node.node.find_child('Provider').node.find_child('framework-isComplete').node.find_child('Resource').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of framework-isComplete has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "the internal function framework-isComplete does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "Setting up ReservedConcurrentExecutions is out of reach with the internal function created by CDK"
                }
            ]
        })
        cluster_resrc_node.node.find_child('Provider').node.find_child('framework-onTimeout').node.find_child('Resource').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of framework-onTimeout has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "the internal function framework-onTimeout does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "Setting up ReservedConcurrentExecutions is out of reach with the internal function created by CDK"
                }
            ]
        })
        cluster_resrc_node.node.find_child('Provider').node.find_child('framework-onEvent').node.find_child('Resource').add_metadata('cfn_nag',{
            "rules_to_suppress": [
                {
                    "id": "W58",
                    "reason": "the service role of framework-onEvent has permission to write logs to CloudWatch"
                },
                {
                    "id": "W89",
                    "reason": "the interal function framework-onEvent does not have VPC associate to"
                },
                {
                    "id": "W92",
                    "reason": "Setting up ReservedConcurrentExecutions is out of reach with the internal function created by CDK"
                }
            ]
        })