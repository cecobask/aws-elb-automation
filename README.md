# aws-elb-automation
A Python script that generates 3 EC2 instances, automates the creation 
of Elastic Load Balancer and Target Group, as well as registering these 
instances in the TG and attaches TG to the created ELB.

Each EC2 instance is pushing custom CloudWatch metrics to AWS in periods 
of 1 minute, using a cron job. Some of the values are hard-coded, like: 
AMI of preconfigured Web Server instance, AutoScalingGroupName, VpcId, 
KeyName, SecurityGroupId and SubnetId.

## Versioning
[Git](https://git-scm.com/) was used for versioning.



## Authors
 **Tsvetoslav Dimov**  
 [LinkedIn](https://www.linkedin.com/in/cecobask/)

