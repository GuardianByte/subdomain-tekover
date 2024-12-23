import boto3

def get_hosted_zone_records(zone_id):
    route53 = boto3.client('route53')
    paginator = route53.get_paginator('list_resource_record_sets')
    records = []
    
    try:
        for page in paginator.paginate(HostedZoneId=zone_id):
            records.extend(page['ResourceRecordSets'])
    except Exception as e:
        print(f"Error fetching records: {e}")
    return records

def validate_alias_record(record):
    elb_client = boto3.client('elbv2')
    try:
        if record.get('AliasTarget') and 'dualstack.' in record['AliasTarget']['DNSName']:
            dns_name = record['AliasTarget']['DNSName']
            response = elb_client.describe_load_balancers()
            existing_elbs = [lb['DNSName'] for lb in response['LoadBalancers']]
            
            if dns_name not in existing_elbs:
                print(f"Dangling Alias Record Detected: {record['Name']} -> {dns_name}")
    except Exception as e:
        print(f"Error validating Alias record: {e}")

def validate_a_record(record):
    ec2 = boto3.client('ec2')
    try:
        if 'ResourceRecords' in record and record['Type'] == 'A':
            ip_addresses = [r['Value'] for r in record['ResourceRecords']]
            response = ec2.describe_instances(Filters=[{'Name': 'private-ip-address', 'Values': ip_addresses}])
            active_ips = [i['PrivateIpAddress'] for r in response['Reservations'] for i in r['Instances']]
            
            for ip in ip_addresses:
                if ip not in active_ips:
                    print(f"Dangling A Record Detected: {record['Name']} -> {ip}")
    except Exception as e:
        print(f"Error validating A record: {e}")

def main():
    route53 = boto3.client('route53')
    try:
        hosted_zones = route53.list_hosted_zones()['HostedZones']
        for zone in hosted_zones:
            print(f"Checking hosted zone: {zone['Name']} (ID: {zone['Id']})")
            zone_id = zone['Id'].split('/')[-1]
            records = get_hosted_zone_records(zone_id)
            
            for record in records:
                if record['Type'] in ['A', 'CNAME']:
                    validate_a_record(record)
                elif record['Type'] == 'ALIAS':
                    validate_alias_record(record)
    except Exception as e:
        print(f"Error in main process: {e}")

if __name__ == "__main__":
    main()
