  
from aws_cdk.core import IConstruct

def suppress_cfnNag_rule(ruleId: str, reason: str, cnstrt: IConstruct):    
    cnstrt.add_metadata('cfn_nag',{
        "rules_to_suppress": [{
                "id": ruleId,
                "reason": reason
            }]
    })