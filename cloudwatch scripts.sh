#!/bin/bash
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
USEDMEMORY=$(free -m | awk 'NR==2{printf "%.2f\t", $3*100/$2 }')
TCP_CONN=$(netstat -an | wc -l)
TCP_CONN_PORT_80=$(netstat -an | grep 80 | wc -l)
USERS=$(uptime |awk '{ print $5 }')
IO_WAIT=$(iostat | awk 'NR==4 {print $5}')

aws cloudwatch put-metric-data --metric-name memory-usage --dimensions Instance=$INSTANCE_ID --namespace "Custom" --value $USEDMEMORY
aws cloudwatch put-metric-data --metric-name Tcp_connections --dimensions Instance=$INSTANCE_ID --namespace "Custom" --value $TCP_CONN
aws cloudwatch put-metric-data --metric-name TCP_connection_on_port_80 --dimensions Instance=$INSTANCE_ID --namespace "Custom" --value $TCP_CONN_PORT_80
aws cloudwatch put-metric-data --metric-name No_of_users --dimensions Instance=$INSTANCE_ID --namespace "Custom" --value $USERS
aws cloudwatch put-metric-data --metric-name IO_WAIT --dimensions Instance=$INSTANCE_ID --namespace "Custom" --value $IO_WAIT

c=0
if [[ $IO_WAIT > 70 && $USEDMEMORY > 80 ]]
then
 c=1
fi
aws cloudwatch put-metric-data --metric-name danger --dimensions Instance=$INSTANCE_ID --namespace "Custom" --value $c


TARGET_GROUPS=$(aws elbv2 describe-target-groups --query 'TargetGroups[?TargetGroupName==`automated-tg`].TargetGroupArn' --output json | jq -r first)
IFS=':' read -ra TARGET_GROUP <<< "$TARGET_GROUPS"
start=$(date -d '3 minutes ago' "+%Y-%m-%dT%H:%M:%SZ")
end=$(date "+%Y-%m-%dT%H:%M:%SZ")
GET_REQUESTS_PER_TARGET=$(aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCountPerTarget --statistics Sum --start-time $start --end-time $end --period 180 \
--dimensions Name=TargetGroup,Value=${TARGET_GROUP[5]} | jq -r .'Datapoints'[].'Sum')
echo $GET_REQUESTS_PER_TARGET
trigger=0
for i in $GET_REQUESTS_PER_TARGET
do
    if [[ $i > 30 ]]
    then
        trigger=1
        break
    fi
done
echo $trigger
aws cloudwatch put-metric-data --metric-name REQUESTS_PER_TARGET_REACHED --dimensions TargetGroup=${TARGET_GROUP[5]} --namespace "Custom" --value $trigger
