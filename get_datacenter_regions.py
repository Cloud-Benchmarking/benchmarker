import itertools
import json
import locale
import os
import re
from pprint import pprint

import humanize
import requests
from bs4 import BeautifulSoup


WORKDIR = os.path.join("artifacts", "regions")


def get_aws_zones():
    import boto3

    ec2 = boto3.client("ec2", region_name="us-west-2")

    # Retrieves all regions/endpoints that work with EC2
    aws_regions = ec2.describe_regions()

    # Get a list of regions and then instantiate a new ec2 client for each region in order to get list of AZs for the region
    zones = []
    for region in aws_regions["Regions"]:
        my_region_name = region["RegionName"]
        ec2_region = boto3.client("ec2", region_name=my_region_name)
        my_region = [{"Name": "region-name", "Values": [my_region_name]}]
        # print("Current Region is %s" % my_region_name)
        aws_azs = ec2_region.describe_availability_zones(Filters=my_region)
        for az in aws_azs["AvailabilityZones"]:
            zone = az["ZoneName"]
            # print(zone)
            zones.append(zone)
    pprint({z: None for z in zones})


def get_linode_regions():
    cached_filename = os.path.join(WORKDIR, "linode.json")
    if not os.path.exists(cached_filename):
        if not os.path.exists(os.path.dirname(cached_filename)):
            os.makedirs(os.path.dirname(cached_filename))

        linode = requests.get("https://api.linode.com/v4/regions")
        json.dump(linode.json(), open(cached_filename, "w"))
        linode_regions = linode.json()["data"]
    else:
        linode_regions = json.load(open(cached_filename, "r"))["data"]

    return linode_regions


def get_digitalocean_regions():
    cached_filename = os.path.join(WORKDIR, "digitalocean.json")
    if not os.path.exists(cached_filename):
        headers = {
            "Authorization": "Bearer " + os.environ.get("DIGITALOCEAN_API_TOKEN")
        }
        if not os.path.exists(os.path.dirname(cached_filename)):
            os.makedirs(os.path.dirname(cached_filename))

        resp = requests.get("https://api.digitalocean.com/v2/regions", headers=headers)
        digitalocean = {"regions": []}
        for r in resp.json()["regions"]:
            if r["available"]:
                digitalocean["regions"].append(r)
        json.dump(digitalocean, open(cached_filename, "w"))
        digitalocean_regions = digitalocean["regions"]
    else:
        digitalocean_regions = json.load(open(cached_filename, "r"))["regions"]

    return digitalocean_regions


def get_googlecloud_zones():
    # TODO: Error: Error creating instance: googleapi: Error 400: Standard network tier is not supported for region asia-northeast2., badRequest
    cached_filename = os.path.join(WORKDIR, "googlecloud.json")
    if not os.path.exists(cached_filename):
        if not os.path.exists(os.path.dirname(cached_filename)):
            os.makedirs(os.path.dirname(cached_filename))

        gcp = requests.get("https://cloud.google.com/compute/docs/regions-zones/")
        soup = BeautifulSoup(gcp.content, features="html.parser")
        zones = []
        trs = soup.find(class_="devsite-article-body").find("tbody").find_all("tr")
        for tr in trs:
            tds = tr.find_all("td")
            zone_id = tds[0].find("code").text
            location = tds[1].text

            # does not allow standard networking tier which explodes bandwidth costs
            if zone_id.startswith(
                "asia-northeast2"
            ):  # or zone_id.startswith('asia-south1'):
                continue

            zones.append({"id": zone_id, "location": location})
        json.dump(zones, open(cached_filename, "w"))
        gcp_zones = zones
    else:
        gcp_zones = json.load(open(cached_filename, "r"))

    return gcp_zones


def get_aws_regions():
    cached_filename = os.path.join(WORKDIR, "aws.json")
    if not os.path.exists(cached_filename):
        aws = requests.get("https://docs.aws.amazon.com/general/latest/gr/rande.html")
        soup = BeautifulSoup(aws.content, features="html.parser")
        regions = []
        # pprint(soup.find_all('table'))
        th = soup.find("th", text=re.compile(r"Region Name"))
        table = th.find_parent("table")
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 0:
                continue

            region_name = tds[1].text
            if region_name.startswith("cn-"):
                continue
            # does not allow t2.micro, which means free-tier is t3.micro but has 5gbps connection which explodes bandwidth costs
            if region_name in [
                "ap-northeast-3",
                "af-south-1",
                "ap-east-1",
                "eu-north-1",
                "eu-south-1",
                "me-south-1",
            ]:
                continue

            regions.append(region_name)
        json.dump(regions, open(cached_filename, "w"))
    else:
        regions = json.load(open(cached_filename, "r"))

    return regions


def get_azure_regions():
    cached_filename = os.path.join(WORKDIR, "azure.json")
    if not os.path.exists(cached_filename):
        if not os.path.exists(os.path.dirname(cached_filename)):
            os.makedirs(os.path.dirname(cached_filename))

        # the method used to get regions has a bug and returns regions that you can't launch or have a public-IP
        # this is the reduced list that Azure-Terraform responds back with
        azure_regions = [
            "australiacentral",
            "australiaeast",
            "australiasoutheast",
            "brazilsouth",
            "canadacentral",
            "canadaeast",
            "centralindia",
            "centralus",
            "eastasia",
            "eastus",
            "eastus2",
            "francecentral",
            "germanywestcentral",
            "japaneast",
            "japanwest",
            "koreacentral",
            "koreasouth",
            "northcentralus",
            "northeurope",
            "norwayeast",
            "southafricanorth",
            "southcentralus",
            "southeastasia",
            "switzerlandnorth",
            "uaenorth",
            "uksouth",
            "ukwest",
            "westeurope",
            "westus",
            "westus2",
            # need pay-subscription to request access
            # "westindia",
            # "southindia",
            # larger VM sizes available, cant launch cheap VM with current subscription:
            # "westcentralus"
        ]

        # Azure IP Ranges and Service Tags – Public Cloud
        # https://www.microsoft.com/en-us/download/details.aspx?id=56519
        # service_tags = json.load(open(os.path.join('artifacts', 'ServiceTags_Public_20201221.json'), 'r'))
        # azure_regions = set()
        # for v in service_tags['values']:
        #     if not v['name'].startswith('AzureCloud.'):
        #         continue
        #     r = v['properties']['region']
        #     if r is None or r == '':
        #         continue
        #     azure_regions.add(r)
        # azure_regions = sorted(list(azure_regions))

        # azure = requests.get('https://management.azure.com/metadata/endpoints?api-version=2018-01-01').json()['cloudEndpoint']
        # azure_regions = {}
        # for type, data in azure.items():
        #     azure_regions[type] = data['locations']
        json.dump(azure_regions, open(cached_filename, "w"))
        azure_regions = azure_regions
    else:
        azure_regions = json.load(open(cached_filename, "r"))

    return azure_regions


def get_vultr_regions():
    # https://api.vultr.com/v2/plans
    cached_filename = os.path.join(WORKDIR, "vultr.json")
    if not os.path.exists(cached_filename):
        if not os.path.exists(os.path.dirname(cached_filename)):
            os.makedirs(os.path.dirname(cached_filename))

        # Azure IP Ranges and Service Tags – Public Cloud
        # https://www.microsoft.com/en-us/download/details.aspx?id=56519
        vultr = requests.get("https://api.vultr.com/v2/plans").json()
        vultr_regions = set()
        for plan in vultr["plans"]:
            if plan["id"] != "vc2-1c-1gb":
                continue
            for r in plan["locations"]:
                vultr_regions.add(r)
        vultr_regions = sorted(list(vultr_regions))

        json.dump(vultr_regions, open(cached_filename, "w"))
        vultr_regions = vultr_regions
    else:
        vultr_regions = json.load(open(cached_filename, "r"))

    return vultr_regions
    pass


if __name__ == "__main__":
    aws_regions = get_aws_regions()
    linode_regions = get_linode_regions()
    digitalocean_regions = get_digitalocean_regions()
    googlecloud_zones = get_googlecloud_zones()
    azure_zones = get_azure_regions()
    vultr_regions = get_vultr_regions()

    gcp_zones = list(googlecloud_zones)
    gcp_regions = sorted(
        list(set(["-".join(z["id"].split("-")[:-1]) for z in gcp_zones]))
    )

    all_regions_by_provider = {}
    all_regions_by_provider["linode"] = {r["id"]: None for r in linode_regions}
    all_regions_by_provider["digitalocean"] = {
        r["slug"]: None for r in digitalocean_regions if r["available"]
    }
    all_regions_by_provider["gcp"] = {r: None for r in gcp_regions}
    all_regions_by_provider["azure"] = {r: None for r in azure_zones}
    all_regions_by_provider["aws"] = {r: None for r in aws_regions}

    all_regions_by_provider["vultr"] = {r: None for r in vultr_regions}

    with open(os.path.join("artifacts", "all_regions.json"), "w") as fp:
        json.dump(all_regions_by_provider, fp)

    all_regions = []
    for provider, regions in all_regions_by_provider.items():
        all_regions.extend(regions)
    interregion_combos = list(itertools.combinations(all_regions, 2))
    intraregion_combos = list(zip(all_regions, all_regions))
    all_region_combos = intraregion_combos + interregion_combos
    # pprint(all_region_combos)
    num_combos = len(all_region_combos)
    print(humanize.intcomma(num_combos))
    locale.setlocale(locale.LC_ALL, "English_United States.1252")
    print(locale.currency(num_combos * 0.02, grouping=True))
    with open(os.path.join("artifacts", "all-region-combos.json"), "w") as fp:
        json.dump(all_region_combos, fp)
