from aws_cdk import (
    core,
    aws_cloudfront_origins as origins,
    aws_cloudfront as cf
)
from aws_cdk.aws_elasticloadbalancingv2 import ILoadBalancerV2 

class CloudFrontConst(core.Construct):

    @property
    def distribution(self):
        return self._dist

    def __init__(self,scope: core.Construct, id:str, alb: ILoadBalancerV2, port: int, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

        self._origin = origins.LoadBalancerV2Origin(alb,
            http_port=port,
            protocol_policy=cf.OriginProtocolPolicy.HTTP_ONLY
        )
        self._dist = cf.Distribution(self, id,
            default_behavior={
                "origin": self._origin,
                "allowed_methods": cf.AllowedMethods.ALLOW_ALL,
                "origin_request_policy": cf.OriginRequestPolicy.ALL_VIEWER,
                "viewer_protocol_policy": cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            }
        )