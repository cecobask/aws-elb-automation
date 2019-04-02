#!/usr/bin/env python3
import boto3
from botocore.config import Config

# Workaround for error:
# An error occurred (RequestLimitExceeded) when calling the DescribeInstances operation (reached max retries: 4): Request limit exceeded.
config = Config(
    retries=dict(
        max_attempts=20
    )
)

ec2 = boto3.resource('ec2', config=config)
elb = boto3.client('elbv2')
autoscaling = boto3.client('autoscaling')
waiter = boto3.client('ec2').get_waiter('instance_running')
instance_ids = []


def create_load_balancer():
    # Create load balancer
    create_lb_response = elb.create_load_balancer(
        Name='automated-lb',
        Subnets=['subnet-0df2c5bd0bcda0308', 'subnet-0898c6a25c05a612b', 'subnet-0c633d627ec94f13e'],
        SecurityGroups=['sg-02348d518d8a4febd'],
        Scheme='internet-facing',
        Type='application')

    # Check create lb was successful
    if create_lb_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        lb_id = create_lb_response['LoadBalancers'][0]['LoadBalancerArn']
        print(f"\nSuccessfully created load balancer {lb_id}")
        return lb_id
    else:
        print("\nCreate load balancer failed.")


def create_instance(instance_name, subnet_id):
    instance = ec2.create_instances(
        ImageId='ami-0157ecca833d5d515',
        InstanceType="t2.micro",
        KeyName='slav_awskey',
        MinCount=1,
        MaxCount=1,
        NetworkInterfaces=[
            {
                'SubnetId': subnet_id,
                'DeviceIndex': 0,
                'AssociatePublicIpAddress': True,
                'Groups': ['sg-02348d518d8a4febd']
            }
        ],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ],
        UserData='''#!/bin/bash
                        sudo yum -y update
                        sudo ./mem.sh'''
    )

    print(f"\nAn instance with ID {instance[0].id} is being created.")
    print("Please wait while the public IP address of your instance is being fetched...")

    # # A loop that will go on until it gets the public IP address of the instance
    while not instance[0].public_ip_address:
        try:
            instance[0].reload()
            if instance[0].public_ip_address:
                # Public IP address is available
                public_ip = instance[0].public_ip_address
                instance_ids.append(instance[0].id)
                print(f"Public IP address of instance {instance_name} ({instance[0].id}): {public_ip}")

        except Exception as e:
            print(e, "\n")


def create_target_group():
    create_tg_response = elb.create_target_group(
        Name='automated-tg',
        Protocol='HTTP',
        Port=80,
        VpcId='vpc-0c2fd01188b67b37f',
        TargetType='instance'
    )

    # check create target-group returned successfully
    if create_tg_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        tg_arn = create_tg_response['TargetGroups'][0]['TargetGroupArn']
        print(f"\nSuccessfully created target group {tg_arn}.")
        return tg_arn
    else:
        print("\nCreate target group failed.")


def register_targets(tg_id):
    # Wait until instances are running
    for instance_id in instance_ids:
        waiter.wait(InstanceIds=[instance_id])

    # Register targets
    targets_dict = [dict(Id=target_id, Port=80) for target_id in instance_ids]
    reg_targets_response = elb.register_targets(TargetGroupArn=tg_id, Targets=targets_dict)

    # Check register targets was successful
    if reg_targets_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("\nSuccessfully registered targets.")
    else:
        print("\nRegister targets failed.")


def create_elb_listener(tg_id, lb_id):
    # Create listener
    create_listener_response = elb.create_listener(
        LoadBalancerArn=lb_id,
        Protocol='HTTP', Port=80,
        DefaultActions=[{'Type': 'forward', 'TargetGroupArn': tg_id}]
    )

    # Check create listener was successful
    if create_listener_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(f"\nSuccessfully created listener for {tg_id}")
    else:
        print("\nCreate listener failed.")


def attach_tg_to_asg(tg_arn):
    attach_tg_response = autoscaling.attach_load_balancer_target_groups(
        AutoScalingGroupName='Assgnmnt-asg',
        TargetGroupARNs=[
            tg_arn,
        ]
    )

    # Check attaching was successful
    if attach_tg_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(f"\nSuccessfully attached {tg_arn} to ASG 'Assgnmnt-asg'")
    else:
        print("\nAttachment of Target Group to Auto Scaling Group failed.")


def main():
    lb_id = create_load_balancer()
    create_instance('WebServer 1a', 'subnet-0df2c5bd0bcda0308')
    create_instance('WebServer 1b', 'subnet-0898c6a25c05a612b')
    create_instance('WebServer 1c', 'subnet-0c633d627ec94f13e')
    tg_arn = create_target_group()
    register_targets(tg_arn)
    create_elb_listener(tg_arn, lb_id)
    attach_tg_to_asg(tg_arn)


if __name__ == '__main__':
    main()
