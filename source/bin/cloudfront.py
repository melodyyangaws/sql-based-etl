from aws_cdk import (
    core,
    aws_cloudfront_origins as origins,
    aws_cloudfront as cf,
    aws_elasticloadbalancingv2 as alb
)

class CloudFrontConst(core.Construct):

    @property
    def jhub_alb_name(self):
        return self._jhub_alb.load_balancer_dns_name

    @property
    def jhub_cf_name(self):
        return self._jhub_cf.distribution_domain_name  

    @property
    def argo_alb_name(self):
        return self._argo_alb.load_balancer_dns_name

    @property
    def argo_cf_name(self):
        return self._argo_cf.distribution_domain_name    


    def __init__(self,scope: core.Construct, id:str, eksname: str, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

# //**********************************************************************************************************//
# //*************************** Add CloudFront to enable HTTPS Endpoint (OPTIONAL) **************************//
# //***** recommended way is to generate your own SSL certificate via AWS Certificate Manager ***************//
# //****************************** add it to the application load balancer *********************************//
# //*******************************************************************************************************//

        self._jhub_alb = alb.ApplicationLoadBalancer.from_lookup(self, "ALBJHub",
            load_balancer_tags={
                "ingress.k8s.aws/stack": "jupyter/jupyterhub",
                "elbv2.k8s.aws/cluster": eksname
            }
        ) 
        # self._jhub_alb.node.add_dependency(config_hub)
        self._jhub_cf = add_distribution(self, 'jhub_dist', self._jhub_alb, 8000)
        
        self._argo_alb = alb.ApplicationLoadBalancer.from_lookup(self, "ALBArgo",
            load_balancer_tags={
                "ingress.k8s.aws/stack": "argo/argo-server",
                "elbv2.k8s.aws/cluster": eksname
            }
        )   
        # argo_alb.node.add_dependency(argo_install)  
        self._argo_cf = add_distribution(self, 'argo_dist', self._argo_alb, 2746)


def add_distribution(scope: core.Construct, 
    id: str, 
    alb2: alb.ILoadBalancerV2, 
    port: int
) -> cf.IDistribution:

    _origin = origins.LoadBalancerV2Origin(alb2,
        http_port=port,
        protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY
    )
    dist = cf.Distribution(scope, id,
        default_behavior={
            "origin": _origin,
            "allowed_methods": cf.AllowedMethods.ALLOW_ALL,
            "cache_policy": cf.CachePolicy.CACHING_DISABLED,
            "origin_request_policy": cf.OriginRequestPolicy.ALL_VIEWER,
            "viewer_protocol_policy": cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
        }
    )
    return dist